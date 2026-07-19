"""Admin seed entrypoint (T-1.07).

Idempotent: creates default admin from env if email is absent.
Run: ``python -m app.scripts.seed_admin`` from ``backend/``.
"""

from __future__ import annotations

import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import UserRole, UserStatus
from app.repositories.user_repository import UserRepository


def seed_admin() -> int:
    settings = get_settings()
    email = (settings.seed_admin_email or "").strip().lower()
    password = settings.seed_admin_password or ""
    name = (settings.seed_admin_name or "Admin").strip() or "Admin"

    if not email:
        print("seed: SEED_ADMIN_EMAIL is required", file=sys.stderr)
        return 1
    if len(password) < 8:
        print(
            "seed: SEED_ADMIN_PASSWORD must be at least 8 characters",
            file=sys.stderr,
        )
        return 1

    session = SessionLocal()
    try:
        users = UserRepository(session)
        existing = users.get_by_email(email)
        if existing is not None:
            # Idempotent: leave password as-is; ensure admin + active.
            changed = False
            if existing.role != UserRole.admin:
                existing.role = UserRole.admin
                changed = True
            if existing.status != UserStatus.active:
                existing.status = UserStatus.active
                changed = True
            if changed:
                session.commit()
                print(f"seed: updated existing user to admin/active: {email}")
            else:
                print(f"seed: admin already present, skipping: {email}")
            return 0

        user = users.create(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=UserRole.admin,
            status=UserStatus.active,
        )
        session.commit()
        print(f"seed: created admin user id={user.id} email={email}")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI exit path
        session.rollback()
        print(f"seed: failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


def main() -> None:
    raise SystemExit(seed_admin())


if __name__ == "__main__":
    main()
