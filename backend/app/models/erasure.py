"""Erasure job ORM (T-17.01 / B-P1-ERASURE / SPIKE_DATA_RETENTION)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ErasureJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ErasureJob(Base):
    __tablename__ = "erasure_jobs"
    __table_args__ = (
        Index("ix_erasure_jobs_target_created", "target_user_id", "created_at"),
        Index("ix_erasure_jobs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # ["account"] | ["documents"] | both
    scopes: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default='["account"]',
    )
    status: Mapped[ErasureJobStatus] = mapped_column(
        Enum(ErasureJobStatus, name="erasure_job_status", native_enum=True),
        nullable=False,
        server_default=ErasureJobStatus.queued.value,
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
