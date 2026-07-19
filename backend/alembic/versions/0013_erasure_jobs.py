"""erasure_jobs

Revision ID: 0013_erasure_jobs
Revises: 0012_organizations
Create Date: 2026-07-19

T-17.01 — B-P1-ERASURE / SPIKE_DATA_RETENTION: async account/document erasure jobs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_erasure_jobs"
down_revision: Union[str, Sequence[str], None] = "0012_organizations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

erasure_job_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    name="erasure_job_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "queued",
        "running",
        "succeeded",
        "failed",
        name="erasure_job_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "erasure_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[\"account\"]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            erasure_job_status,
            server_default="queued",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_erasure_jobs_target_created",
        "erasure_jobs",
        ["target_user_id", "created_at"],
    )
    op.create_index("ix_erasure_jobs_status", "erasure_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_erasure_jobs_status", table_name="erasure_jobs")
    op.drop_index("ix_erasure_jobs_target_created", table_name="erasure_jobs")
    op.drop_table("erasure_jobs")
    op.execute("DROP TYPE IF EXISTS erasure_job_status")
