"""documents

Revision ID: 0005_documents
Revises: 0004_audit_logs
Create Date: 2026-07-18

T-3.01 — SDS §10.8 documents (+ native ENUM document_status).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_documents"
down_revision: Union[str, Sequence[str], None] = "0004_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

document_status = postgresql.ENUM(
    "uploaded",
    "processing",
    "ready",
    "deleted",
    "failed",
    name="document_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "uploaded",
        "processing",
        "ready",
        "deleted",
        "failed",
        name="document_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            document_status,
            server_default="uploaded",
            nullable=False,
        ),
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
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_documents_owner_created",
        "documents",
        ["owner_id", "created_at"],
    )
    op.create_index("ix_documents_status", "documents", ["status"])


def downgrade() -> None:
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_owner_created", table_name="documents")
    op.drop_table("documents")
    bind = op.get_bind()
    postgresql.ENUM(name="document_status").drop(bind, checkfirst=True)
