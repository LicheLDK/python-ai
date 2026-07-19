"""document_chunks for RAG

Revision ID: 0011_rag_chunks
Revises: 0010_ai_provider_ollama
Create Date: 2026-07-19

T-15.04 — B-1.1-RAG / SDS ADR-016 (v1.1): chunk + JSONB embedding store.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_rag_chunks"
down_revision: Union[str, Sequence[str], None] = "0010_ai_provider_ollama"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ocr_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page", sa.Integer(), server_default="1", nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column(
            "meta",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ocr_job_id"], ["ocr_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "ocr_job_id",
            "chunk_index",
            name="uq_document_chunks_doc_job_idx",
        ),
    )
    op.create_index(
        "ix_document_chunks_owner_document",
        "document_chunks",
        ["owner_id", "document_id"],
    )
    op.create_index(
        "ix_document_chunks_ocr_job_id",
        "document_chunks",
        ["ocr_job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_ocr_job_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_owner_document", table_name="document_chunks")
    op.drop_table("document_chunks")
