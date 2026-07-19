"""ARQ queue publisher adapter (T-4.02 / SDS §5.16)."""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from arq.jobs import Job

from app.core.config import settings
from app.workers.noop_jobs import noop_job
from app.workers.settings import redis_settings_from_url

NOOP_JOB_NAME = noop_job.__name__
OCR_JOB_NAME = "run_ocr_job"
PIPELINE_JOB_NAME = "run_pipeline"
ERASURE_JOB_NAME = "run_erasure_job"


class QueuePublisher:
    """Thin wrapper around ARQ ``enqueue_job`` for services to call."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_settings: RedisSettings = redis_settings_from_url(redis_url)
        self._pool: ArqRedis | None = None

    async def connect(self) -> ArqRedis:
        if self._pool is None:
            self._pool = await create_pool(self._redis_settings)
        return self._pool

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

    async def enqueue(self, function: str, *args: Any, **kwargs: Any) -> Job | None:
        redis = await self.connect()
        return await redis.enqueue_job(function, *args, **kwargs)

    async def enqueue_noop(self, *, message: str = "ping") -> Job | None:
        """Enqueue the T-4.02 smoke job."""
        return await self.enqueue(NOOP_JOB_NAME, message)

    async def enqueue_ocr_job(
        self,
        job_id: str,
        *,
        defer_by: float | None = None,
        attempt: int | None = None,
    ) -> Job | None:
        """Enqueue OCR worker handler (T-4.05 / T-4.06 backoff / T-4.09)."""
        arq_id = (
            f"ocr:{job_id}"
            if attempt is None
            else f"ocr:{job_id}:a{attempt}"
        )
        kwargs: dict[str, Any] = {"_job_id": arq_id}
        if defer_by is not None:
            kwargs["_defer_by"] = defer_by
        return await self.enqueue(OCR_JOB_NAME, job_id, **kwargs)

    async def enqueue_pipeline_run(self, run_id: str) -> Job | None:
        """Enqueue pipeline worker handler (T-6.02)."""
        return await self.enqueue(
            PIPELINE_JOB_NAME,
            run_id,
            _job_id=f"pipeline:{run_id}",
        )

    async def enqueue_erasure_job(self, job_id: str) -> Job | None:
        """Enqueue erasure worker handler (T-17.04)."""
        return await self.enqueue(
            ERASURE_JOB_NAME,
            job_id,
            _job_id=f"erasure:{job_id}",
        )
