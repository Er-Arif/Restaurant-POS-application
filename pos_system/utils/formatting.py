from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal("0.01")


def as_decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def money_text(value, currency_symbol: str = "₹") -> str:
    amount = as_decimal(value)
    return f"{currency_symbol}{amount:,.2f}"


def parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
