from __future__ import annotations

from sqlalchemy import select

from pos_system.database.session import session_scope
from pos_system.models.dtos import SessionUser
from pos_system.models.entities import User
from pos_system.models.enums import UserRole
from pos_system.utils.security import hash_password, verify_password


class AuthService:
    def has_any_user(self) -> bool:
        with session_scope() as session:
            return session.scalar(select(User.id).limit(1)) is not None

    def create_user(self, username: str, password: str, role: UserRole, is_active: bool = True) -> dict:
        username = username.strip()
        if not username or not password:
            raise ValueError("Username and password are required.")
        with session_scope() as session:
            existing = session.scalar(select(User).where(User.username == username))
            if existing:
                raise ValueError("Username already exists.")
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=is_active,
            )
            session.add(user)
            session.flush()
            return self._serialize_user(user)

    def update_user(self, user_id: int, username: str, role: UserRole, is_active: bool, password: str = "") -> dict:
        username = username.strip()
        if not username:
            raise ValueError("Username is required.")
        with session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                raise ValueError("User not found.")
            collision = session.scalar(select(User).where(User.username == username, User.id != user_id))
            if collision:
                raise ValueError("Username already exists.")
            user.username = username
            user.role = role
            user.is_active = is_active
            if password:
                user.password_hash = hash_password(password)
            session.flush()
            return self._serialize_user(user)

    def list_users(self) -> list[dict]:
        with session_scope() as session:
            users = session.scalars(select(User).order_by(User.username.asc())).all()
            return [self._serialize_user(user) for user in users]

    def login(self, username: str, password: str) -> SessionUser:
        with session_scope() as session:
            user = session.scalar(select(User).where(User.username == username.strip()))
            if not user or not verify_password(password, user.password_hash):
                raise ValueError("Invalid username or password.")
            if not user.is_active:
                raise ValueError("This user account is inactive.")
            return SessionUser(user_id=user.id, username=user.username, role=user.role)

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
