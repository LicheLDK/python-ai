"""SQLAlchemy Declarative Base (T-0.06).

Domain models register on this Base (users/auth from T-1.01 onward).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadata root for Alembic and future ORM models."""

    pass
