"""pipeline_runs

Revision ID: 0008_pipelines
Revises: 0007_ai
Create Date: 2026-07-18

T-6.01 — SDS §10.14 pipeline_runs (+ ENUM pipeline_run_status).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_pipelines"
down_revision: Union[str, Sequence[str], None] = "0007_ai"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pipeline_run_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="pipeline_run_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelled",
        name="pipeline_run_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            pipeline_run_status,
            server_default="queued",
            nullable=False,
        ),
        sa.Column(
            "stages",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("ocr_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ocr_job_id"], ["ocr_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["ai_request_id"], ["ai_requests.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_runs_user_created",
        "pipeline_runs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_pipeline_runs_status",
        "pipeline_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_user_created", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
    bind = op.get_bind()
    postgresql.ENUM(name="pipeline_run_status").drop(bind, checkfirst=True)
