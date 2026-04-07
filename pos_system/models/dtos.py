from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pos_system.models.enums import LicenseType, StartupStatus, UserRole


@dataclass(slots=True)
class StartupState:
    status: StartupStatus
    message: str = ""


@dataclass(slots=True)
class ActivationResult:
    success: bool
    message: str
    license_type: LicenseType | None = None
    expiry_date: date | None = None


@dataclass(slots=True)
class SessionUser:
    user_id: int
    username: str
    role: UserRole


@dataclass(slots=True)
class OrderTotals:
    subtotal: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    service_charge_amount: Decimal = Decimal("0.00")
    gst_percent: Decimal = Decimal("0.00")
    gst_amount: Decimal = Decimal("0.00")
    grand_total: Decimal = Decimal("0.00")
