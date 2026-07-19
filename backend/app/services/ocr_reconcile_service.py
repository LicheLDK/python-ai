"""OCR job reconciler — Redis queue loss recovery (T-4.09 / SDS §10 Redis policy).

Ops behavior
------------
Redis AOF is optional. If the ARQ queue is flushed/lost while Postgres still has
``ocr_jobs`` in ``queued`` or ``running``, this reconciler periodically:

1. **stale queued** (``updated_at`` older than ``OCR_STALE_QUEUED_SECONDS``):
   re-enqueue ``run_ocr_job`` without changing status.
2. **stale running** (``started_at`` older than ``OCR_STALE_RUNNING_SECONDS``):
   assume worker crash → reset to ``queued`` (attempt_count unchanged) and re-enqueue.

Runs as an ARQ cron on the ``worker`` process (every minute when enabled).
Disable with ``OCR_RECONCILE_ENABLED=false``.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.ocr_job_repository import OcrJobRepository

logger = logging.getLogger(__name__)


@dataclass
class ReconcilePlan:
    """Job ids that should be enqueued after DB updates are committed."""

    requeue_ids: list[uuid.UUID] = field(default_factory=list)
    reset_running_ids: list[uuid.UUID] = field(default_factory=list)


class OcrReconcileService:
    def __init__(
        self,
        session: Session,
        *,
        jobs: OcrJobRepository | None = None,
        stale_queued_seconds: int | None = None,
        stale_running_seconds: int | None = None,
        batch_limit: int = 100,
    ) -> None:
        self._session = session
        self._jobs = jobs or OcrJobRepository(session)
        self._stale_queued_seconds = (
            stale_queued_seconds
            if stale_queued_seconds is not None
            else settings.ocr_stale_queued_seconds
        )
        self._stale_running_seconds = (
            stale_running_seconds
            if stale_running_seconds is not None
            else settings.ocr_stale_running_seconds
        )
        self._batch_limit = batch_limit

    def scan(self, *, now: datetime | None = None) -> ReconcilePlan:
        """Mutate stale rows in-session; caller commits then enqueues ``requeue_ids``."""
        now = now or datetime.now(UTC)
        plan = ReconcilePlan()

        queued_cutoff = now - timedelta(seconds=self._stale_queued_seconds)
        for job in self._jobs.list_stale_queued(
            older_than=queued_cutoff,
            limit=self._batch_limit,
        ):
            self._jobs.touch(job, at=now)
            plan.requeue_ids.append(job.id)
            logger.info(
                "ocr reconcile: requeue stale queued job_id=%s updated_at=%s",
                job.id,
                job.updated_at,
            )

        running_cutoff = now - timedelta(seconds=self._stale_running_seconds)
        for job in self._jobs.list_stale_running(
            older_than=running_cutoff,
            limit=self._batch_limit,
        ):
            self._jobs.mark_stale_requeue(
                job,
                note=(
                    "stale running job reset by reconciler "
                    f"(threshold={self._stale_running_seconds}s)"
                ),
            )
            self._jobs.touch(job, at=now)
            plan.reset_running_ids.append(job.id)
            plan.requeue_ids.append(job.id)
            logger.warning(
                "ocr reconcile: reset stale running job_id=%s started_at=%s",
                job.id,
                job.started_at,
            )

        return plan


def ocr_reconcile_arq_job_id(job_id: uuid.UUID) -> str:
    """Unique ARQ id so keep_result of a prior run does not block re-enqueue."""
    return f"ocr:r:{job_id}:{int(time.time())}"
