"""RBAC migration/seed checks (T-2.01)."""

from __future__ import annotations

from sqlalchemy import text

from app.core.database import engine
from app.core.permissions_catalog import PERMISSION_SEED, USER_ROLE_PERMISSION_CODES


def test_permissions_seeded() -> None:
    codes = {code for code, _ in PERMISSION_SEED}
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT code FROM permissions ORDER BY code")).fetchall()
        db_codes = {r[0] for r in rows}
        assert db_codes == codes

        admin_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM role_permissions WHERE role = 'admin'"
            )
        ).scalar_one()
        assert admin_count == len(codes)

        user_rows = conn.execute(
            text(
                """
                SELECT p.code
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role = 'user'
                ORDER BY p.code
                """
            )
        ).fetchall()
        user_codes = {r[0] for r in user_rows}
        assert user_codes == set(USER_ROLE_PERMISSION_CODES)
