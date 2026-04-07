from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from pos_system.database.session import session_scope
from pos_system.models.entities import Category, MenuItem
from pos_system.utils.formatting import as_decimal


class MenuService:
    def save_category(self, name: str, description: str = "", category_id: int | None = None) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Category name is required.")
        with session_scope() as session:
            if category_id:
                category = session.get(Category, category_id)
                if not category:
                    raise ValueError("Category not found.")
            else:
                category = Category()
                session.add(category)
            category.name = name
            category.description = description.strip()
            category.is_active = True
            session.flush()
            return self._serialize_category(category)

    def list_categories(self) -> list[dict]:
        with session_scope() as session:
            categories = session.scalars(select(Category).order_by(Category.name.asc())).all()
            return [self._serialize_category(category) for category in categories]

    def save_menu_item(self, payload: dict, item_id: int | None = None) -> dict:
        with session_scope() as session:
            if item_id:
                item = session.get(MenuItem, item_id)
                if not item:
                    raise ValueError("Menu item not found.")
            else:
                item = MenuItem()
                session.add(item)
            item.category_id = int(payload["category_id"])
            item.name = payload["name"].strip()
            item.description = payload.get("description", "").strip()
            item.price = as_decimal(payload["price"])
            item.is_available = bool(payload.get("is_available", True))
            session.flush()
            session.refresh(item)
            return self._serialize_item(item)

    def list_menu_items(self, category_id: int | None = None, only_available: bool = False) -> list[dict]:
        with session_scope() as session:
            query = select(MenuItem).options(joinedload(MenuItem.category)).order_by(MenuItem.name.asc())
            if category_id:
                query = query.where(MenuItem.category_id == category_id)
            if only_available:
                query = query.where(MenuItem.is_available.is_(True))
            items = session.scalars(query).all()
            return [self._serialize_item(item) for item in items]

    @staticmethod
    def _serialize_category(category: Category) -> dict:
        return {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
        }

    @staticmethod
    def _serialize_item(item: MenuItem) -> dict:
        category_name = item.category.name if item.category else ""
        return {
            "id": item.id,
            "category_id": item.category_id,
            "category_name": category_name,
            "name": item.name,
            "description": item.description,
            "price": float(item.price or 0),
            "is_available": item.is_available,
        }
