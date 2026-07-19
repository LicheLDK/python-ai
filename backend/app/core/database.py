"""SQLAlchemy 2.x engine and session factory (T-0.06).

Connection URL comes from Settings / `.env` (`DATABASE_URL`).
Uses a sync engine for SessionLocal and Alembic (ADR-018).
Does not define domain models or repositories.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def to_sync_database_url(url: str) -> str:
    """Normalize DATABASE_URL to a sync driver for Engine / Alembic.

    `.env` may use ``postgresql+asyncpg://`` (future async clients).
    SessionLocal and Alembic require a sync driver (psycopg).
    """
    sync_url = url
    for source, target in (
        ("postgresql+asyncpg://", "postgresql+psycopg://"),
        ("postgres+asyncpg://", "postgresql+psycopg://"),
        ("postgresql+psycopg2://", "postgresql+psycopg://"),
    ):
        sync_url = sync_url.replace(source, target)
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return sync_url


SQLALCHEMY_DATABASE_URL = to_sync_database_url(settings.database_url)

engine: Engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session and always close it (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_postgres() -> bool:
    """Return True if PostgreSQL accepts a simple query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
