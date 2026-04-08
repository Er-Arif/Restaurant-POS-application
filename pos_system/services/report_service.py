from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from pos_system.config.app_config import EXPORT_DIR
from pos_system.database.session import session_scope
from pos_system.models.entities import Order
from pos_system.models.enums import OrderStatus, PaymentMethod
from pos_system.utils.formatting import as_decimal


@dataclass(slots=True)
class ReportSummary:
    order_count: int
    total_revenue: Decimal
    cash_revenue: Decimal
    upi_revenue: Decimal
    average_bill: Decimal = Decimal("0.00")
    top_items: list[tuple[str, int]] = field(default_factory=list)
    recent_orders: list[dict] = field(default_factory=list)


class ReportService:
    def sales_summary(self, start_date: date, end_date: date) -> ReportSummary:
        orders = self._load_paid_orders(start_date, end_date)
        total_revenue = sum((as_decimal(order.grand_total) for order in orders), start=Decimal("0.00"))
        cash_revenue = Decimal("0.00")
        upi_revenue = Decimal("0.00")
        item_counter: Counter[str] = Counter()
        recent_orders: list[dict] = []
        for order in orders:
            for payment in order.payments:
                if payment.method == PaymentMethod.CASH:
                    cash_revenue += as_decimal(payment.paid_amount)
                elif payment.method == PaymentMethod.UPI:
                    upi_revenue += as_decimal(payment.paid_amount)
            for item in order.items:
                item_counter[item.item_name_snapshot] += item.quantity
            recent_orders.append(
                {
                    "order_number": order.order_number,
                    "table_name": order.table.name if order.table else "",
                    "created_by": order.created_by.username if order.created_by else "",
                    "total": float(order.grand_total or 0),
                    "created_at": order.created_at,
                    "payment_method": order.payments[0].method.value if order.payments else "",
                }
            )
        average_bill = (total_revenue / len(orders)).quantize(Decimal("0.01")) if orders else Decimal("0.00")
        return ReportSummary(
            order_count=len(orders),
            total_revenue=total_revenue,
            cash_revenue=cash_revenue,
            upi_revenue=upi_revenue,
            average_bill=average_bill,
            top_items=item_counter.most_common(5),
            recent_orders=recent_orders[:8],
        )

    def export_orders_csv(self, filters: dict) -> str:
        start_date = filters["start_date"]
        end_date = filters["end_date"]
        orders = self._load_paid_orders(start_date, end_date)
        filename = EXPORT_DIR / f"orders_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        with filename.open("w", newline="", encoding="utf-8") as file_handle:
            writer = csv.writer(file_handle)
            writer.writerow(
                [
                    "Order Number",
                    "Table",
                    "Created By",
                    "Status",
                    "Subtotal",
                    "Discount",
                    "Service Charge",
                    "GST %",
                    "GST Amount",
                    "Grand Total",
                    "Payment Method",
                    "Created At",
                ]
            )
            for order in orders:
                payment_method = order.payments[0].method.value if order.payments else ""
                writer.writerow(
                    [
                        order.order_number,
                        order.table.name if order.table else "",
                        order.created_by.username if order.created_by else "",
                        order.status.value,
                        f"{float(order.subtotal):.2f}",
                        f"{float(order.discount_amount):.2f}",
                        f"{float(order.service_charge_amount):.2f}",
                        f"{float(order.gst_percent):.2f}",
                        f"{float(order.gst_amount):.2f}",
                        f"{float(order.grand_total):.2f}",
                        payment_method,
                        order.created_at.isoformat(sep=" ", timespec="seconds"),
                    ]
                )
        return str(filename)

    def _load_paid_orders(self, start_date: date, end_date: date) -> list[Order]:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        with session_scope() as session:
            orders = session.scalars(
                select(Order)
                .where(Order.status == OrderStatus.PAID, Order.created_at >= start_dt, Order.created_at <= end_dt)
                .options(selectinload(Order.payments), selectinload(Order.items), joinedload(Order.table), joinedload(Order.created_by))
                .order_by(Order.created_at.desc())
            ).unique().all()
            return orders

