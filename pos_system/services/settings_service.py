from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select

from pos_system.config.app_config import LOGO_DIR
from pos_system.database.session import session_scope
from pos_system.models.entities import RestaurantSettings
from pos_system.utils.formatting import as_decimal


class SettingsService:
    def get_settings(self) -> dict:
        with session_scope() as session:
            settings = session.scalar(select(RestaurantSettings).limit(1))
            if not settings:
                settings = RestaurantSettings()
                session.add(settings)
                session.flush()
            return self._serialize(settings)

    def save_settings(self, payload: dict) -> dict:
        with session_scope() as session:
            settings = session.scalar(select(RestaurantSettings).limit(1))
            if not settings:
                settings = RestaurantSettings()
                session.add(settings)
            settings.restaurant_name = payload.get("restaurant_name", "").strip()
            settings.address = payload.get("address", "").strip()
            settings.phone = payload.get("phone", "").strip()
            settings.gst_number = payload.get("gst_number", "").strip()
            settings.currency_symbol = payload.get("currency_symbol", "?").strip() or "?"
            settings.receipt_footer = payload.get("receipt_footer", "").strip() or "Thank you for dining with us!"
            settings.gst_percent = as_decimal(payload.get("gst_percent", 0))
            settings.default_discount_amount = as_decimal(payload.get("default_discount_amount", 0))
            settings.default_service_charge_amount = as_decimal(payload.get("default_service_charge_amount", 0))
            settings.setup_complete = bool(payload.get("setup_complete", settings.setup_complete))
            logo_source = payload.get("logo_source_path", "")
            if logo_source:
                settings.logo_path = self._store_logo(logo_source)
            session.flush()
            return self._serialize(settings)

    def is_setup_complete(self) -> bool:
        with session_scope() as session:
            settings = session.scalar(select(RestaurantSettings).limit(1))
            return bool(settings and settings.setup_complete)

    def _store_logo(self, source_path: str) -> str:
        source = Path(source_path).resolve()
        if not source.exists():
            raise ValueError("Logo file not found.")
        target = (LOGO_DIR / f"restaurant_logo{source.suffix.lower()}").resolve()
        if source == target:
            return str(target)
        shutil.copy2(source, target)
        return str(target)

    @staticmethod
    def _serialize(settings: RestaurantSettings) -> dict:
        return {
            "id": settings.id,
            "restaurant_name": settings.restaurant_name,
            "address": settings.address,
            "phone": settings.phone,
            "gst_number": settings.gst_number,
            "currency_symbol": settings.currency_symbol,
            "receipt_footer": settings.receipt_footer,
            "gst_percent": float(settings.gst_percent or 0),
            "default_discount_amount": float(settings.default_discount_amount or 0),
            "default_service_charge_amount": float(settings.default_service_charge_amount or 0),
            "logo_path": settings.logo_path,
            "setup_complete": settings.setup_complete,
        }
