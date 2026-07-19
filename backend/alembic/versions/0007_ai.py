"""ai_prompts_requests_usages

Revision ID: 0007_ai
Revises: 0006_ocr
Create Date: 2026-07-18

T-5.01 — SDS §10.11 ai_prompts, §10.12 ai_requests, §10.13 ai_usages
(+ ENUMs ai_provider, ai_request_type, ai_request_status).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_ai"
down_revision: Union[str, Sequence[str], None] = "0006_ocr"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ai_provider = postgresql.ENUM(
    "openai",
    "gemini",
    name="ai_provider",
    create_type=False,
)
ai_request_type = postgresql.ENUM(
    "chat",
    "vision",
    "pipeline",
    name="ai_request_type",
    create_type=False,
)
ai_request_status = postgresql.ENUM(
    "succeeded",
    "failed",
    name="ai_request_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("openai", "gemini", name="ai_provider").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("chat", "vision", "pipeline", name="ai_request_type").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("succeeded", "failed", name="ai_request_status").create(
        bind, checkfirst=True
    )

    op.create_table(
        "ai_prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column(
            "variables_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["created_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_ai_prompts_name_version"),
    )
    op.create_index(
        "uq_ai_prompts_name_active",
        "ai_prompts",
        ["name"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE"),
    )

    op.create_table(
        "ai_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", ai_provider, nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_type", ai_request_type, nullable=False),
        sa.Column(
            "input_ref",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "output_ref",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("status", ai_request_status, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["prompt_id"],
            ["ai_prompts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_requests_user_created",
        "ai_requests",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ai_requests_provider_created",
        "ai_requests",
        ["provider", "created_at"],
    )

    op.create_table(
        "ai_usages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tokens_in",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "tokens_out",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "cost_estimate",
            sa.Numeric(18, 6),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ai_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_ai_usages_request_id"),
    )
    op.create_index("ix_ai_usages_created_at", "ai_usages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_usages_created_at", table_name="ai_usages")
    op.drop_table("ai_usages")
    op.drop_index("ix_ai_requests_provider_created", table_name="ai_requests")
    op.drop_index("ix_ai_requests_user_created", table_name="ai_requests")
    op.drop_table("ai_requests")
    op.drop_index(
        "uq_ai_prompts_name_active",
        table_name="ai_prompts",
        postgresql_where=sa.text("active IS TRUE"),
    )
    op.drop_table("ai_prompts")
    bind = op.get_bind()
    postgresql.ENUM(name="ai_request_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="ai_request_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="ai_provider").drop(bind, checkfirst=True)
