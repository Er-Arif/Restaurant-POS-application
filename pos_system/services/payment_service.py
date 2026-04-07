from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from pos_system.database.session import session_scope
from pos_system.models.entities import Order, Payment
from pos_system.models.enums import OrderStatus, PaymentMethod
from pos_system.utils.formatting import as_decimal


class PaymentService:
    def settle(self, order_id: int, method: str, amount_received: float) -> dict:
        payment_method = PaymentMethod(method)
        with session_scope() as session:
            order = session.execute(
                select(Order)
                .where(Order.id == order_id)
                .options(selectinload(Order.items), joinedload(Order.table), joinedload(Order.created_by), selectinload(Order.payments))
            ).scalars().first()
            if not order:
                raise ValueError("Order not found.")
            if order.status != OrderStatus.OPEN:
                raise ValueError("Only open orders can be settled.")
            paid_amount = as_decimal(order.grand_total)
            received = as_decimal(amount_received if payment_method == PaymentMethod.CASH else paid_amount)
            if payment_method == PaymentMethod.CASH and received < paid_amount:
                raise ValueError("Cash received is less than the bill total.")
            change_returned = received - paid_amount if payment_method == PaymentMethod.CASH else as_decimal(0)
            payment = Payment(
                order_id=order.id,
                method=payment_method,
                paid_amount=paid_amount,
                amount_received=received,
                change_returned=change_returned,
            )
            session.add(payment)
            order.status = OrderStatus.PAID
            session.flush()
            return {
                "order_id": order.id,
                "method": payment_method.value,
                "paid_amount": float(payment.paid_amount),
                "amount_received": float(payment.amount_received),
                "change_returned": float(payment.change_returned),
                "status": order.status.value,
            }
