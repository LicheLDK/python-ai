"""stat_daily

Revision ID: 0009_stat_daily
Revises: 0008_pipelines
Create Date: 2026-07-18

T-7.01 — SDS §10.16 stat_daily (UNIQUE(date, metric, user_id, dim_key);
NULL user_id = global, uniqueness enforced via coalesce expression index).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_stat_daily"
down_revision: Union[str, Sequence[str], None] = "0008_pipelines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NIL_UUID = "'00000000-0000-0000-0000-000000000000'::uuid"


def upgrade() -> None:
    op.create_table(
        "stat_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "dim_key",
            sa.String(length=256),
            server_default="",
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(24, 6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # NULL user_id must collide (global rows) → coalesce to nil uuid.
    op.create_index(
        "ux_stat_daily_key",
        "stat_daily",
        [
            sa.text("date"),
            sa.text("metric"),
            sa.text(f"coalesce(user_id, {_NIL_UUID})"),
            sa.text("dim_key"),
        ],
        unique=True,
    )
    op.create_index(
        "ix_stat_daily_metric_date",
        "stat_daily",
        ["metric", "date"],
        unique=False,
    )
    op.create_index(
        "ix_stat_daily_user_date",
        "stat_daily",
        ["user_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stat_daily_user_date", table_name="stat_daily")
    op.drop_index("ix_stat_daily_metric_date", table_name="stat_daily")
    op.drop_index("ux_stat_daily_key", table_name="stat_daily")
    op.drop_table("stat_daily")
