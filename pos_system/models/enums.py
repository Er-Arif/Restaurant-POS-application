from enum import Enum


class StartupStatus(str, Enum):
    NEEDS_ACTIVATION = "needs_activation"
    NEEDS_SETUP = "needs_setup"
    READY = "ready"


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"


class LicenseType(str, Enum):
    TRIAL = "trial"
    LIFETIME = "lifetime"


class OrderStatus(str, Enum):
    OPEN = "open"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CASH = "cash"
    UPI = "upi"
