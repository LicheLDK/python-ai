"""StatDaily ORM model (T-7.01 / SDS §10.16)."""

from __future__ import annotations

import uuid
from datetime import date as date_type, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Normative metric names (SDS §9.8).
METRIC_OCR_JOBS_COUNT = "ocr.jobs.count"
METRIC_OCR_JOBS_FAILED = "ocr.jobs.failed"
METRIC_OCR_LATENCY_AVG = "ocr.jobs.latency_ms.avg"
METRIC_AI_REQUESTS_COUNT = "ai.requests.count"
METRIC_AI_TOKENS_IN = "ai.tokens.in"
METRIC_AI_TOKENS_OUT = "ai.tokens.out"
METRIC_AI_COST_ESTIMATE = "ai.cost.estimate"
METRIC_PIPELINE_RUNS_COUNT = "pipeline.runs.count"
METRIC_AUTH_LOGIN_FAILED = "auth.login.failed"  # admin/global only

ALL_METRICS: tuple[str, ...] = (
    METRIC_OCR_JOBS_COUNT,
    METRIC_OCR_JOBS_FAILED,
    METRIC_OCR_LATENCY_AVG,
    METRIC_AI_REQUESTS_COUNT,
    METRIC_AI_TOKENS_IN,
    METRIC_AI_TOKENS_OUT,
    METRIC_AI_COST_ESTIMATE,
    METRIC_PIPELINE_RUNS_COUNT,
    METRIC_AUTH_LOGIN_FAILED,
)

ADMIN_ONLY_METRICS: frozenset[str] = frozenset({METRIC_AUTH_LOGIN_FAILED})


class StatDaily(Base):
    __tablename__ = "stat_daily"
    __table_args__ = (
        Index("ix_stat_daily_metric_date", "metric", "date"),
        Index("ix_stat_daily_user_date", "user_id", "date"),
        # Unique (date, metric, coalesce(user_id), dim_key) lives in migration
        # 0009 as an expression index (NULL user_id = global must collide).
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    dimensions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    dim_key: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        server_default="",
    )
    value: Mapped[float] = mapped_column(Numeric(24, 6), nullable=False)
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
