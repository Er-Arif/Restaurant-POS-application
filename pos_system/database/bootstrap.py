from pos_system.database.base import Base
from pos_system.database.session import engine
from pos_system.models import entities  # noqa: F401


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
