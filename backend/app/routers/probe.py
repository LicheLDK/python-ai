"""Temporary protected stubs for T-1.05 exit criteria (401/403).

Formal profile API is T-2.02 (`/users/me`). These probes verify Depends wiring.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser
from app.schemas.user import UserRead

router = APIRouter(prefix="/_probe", tags=["probe"])


def _user_read(user) -> UserRead:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    status_value = (
        user.status.value if hasattr(user.status, "value") else str(user.status)
    )
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role,
        status=status_value,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/me", response_model=UserRead)
def probe_me(user: CurrentUser) -> UserRead:
    """Any authenticated active user."""
    return _user_read(user)


@router.get("/admin")
def probe_admin(user: AdminUser) -> dict[str, str]:
    """Admin role only — non-admin → 403."""
    return {"status": "ok", "role": "admin", "user_id": str(user.id)}
