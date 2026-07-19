"""ocr_jobs_results

Revision ID: 0006_ocr
Revises: 0005_documents
Create Date: 2026-07-18

T-4.01 — SDS §10.9 ocr_jobs, §10.10 ocr_results (+ ENUM ocr_job_status).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_ocr"
down_revision: Union[str, Sequence[str], None] = "0005_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ocr_job_status = postgresql.ENUM(
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    name="ocr_job_status",
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
        name="ocr_job_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "ocr_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            ocr_job_status,
            server_default="queued",
            nullable=False,
        ),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ocr_jobs_user_created",
        "ocr_jobs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ocr_jobs_status_created",
        "ocr_jobs",
        ["status", "created_at"],
    )
    op.create_index("ix_ocr_jobs_document_id", "ocr_jobs", ["document_id"])

    op.create_table(
        "ocr_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "boxes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["ocr_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "page", name="uq_ocr_results_job_page"),
    )


def downgrade() -> None:
    op.drop_table("ocr_results")
    op.drop_index("ix_ocr_jobs_document_id", table_name="ocr_jobs")
    op.drop_index("ix_ocr_jobs_status_created", table_name="ocr_jobs")
    op.drop_index("ix_ocr_jobs_user_created", table_name="ocr_jobs")
    op.drop_table("ocr_jobs")
    bind = op.get_bind()
    postgresql.ENUM(name="ocr_job_status").drop(bind, checkfirst=True)
