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
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(users)"))}
        if "full_name" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(120) NOT NULL DEFAULT ''"))
