"""OCR ORM models (T-4.01 / SDS §10.9–10.10).

Job orchestration / worker handlers belong to T-4.05+.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OcrJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class OcrJob(Base):
    __tablename__ = "ocr_jobs"
    __table_args__ = (
        Index("ix_ocr_jobs_user_created", "user_id", "created_at"),
        Index("ix_ocr_jobs_status_created", "status", "created_at"),
        Index("ix_ocr_jobs_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[OcrJobStatus] = mapped_column(
        Enum(OcrJobStatus, name="ocr_job_status", native_enum=True),
        nullable=False,
        server_default=OcrJobStatus.queued.value,
    )
    options: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    results: Mapped[list[OcrResult]] = relationship(
        "OcrResult",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class OcrResult(Base):
    __tablename__ = "ocr_results"
    __table_args__ = (
        UniqueConstraint("job_id", "page", name="uq_ocr_results_job_page"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ocr_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    boxes: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[OcrJob] = relationship("OcrJob", back_populates="results")
