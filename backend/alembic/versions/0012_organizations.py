"""organizations + users.org_id

Revision ID: 0012_organizations
Revises: 0011_rag_chunks
Create Date: 2026-07-19

T-16.01 / T-16.02 — B-1.2-TENANT / SDS ADR-015 additive soft multi-tenant.
Creates default org and backfills existing users.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_organizations"
down_revision: Union[str, Sequence[str], None] = "0011_rag_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Stable default tenant id for local/seed predictability
DEFAULT_ORG_ID = "00000000-0000-4000-8000-000000000001"

organization_status = postgresql.ENUM(
    "active",
    "inactive",
    name="organization_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "active",
        "inactive",
        name="organization_status",
    ).create(bind, checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            organization_status,
            server_default="active",
            nullable=False,
        ),
        sa.Column("ai_rate_limit_max", sa.Integer(), nullable=True),
        sa.Column("ai_rate_limit_window_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "branding",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, slug, status, branding)
            VALUES (
              CAST(:id AS uuid),
              'Default Organization',
              'default',
              'active',
              '{}'::jsonb
            )
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(id=DEFAULT_ORG_ID)
    )

    op.add_column(
        "users",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users SET org_id = CAST(:id AS uuid) WHERE org_id IS NULL"
        ).bindparams(id=DEFAULT_ORG_ID)
    )
    op.alter_column("users", "org_id", nullable=False)
    op.create_foreign_key(
        "fk_users_org_id_organizations",
        "users",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_users_org_id", "users", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_constraint("fk_users_org_id_organizations", "users", type_="foreignkey")
    op.drop_column("users", "org_id")
    op.drop_table("organizations")
    op.execute("DROP TYPE IF EXISTS organization_status")
