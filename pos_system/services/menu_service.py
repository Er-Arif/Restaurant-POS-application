from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from pos_system.database.session import session_scope
from pos_system.models.entities import Category, MenuItem, OrderItem
from pos_system.utils.formatting import as_decimal


class MenuService:
    def save_category(self, name: str, description: str = "", category_id: int | None = None) -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Category name is required.")
        with session_scope() as session:
            existing = session.scalar(select(Category).where(Category.name == name))
            if existing and existing.id != category_id:
                raise ValueError("Category name already exists.")
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

    def list_categories(self, only_active: bool = False) -> list[dict]:
        with session_scope() as session:
            query = select(Category).order_by(Category.name.asc())
            if only_active:
                query = query.where(Category.is_active.is_(True))
            categories = session.scalars(query).all()
            return [self._serialize_category(category) for category in categories]

    def set_category_active(self, category_id: int, is_active: bool) -> dict:
        with session_scope() as session:
            category = session.get(Category, category_id)
            if not category:
                raise ValueError("Category not found.")
            category.is_active = bool(is_active)
            if not is_active:
                for item in category.menu_items:
                    item.is_available = False
            session.flush()
            session.refresh(category)
            return self._serialize_category(category)

    def delete_category(self, category_id: int) -> None:
        with session_scope() as session:
            category = session.get(Category, category_id)
            if not category:
                raise ValueError("Category not found.")
            active_items = session.scalars(select(MenuItem).where(MenuItem.category_id == category_id)).all()
            if active_items:
                raise ValueError("This category still has menu items. Archive the category or move/delete its items first.")
            session.delete(category)
            session.flush()

    def save_menu_item(self, payload: dict, item_id: int | None = None) -> dict:
        name = payload["name"].strip()
        if not name:
            raise ValueError("Menu item name is required.")
        if as_decimal(payload["price"]) <= 0:
            raise ValueError("Price must be greater than zero.")
        with session_scope() as session:
            if item_id:
                item = session.get(MenuItem, item_id)
                if not item:
                    raise ValueError("Menu item not found.")
            else:
                item = MenuItem()
                session.add(item)
            category = session.get(Category, int(payload["category_id"]))
            if not category:
                raise ValueError("Category not found.")
            item.category_id = category.id
            item.name = name
            item.description = payload.get("description", "").strip()
            item.price = as_decimal(payload["price"])
            item.is_available = bool(payload.get("is_available", True))
            session.flush()
            session.refresh(item)
            return self._serialize_item(item)

    def set_menu_item_availability(self, item_id: int, is_available: bool) -> dict:
        with session_scope() as session:
            item = session.get(MenuItem, item_id)
            if not item:
                raise ValueError("Menu item not found.")
            item.is_available = bool(is_available)
            session.flush()
            session.refresh(item)
            return self._serialize_item(item)

    def delete_menu_item(self, item_id: int) -> None:
        with session_scope() as session:
            item = session.get(MenuItem, item_id)
            if not item:
                raise ValueError("Menu item not found.")
            existing_sales = session.scalar(select(OrderItem.id).where(OrderItem.menu_item_id == item_id).limit(1))
            if existing_sales is not None:
                raise ValueError("This item has already been sold. Mark it unavailable instead of deleting it.")
            session.delete(item)
            session.flush()

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
        category_active = item.category.is_active if item.category else True
        return {
            "id": item.id,
            "category_id": item.category_id,
            "category_name": category_name,
            "category_is_active": category_active,
            "name": item.name,
            "description": item.description,
            "price": float(item.price or 0),
            "is_available": item.is_available,
        }
