from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_value: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_value.encode("utf-8"))
