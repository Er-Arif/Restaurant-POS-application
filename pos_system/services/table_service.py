from __future__ import annotations

from sqlalchemy import select

from pos_system.database.session import session_scope
from pos_system.models.entities import Table


class TableService:
    def initialize_tables(self, count: int, prefix: str = "T") -> list[dict]:
        prefix = prefix.strip() or "T"
        with session_scope() as session:
            session.query(Table).delete()
            tables = []
            for index in range(1, count + 1):
                table = Table(
                    name=f"{prefix}{index}",
                    code=f"{prefix}{index}",
                    display_order=index,
                    is_active=True,
                )
                session.add(table)
                tables.append(table)
            session.flush()
            return [self._serialize(table) for table in tables]

    def list_tables(self) -> list[dict]:
        with session_scope() as session:
            tables = session.scalars(select(Table).order_by(Table.display_order.asc(), Table.name.asc())).all()
            return [self._serialize(table) for table in tables]

    @staticmethod
    def _serialize(table: Table) -> dict:
        return {
            "id": table.id,
            "name": table.name,
            "code": table.code,
            "display_order": table.display_order,
            "is_active": table.is_active,
        }
