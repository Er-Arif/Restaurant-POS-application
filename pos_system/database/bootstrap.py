from __future__ import annotations

from sqlalchemy import text

from pos_system.database.base import Base
from pos_system.database.session import engine
from pos_system.models import entities  # noqa: F401


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_schema_updates()


def _ensure_schema_updates() -> None:
    with engine.begin() as connection:
        user_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(users)"))}
        if "full_name" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) NOT NULL DEFAULT ''"))

        settings_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(restaurant_settings)"))}
        schema_updates = [
            ("receipt_header", "ALTER TABLE restaurant_settings ADD COLUMN receipt_header VARCHAR(160) NOT NULL DEFAULT 'Thank you for dining with us!'"),
            ("receipt_subheader", "ALTER TABLE restaurant_settings ADD COLUMN receipt_subheader VARCHAR(160) NOT NULL DEFAULT ''"),
            ("receipt_show_address", "ALTER TABLE restaurant_settings ADD COLUMN receipt_show_address BOOLEAN NOT NULL DEFAULT 1"),
            ("receipt_show_phone", "ALTER TABLE restaurant_settings ADD COLUMN receipt_show_phone BOOLEAN NOT NULL DEFAULT 1"),
            ("receipt_show_gst", "ALTER TABLE restaurant_settings ADD COLUMN receipt_show_gst BOOLEAN NOT NULL DEFAULT 1"),
            ("receipt_show_cashier", "ALTER TABLE restaurant_settings ADD COLUMN receipt_show_cashier BOOLEAN NOT NULL DEFAULT 1"),
            ("receipt_show_table", "ALTER TABLE restaurant_settings ADD COLUMN receipt_show_table BOOLEAN NOT NULL DEFAULT 1"),
            ("receipt_show_order_number", "ALTER TABLE restaurant_settings ADD COLUMN receipt_show_order_number BOOLEAN NOT NULL DEFAULT 1"),
        ]
        for column_name, statement in schema_updates:
            if column_name not in settings_columns:
                connection.execute(text(statement))
