"""ARQ cron: reconcile stale OCR jobs after Redis queue loss (T-4.09)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.ocr_reconcile_service import (
    OcrReconcileService,
    ocr_reconcile_arq_job_id,
)

logger = logging.getLogger(__name__)

# Keep in sync with ``app.adapters.queue_publisher.OCR_JOB_NAME`` (avoid circular import).
_OCR_JOB_NAME = "run_ocr_job"


async def reconcile_stale_ocr_jobs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Periodic scan of stale ``queued`` / ``running`` OCR jobs → re-enqueue."""
    if not settings.ocr_reconcile_enabled:
        return {"skipped": True, "reason": "OCR_RECONCILE_ENABLED=false"}

    with SessionLocal() as session:
        plan = OcrReconcileService(session).scan()
        session.commit()

    redis = ctx.get("redis")
    enqueued = 0
    if redis is None:
        logger.error("ocr reconcile: ctx['redis'] missing; DB updated but not enqueued")
        return {
            "skipped": False,
            "planned": len(plan.requeue_ids),
            "reset_running": len(plan.reset_running_ids),
            "enqueued": 0,
            "error": "redis_missing",
        }

    for job_id in plan.requeue_ids:
        job = await redis.enqueue_job(
            _OCR_JOB_NAME,
            str(job_id),
            _job_id=ocr_reconcile_arq_job_id(job_id),
        )
        if job is not None:
            enqueued += 1

    logger.info(
        "ocr reconcile done planned=%s reset_running=%s enqueued=%s",
        len(plan.requeue_ids),
        len(plan.reset_running_ids),
        enqueued,
    )
    return {
        "skipped": False,
        "planned": len(plan.requeue_ids),
        "reset_running": len(plan.reset_running_ids),
        "enqueued": enqueued,
    }
