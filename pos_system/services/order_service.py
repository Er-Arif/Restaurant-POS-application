from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from pos_system.database.session import session_scope
from pos_system.models.dtos import OrderTotals
from pos_system.models.entities import MenuItem, Order, OrderItem, RestaurantSettings, Table
from pos_system.models.enums import OrderStatus
from pos_system.utils.formatting import as_decimal


class OrderService:
    def open_table_order(self, table_id: int, user_id: int) -> dict:
        with session_scope() as session:
            table = session.get(Table, table_id)
            if not table or not table.is_active:
                raise ValueError("Table not found.")
            existing = session.execute(
                select(Order)
                .where(Order.table_id == table_id, Order.status == OrderStatus.OPEN)
                .options(selectinload(Order.items), joinedload(Order.table), joinedload(Order.created_by), selectinload(Order.payments))
                .execution_options(populate_existing=True)
            ).scalars().first()
            if existing:
                return self._serialize_order(existing)
            settings = session.scalar(select(RestaurantSettings).limit(1))
            order = Order(
                order_number=self._generate_order_number(table.code),
                table_id=table_id,
                created_by_user_id=user_id,
                status=OrderStatus.OPEN,
                discount_amount=as_decimal(settings.default_discount_amount if settings else 0),
                service_charge_amount=as_decimal(settings.default_service_charge_amount if settings else 0),
                gst_percent=as_decimal(settings.gst_percent if settings else 0),
            )
            session.add(order)
            session.flush()
            self._reprice_with_session(session, order)
            order = self._load_order(session, order.id)
            return self._serialize_order(order)

    def add_item(self, order_id: int, menu_item_id: int, qty: int = 1) -> dict:
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero.")
        with session_scope() as session:
            order = self._load_order(session, order_id)
            menu_item = session.get(MenuItem, menu_item_id)
            if not menu_item or not menu_item.is_available:
                raise ValueError("Menu item is unavailable.")
            existing = next((item for item in order.items if item.menu_item_id == menu_item_id), None)
            if existing:
                existing.quantity += qty
                existing.line_total = as_decimal(existing.quantity) * as_decimal(existing.unit_price_snapshot)
            else:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    item_name_snapshot=menu_item.name,
                    unit_price_snapshot=as_decimal(menu_item.price),
                    quantity=qty,
                    line_total=as_decimal(menu_item.price) * as_decimal(qty),
                )
                session.add(order_item)
            session.flush()
            session.expire_all()
            order = self._load_order(session, order_id)
            self._reprice_with_session(session, order)
            session.expire_all()
            order = self._load_order(session, order_id)
            return self._serialize_order(order)

    def remove_order_item(self, order_id: int, order_item_id: int) -> dict:
        with session_scope() as session:
            order = self._load_order(session, order_id)
            order_item = next((item for item in order.items if item.id == order_item_id), None)
            if not order_item:
                raise ValueError("Order item not found.")
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.line_total = as_decimal(order_item.quantity) * as_decimal(order_item.unit_price_snapshot)
            else:
                session.delete(order_item)
            session.flush()
            session.expire_all()
            order = self._load_order(session, order_id)
            self._reprice_with_session(session, order)
            session.expire_all()
            order = self._load_order(session, order_id)
            return self._serialize_order(order)

    def update_adjustments(self, order_id: int, discount_amount: float, service_charge_amount: float) -> dict:
        with session_scope() as session:
            order = self._load_order(session, order_id)
            order.discount_amount = as_decimal(discount_amount)
            order.service_charge_amount = as_decimal(service_charge_amount)
            self._reprice_with_session(session, order)
            session.expire_all()
            order = self._load_order(session, order_id)
            return self._serialize_order(order)

    def reprice(self, order_id: int) -> OrderTotals:
        with session_scope() as session:
            order = self._load_order(session, order_id)
            return self._reprice_with_session(session, order)

    def list_orders(self, status: str | None = None) -> list[dict]:
        with session_scope() as session:
            query = (
                select(Order)
                .options(selectinload(Order.items), joinedload(Order.table), joinedload(Order.created_by), selectinload(Order.payments))
                .order_by(Order.created_at.desc())
            )
            if status:
                query = query.where(Order.status == OrderStatus(status))
            orders = session.scalars(query).unique().all()
            return [self._serialize_order(order) for order in orders]

    def get_order(self, order_id: int) -> dict:
        with session_scope() as session:
            order = self._load_order(session, order_id)
            return self._serialize_order(order)

    def cancel_order(self, order_id: int) -> dict:
        with session_scope() as session:
            order = self._load_order(session, order_id)
            if order.status == OrderStatus.PAID:
                raise ValueError("Paid orders cannot be cancelled.")
            order.status = OrderStatus.CANCELLED
            session.flush()
            return self._serialize_order(order)

    def _load_order(self, session, order_id: int) -> Order:
        order = session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), joinedload(Order.table), joinedload(Order.created_by), selectinload(Order.payments))
            .execution_options(populate_existing=True)
        ).scalars().first()
        if not order:
            raise ValueError("Order not found.")
        return order

    def _reprice_with_session(self, session, order: Order) -> OrderTotals:
        subtotal = sum((as_decimal(item.line_total) for item in order.items), start=Decimal("0.00"))
        discount_amount = as_decimal(order.discount_amount)
        service_charge_amount = as_decimal(order.service_charge_amount)
        gst_percent = as_decimal(order.gst_percent)
        if subtotal == Decimal("0.00"):
            gst_amount = Decimal("0.00")
            grand_total = Decimal("0.00")
        else:
            taxable_amount = max(subtotal - discount_amount, Decimal("0.00")) + service_charge_amount
            gst_amount = (taxable_amount * gst_percent / Decimal("100")).quantize(Decimal("0.01"))
            grand_total = (taxable_amount + gst_amount).quantize(Decimal("0.01"))

        order.subtotal = subtotal
        order.gst_amount = gst_amount
        order.grand_total = grand_total
        session.flush()
        return OrderTotals(
            subtotal=subtotal,
            discount_amount=discount_amount,
            service_charge_amount=service_charge_amount,
            gst_percent=gst_percent,
            gst_amount=gst_amount,
            grand_total=grand_total,
        )

    @staticmethod
    def _generate_order_number(table_code: str) -> str:
        return f"{table_code}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    @staticmethod
    def _serialize_order(order: Order) -> dict:
        return {
            "id": order.id,
            "order_number": order.order_number,
            "table_id": order.table_id,
            "table_name": order.table.name if order.table else "",
            "created_by_user_id": order.created_by_user_id,
            "created_by_username": order.created_by.username if order.created_by else "",
            "status": order.status.value,
            "subtotal": float(order.subtotal or 0),
            "discount_amount": float(order.discount_amount or 0),
            "service_charge_amount": float(order.service_charge_amount or 0),
            "gst_percent": float(order.gst_percent or 0),
            "gst_amount": float(order.gst_amount or 0),
            "grand_total": float(order.grand_total or 0),
            "created_at": order.created_at,
            "items": [
                {
                    "id": item.id,
                    "menu_item_id": item.menu_item_id,
                    "name": item.item_name_snapshot,
                    "unit_price": float(item.unit_price_snapshot or 0),
                    "quantity": item.quantity,
                    "line_total": float(item.line_total or 0),
                }
                for item in order.items
            ],
            "payments": [
                {
                    "id": payment.id,
                    "method": payment.method.value,
                    "paid_amount": float(payment.paid_amount or 0),
                    "amount_received": float(payment.amount_received or 0),
                    "change_returned": float(payment.change_returned or 0),
                    "created_at": payment.created_at,
                }
                for payment in order.payments
            ],
        }
