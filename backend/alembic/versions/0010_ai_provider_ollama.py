"""Add ``ollama`` to ``ai_provider`` enum (T-13.02)."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0010_ai_provider_ollama"
down_revision: Union[str, None] = "0009_stat_daily"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL ENUM values cannot be removed easily; ADD VALUE is the
    # normative forward path for provider expansion.
    op.execute("ALTER TYPE ai_provider ADD VALUE IF NOT EXISTS 'ollama'")


def downgrade() -> None:
    # PG cannot drop a single enum value safely without recreating the type.
    # Leave as no-op; documented in TASKS / CHANGELOG.
    pass
