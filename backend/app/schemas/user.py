"""User DTOs (T-1.04 / T-2.02 / SDS §9.3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    """Public user profile returned by auth and /users/me."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    org_id: uuid.UUID
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    """PATCH /users/me — email change is not allowed in v1 (extra=forbid)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)


class RegisterResponse(BaseModel):
    """POST /auth/register 201 body."""

    user: UserRead = Field(..., description="Created user")


def to_user_read(user) -> UserRead:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    status_value = (
        user.status.value if hasattr(user.status, "value") else str(user.status)
    )
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        org_id=user.org_id,
        role=role,
        status=status_value,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
