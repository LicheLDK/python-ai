"""ARQ worker settings (T-4.02 / T-4.05 / T-4.09 / SDS ADR-010).

Run: ``arq app.workers.settings.WorkerSettings``
"""

from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.erasure_jobs import run_erasure_job
from app.workers.noop_jobs import noop_job
from app.workers.ocr_jobs import run_ocr_job
from app.workers.pipeline_jobs import run_pipeline
from app.workers.reconcile_jobs import reconcile_stale_ocr_jobs
from app.workers.stats_jobs import materialize_daily_stats


def redis_settings_from_url(url: str | None = None) -> RedisSettings:
    return RedisSettings.from_dsn(url or settings.redis_url)


def _cron_jobs() -> list:
    jobs: list = []
    if settings.ocr_reconcile_enabled:
        # Every minute at :00 — scan stale queued/running OCR rows (T-4.09).
        jobs.append(
            cron(
                reconcile_stale_ocr_jobs,
                second=0,
                unique=True,
                run_at_startup=False,
                timeout=120,
                max_tries=1,
                keep_result=300,
            )
        )
    if settings.stats_materialize_enabled:
        # Every 10 minutes — rebuild today's/yesterday's stat_daily (T-7.02).
        jobs.append(
            cron(
                materialize_daily_stats,
                minute={0, 10, 20, 30, 40, 50},
                second=30,
                unique=True,
                run_at_startup=False,
                timeout=300,
                max_tries=1,
                keep_result=600,
            )
        )
    return jobs


class WorkerSettings:
    """Discovered by the ``arq`` CLI."""

    functions = [
        noop_job,
        run_ocr_job,
        run_pipeline,
        run_erasure_job,
        reconcile_stale_ocr_jobs,
        materialize_daily_stats,
    ]
    cron_jobs = _cron_jobs()
    redis_settings = redis_settings_from_url()
    # Keep results long enough for tests / local debugging of enqueue round-trip.
    keep_result = 3600
    max_jobs = 10
    # OCR can be slow on CPU (model load + inference).
    job_timeout = 600
