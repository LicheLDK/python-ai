"""Stats materialize job (T-7.02 / SDS §9.8).

Cron: rebuild today's (and yesterday's, for late events near midnight UTC)
stat_daily rows from OCR/AI/pipeline/audit sources. Idempotent delete+insert.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)


async def materialize_daily_stats(
    ctx: dict[str, Any],
    target_date: str | None = None,
) -> dict[str, Any]:
    """ARQ entrypoint. ``target_date`` (YYYY-MM-DD) overrides for backfill."""
    if not settings.stats_materialize_enabled:
        return {"skipped": True, "reason": "STATS_MATERIALIZE_ENABLED=false"}

    if target_date:
        days = [datetime.strptime(target_date, "%Y-%m-%d").date()]
    else:
        today = datetime.now(UTC).date()
        days = [today - timedelta(days=1), today]

    results: list[dict[str, Any]] = []
    with SessionLocal() as session:
        service = StatsService(session)
        for day in days:
            results.append(service.materialize_day(day))
        session.commit()

    logger.info("stats materialize done: %s", results)
    return {"skipped": False, "days": results}
