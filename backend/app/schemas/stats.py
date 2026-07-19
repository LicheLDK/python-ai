"""Statistics DTOs (T-7.03 / SDS §9.8)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class StatPoint(BaseModel):
    date: date
    metric: str
    value: float
    dimensions: dict[str, Any] = Field(default_factory=dict)


class DailyStatsResponse(BaseModel):
    points: list[StatPoint]


class MonthlyStatPoint(BaseModel):
    month: str  # YYYY-MM
    metric: str
    value: float


class MonthlyStatsResponse(BaseModel):
    points: list[MonthlyStatPoint]


class StatsSummaryResponse(BaseModel):
    ocr_jobs_today: int
    ai_requests_today: int
    tokens_today: float
    error_rate_today: float


def to_stat_point(row) -> StatPoint:
    return StatPoint(
        date=row.date,
        metric=row.metric,
        value=float(row.value),
        dimensions=dict(row.dimensions or {}),
    )
