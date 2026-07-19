"""T-4.02: enqueue no-op job and run it via ARQ burst worker."""

from __future__ import annotations

import asyncio

import pytest
from arq.worker import Worker

from app.adapters.queue_publisher import QueuePublisher
from app.core.config import settings
from app.workers.noop_jobs import noop_job
from app.workers.settings import redis_settings_from_url


@pytest.mark.unit
def test_enqueued_noop_job_runs() -> None:
    asyncio.run(_enqueued_noop_job_runs())


async def _enqueued_noop_job_runs() -> None:
    publisher = QueuePublisher(redis_url=settings.redis_url)
    try:
        job = await publisher.enqueue_noop(message="t-4.02")
        assert job is not None
        assert job.job_id

        worker = Worker(
            functions=[noop_job],
            redis_settings=redis_settings_from_url(settings.redis_url),
            handle_signals=False,
            burst=True,
            keep_result=3600,
        )
        await worker.async_run()

        result = await job.result(timeout=10)
        assert result == {"ok": True, "message": "t-4.02"}
    finally:
        await publisher.aclose()
