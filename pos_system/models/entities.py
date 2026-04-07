from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pos_system.database.base import Base
from pos_system.models.enums import LicenseType, OrderStatus, PaymentMethod, UserRole


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="created_by")


class RestaurantSettings(TimestampMixin, Base):
    __tablename__ = "restaurant_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    gst_number: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    currency_symbol: Mapped[str] = mapped_column(String(8), default="₹", nullable=False)
    receipt_footer: Mapped[str] = mapped_column(Text, default="Thank you for dining with us!", nullable=False)
    gst_percent: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    default_discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    default_service_charge_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    logo_path: Mapped[str] = mapped_column(String(260), default="", nullable=False)
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="category")


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["Category"] = relationship(back_populates="menu_items")


class Table(TimestampMixin, Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="table")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False),
        default=OrderStatus.OPEN,
        nullable=False,
    )
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    service_charge_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    gst_percent: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    gst_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    grand_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    table: Mapped["Table"] = relationship(back_populates="orders")
    created_by: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, native_enum=False), nullable=False)
    paid_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_received: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    change_returned: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="payments")


class LicenseRecord(Base):
    __tablename__ = "license"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hardware_fingerprint_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    license_type: Mapped[LicenseType] = mapped_column(
        Enum(LicenseType, native_enum=False),
        nullable=False,
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    last_validated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
