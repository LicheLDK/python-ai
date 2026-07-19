"""rbac_permissions

Revision ID: 0003_rbac
Revises: 0002_users_auth
Create Date: 2026-07-18

T-2.01 — SDS §10.5 permissions, §10.6 role_permissions + seed codes.
Reuses existing PostgreSQL ENUM user_role (do not recreate).
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_rbac"
down_revision: Union[str, Sequence[str], None] = "0002_users_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("user", "admin", name="user_role", create_type=False)

# Stable UUIDs so upgrade/downgrade and re-seed checks are deterministic.
_PERMISSION_IDS: dict[str, uuid.UUID] = {
    "ocr:run": uuid.UUID("a1000000-0000-4000-8000-000000000001"),
    "ai:chat": uuid.UUID("a1000000-0000-4000-8000-000000000002"),
    "ai:vision": uuid.UUID("a1000000-0000-4000-8000-000000000003"),
    "ai:manage_prompts": uuid.UUID("a1000000-0000-4000-8000-000000000004"),
    "documents:write": uuid.UUID("a1000000-0000-4000-8000-000000000005"),
    "admin:users": uuid.UUID("a1000000-0000-4000-8000-000000000006"),
    "admin:audit": uuid.UUID("a1000000-0000-4000-8000-000000000007"),
    "admin:usage": uuid.UUID("a1000000-0000-4000-8000-000000000008"),
}

_PERMISSION_ROWS: tuple[tuple[str, str], ...] = (
    ("ocr:run", "Submit and view own OCR jobs"),
    ("ai:chat", "Call AI chat endpoints"),
    ("ai:vision", "Call AI vision endpoints"),
    ("ai:manage_prompts", "Create/activate AI prompt templates"),
    ("documents:write", "Upload and delete own documents"),
    ("admin:users", "Manage users (admin console)"),
    ("admin:audit", "View audit logs"),
    ("admin:usage", "View global AI/OCR usage"),
)

_USER_CODES: tuple[str, ...] = (
    "ocr:run",
    "ai:chat",
    "ai:vision",
    "documents:write",
)


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role",
            "permission_id",
            name="uq_role_permissions_role_perm",
        ),
    )

    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": _PERMISSION_IDS[code],
                "code": code,
                "description": description,
            }
            for code, description in _PERMISSION_ROWS
        ],
    )

    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("role", user_role),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )

    rp_rows: list[dict] = []
    # admin → all
    for i, (code, _) in enumerate(_PERMISSION_ROWS, start=1):
        rp_rows.append(
            {
                "id": uuid.UUID(f"a2000000-0000-4000-8000-{i:012d}"),
                "role": "admin",
                "permission_id": _PERMISSION_IDS[code],
            }
        )
    # user → subset
    for j, code in enumerate(_USER_CODES, start=1):
        rp_rows.append(
            {
                "id": uuid.UUID(f"a2000000-0000-4000-9000-{j:012d}"),
                "role": "user",
                "permission_id": _PERMISSION_IDS[code],
            }
        )

    op.bulk_insert(role_permissions_table, rp_rows)


def downgrade() -> None:
    op.drop_table("role_permissions")
    op.drop_table("permissions")
