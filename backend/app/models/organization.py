"""Organization ORM model (T-16.01 / B-1.2-TENANT / ADR-015 additive)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrganizationStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(OrganizationStatus, name="organization_status", native_enum=True),
        nullable=False,
        server_default=OrganizationStatus.active.value,
    )
    # NULL → fall back to Settings.ai_rate_limit_*
    ai_rate_limit_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_rate_limit_window_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    # Soft branding bag (logo_url, primary_color, …) — UI deferred
    branding: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
