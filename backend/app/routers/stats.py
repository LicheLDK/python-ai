"""Statistics routes (T-7.03 / T-7.04 / SDS §9.8). Controller only."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.core.redis import get_redis
from app.schemas.stats import (
    DailyStatsResponse,
    MonthlyStatPoint,
    MonthlyStatsResponse,
    StatsSummaryResponse,
    to_stat_point,
)
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


def get_stats_service(db: Session = Depends(get_db)) -> StatsService:
    return StatsService(db, redis_client=get_redis())


@router.get("/daily", response_model=DailyStatsResponse)
def daily_stats(
    user: CurrentUser,
    service: StatsService = Depends(get_stats_service),
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    metric: str | None = Query(default=None),
    scope: str = Query(default="self"),
) -> DailyStatsResponse:
    rows = service.daily(
        actor=user,
        date_from=date_from,
        date_to=date_to,
        metric=metric,
        scope=scope,
    )
    return DailyStatsResponse(points=[to_stat_point(r) for r in rows])


@router.get("/monthly", response_model=MonthlyStatsResponse)
def monthly_stats(
    user: CurrentUser,
    service: StatsService = Depends(get_stats_service),
    from_month: str = Query(),
    to_month: str = Query(),
    metric: str | None = Query(default=None),
    scope: str = Query(default="self"),
) -> MonthlyStatsResponse:
    rollups = service.monthly(
        actor=user,
        from_month=from_month,
        to_month=to_month,
        metric=metric,
        scope=scope,
    )
    return MonthlyStatsResponse(
        points=[
            MonthlyStatPoint(month=month, metric=metric_name, value=value)
            for month, metric_name, value in rollups
        ]
    )


@router.get("/summary", response_model=StatsSummaryResponse)
def stats_summary(
    user: CurrentUser,
    service: StatsService = Depends(get_stats_service),
) -> StatsSummaryResponse:
    return StatsSummaryResponse(**service.summary(actor=user))


@router.get("/export")
def export_stats(
    user: CurrentUser,
    service: StatsService = Depends(get_stats_service),
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    metric: str | None = Query(default=None),
    scope: str = Query(default="self"),
    format: str = Query(default="csv"),
) -> Response:
    # Only CSV in v1 (SDS §9.8 P1).
    csv_body = service.export_csv(
        actor=user,
        date_from=date_from,
        date_to=date_to,
        metric=metric,
        scope=scope,
    )
    filename = f"stats_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
