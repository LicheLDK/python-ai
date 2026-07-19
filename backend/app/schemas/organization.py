"""Organization DTOs (T-16.04 / B-1.2-TENANT)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    ai_rate_limit_max: int | None = None
    ai_rate_limit_window_seconds: int | None = None
    effective_ai_rate_limit_max: int
    effective_ai_rate_limit_window_seconds: int
    branding: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class OrganizationMeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=64)
    ai_rate_limit_max: int | None = Field(default=None, ge=1)
    ai_rate_limit_window_seconds: int | None = Field(default=None, ge=1)
    branding: dict[str, Any] | None = None


class OrganizationAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: Literal["active", "inactive"] | None = None
    ai_rate_limit_max: int | None = Field(default=None, ge=1)
    ai_rate_limit_window_seconds: int | None = Field(default=None, ge=1)
    clear_ai_rate_limits: bool = False
    branding: dict[str, Any] | None = None


OrganizationPage = Page[OrganizationRead]


def to_organization_read(
    org,
    *,
    default_ai_max: int,
    default_ai_window: int,
) -> OrganizationRead:
    status = org.status.value if hasattr(org.status, "value") else str(org.status)
    eff_max = (
        int(org.ai_rate_limit_max)
        if org.ai_rate_limit_max is not None
        else int(default_ai_max)
    )
    eff_window = (
        int(org.ai_rate_limit_window_seconds)
        if org.ai_rate_limit_window_seconds is not None
        else int(default_ai_window)
    )
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=status,
        ai_rate_limit_max=org.ai_rate_limit_max,
        ai_rate_limit_window_seconds=org.ai_rate_limit_window_seconds,
        effective_ai_rate_limit_max=eff_max,
        effective_ai_rate_limit_window_seconds=eff_window,
        branding=dict(org.branding or {}),
        created_at=org.created_at,
        updated_at=org.updated_at,
    )
