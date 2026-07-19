"""Alembic migration environment (T-0.06 / T-1.01).

- sqlalchemy.url is taken from Settings / DATABASE_URL (.env)
- target_metadata is Base.metadata (models registered via app.models)
- Do not use create_all in production (SDS ADR-018)
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure `app` is importable when running from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.database import to_sync_database_url  # noqa: E402
from app.models import Base  # noqa: E402 — loads User / RefreshToken into metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override ini URL with environment-backed settings.
config.set_main_option("sqlalchemy.url", to_sync_database_url(settings.database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
