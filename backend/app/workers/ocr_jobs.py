"""OCR async job handler (T-4.05 / T-4.06 / T-4.07 / SDS §8.3).

Flow: StoragePort → (PDF split) → OpenCV preprocess → PaddleOCR → ocr_results.
On failure: exponential backoff re-enqueue until ``OCR_MAX_ATTEMPTS``, then failed.
Page-limit violations are permanent (no retry).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import get_local_storage
from app.adapters.ports import (
    ImagePreprocessPort,
    OcrEnginePort,
    OcrPageResult,
    PreprocessOptions,
    StoragePort,
)
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import DocumentStatus
from app.models.ocr import OcrJob, OcrJobStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.utils.pdf_pages import resolve_page_images
from app.workers.ocr_errors import OcrPermanentError

logger = logging.getLogger(__name__)

# Keep in sync with ``app.adapters.queue_publisher.OCR_JOB_NAME`` (avoid circular import).
_OCR_JOB_NAME = "run_ocr_job"


@dataclass(frozen=True, slots=True)
class OcrRunOutcome:
    """Result of one worker attempt."""

    status: str  # succeeded | failed | queued (retry scheduled)
    attempt_count: int
    error: str | None = None
    retry_delay_seconds: float | None = None

    @property
    def should_retry(self) -> bool:
        return self.status == OcrJobStatus.queued.value and self.retry_delay_seconds is not None


def compute_ocr_retry_delay_seconds(
    attempt_count: int,
    *,
    max_attempts: int | None = None,
    base_seconds: float | None = None,
) -> float | None:
    """Return defer seconds after a failed attempt, or None if attempts exhausted."""
    max_n = max_attempts if max_attempts is not None else settings.ocr_max_attempts
    base = base_seconds if base_seconds is not None else settings.ocr_retry_base_seconds
    if attempt_count >= max_n:
        return None
    return float(base) * (2 ** max(attempt_count - 1, 0))


class OcrJobRunner:
    """Synchronous OCR execution used by the ARQ worker (and tests)."""

    def __init__(
        self,
        session: Session,
        *,
        storage: StoragePort | None = None,
        preprocess: ImagePreprocessPort | None = None,
        ocr: OcrEnginePort | None = None,
        max_attempts: int | None = None,
        retry_base_seconds: float | None = None,
        max_pages: int | None = None,
    ) -> None:
        self._session = session
        self._jobs = OcrJobRepository(session)
        self._results = OcrResultRepository(session)
        self._documents = DocumentRepository(session)
        self._storage = storage or get_local_storage()
        self._max_attempts = (
            max_attempts if max_attempts is not None else settings.ocr_max_attempts
        )
        self._retry_base_seconds = (
            retry_base_seconds
            if retry_base_seconds is not None
            else settings.ocr_retry_base_seconds
        )
        self._max_pages = max_pages if max_pages is not None else settings.ocr_max_pages
        if preprocess is None:
            from app.adapters.opencv_preprocess_adapter import OpenCvPreprocessAdapter

            preprocess = OpenCvPreprocessAdapter()
        if ocr is None:
            from app.adapters.paddle_ocr_adapter import PaddleOcrAdapter

            ocr = PaddleOcrAdapter()
        self._preprocess = preprocess
        self._ocr = ocr

    def run(self, job_id: uuid.UUID) -> OcrRunOutcome:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            logger.warning("ocr job missing: %s", job_id)
            return OcrRunOutcome(status="missing", attempt_count=0)

        if job.status in (OcrJobStatus.succeeded, OcrJobStatus.cancelled):
            logger.info("ocr job skip terminal status=%s id=%s", job.status, job_id)
            return OcrRunOutcome(
                status=job.status.value,
                attempt_count=int(job.attempt_count or 0),
            )

        if job.status == OcrJobStatus.failed:
            logger.info("ocr job skip already failed id=%s", job_id)
            return OcrRunOutcome(
                status=OcrJobStatus.failed.value,
                attempt_count=int(job.attempt_count or 0),
                error=job.error,
            )

        now = datetime.now(UTC)
        self._jobs.mark_running(job, started_at=now)
        self._session.commit()
        attempt = int(job.attempt_count or 0)

        try:
            page_results = self._process(job)
            self._results.delete_for_job(job.id)
            for page_result in page_results:
                self._results.create(
                    job_id=job.id,
                    page=page_result.page,
                    text=page_result.text,
                    boxes=page_result.boxes,
                    confidence=page_result.confidence,
                )
            self._jobs.mark_succeeded(job, finished_at=datetime.now(UTC))
            self._session.commit()
            return OcrRunOutcome(
                status=OcrJobStatus.succeeded.value,
                attempt_count=attempt,
            )
        except OcrPermanentError as exc:
            err = str(exc) or exc.__class__.__name__
            logger.warning("ocr job permanent failure id=%s: %s", job_id, err)
            self._session.rollback()
            job = self._jobs.get_by_id(job_id)
            if job is None:
                return OcrRunOutcome(status="missing", attempt_count=attempt, error=err)
            self._jobs.mark_failed(
                job,
                finished_at=datetime.now(UTC),
                error=err,
            )
            self._session.commit()
            return OcrRunOutcome(
                status=OcrJobStatus.failed.value,
                attempt_count=attempt,
                error=err,
            )
        except Exception as exc:  # noqa: BLE001 — persist failure / schedule retry
            err = str(exc) or exc.__class__.__name__
            logger.exception("ocr job attempt failed id=%s attempt=%s", job_id, attempt)
            self._session.rollback()
            job = self._jobs.get_by_id(job_id)
            if job is None:
                return OcrRunOutcome(status="missing", attempt_count=attempt, error=err)

            delay = compute_ocr_retry_delay_seconds(
                attempt,
                max_attempts=self._max_attempts,
                base_seconds=self._retry_base_seconds,
            )
            if delay is not None:
                self._jobs.mark_retry_queued(job, error=err)
                self._session.commit()
                return OcrRunOutcome(
                    status=OcrJobStatus.queued.value,
                    attempt_count=attempt,
                    error=err,
                    retry_delay_seconds=delay,
                )

            self._jobs.mark_failed(
                job,
                finished_at=datetime.now(UTC),
                error=err,
            )
            self._session.commit()
            return OcrRunOutcome(
                status=OcrJobStatus.failed.value,
                attempt_count=attempt,
                error=err,
            )

    def _process(self, job: OcrJob) -> list[OcrPageResult]:
        doc = self._documents.get_by_id(job.document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise RuntimeError("Document not found for OCR job")
        raw = self._storage.get(doc.storage_key)
        total_pages, page_images = resolve_page_images(
            raw,
            mime_type=doc.mime_type,
            max_pages=self._max_pages,
        )
        if total_pages > self._max_pages:
            raise OcrPermanentError(
                f"Document exceeds OCR page limit "
                f"(page_count={total_pages}, max_pages={self._max_pages})"
            )

        options = dict(job.options or {})
        preprocess_opts = self._preprocess_options(options)
        lang = options.get("lang")
        results: list[OcrPageResult] = []
        for idx, image_bytes in enumerate(page_images, start=1):
            processed = self._preprocess.process(image_bytes, preprocess_opts)
            results.append(self._ocr.extract(processed, lang=lang, page=idx))
        return results

    @staticmethod
    def _preprocess_options(options: dict[str, Any]) -> PreprocessOptions:
        raw = options.get("preprocess") or {}
        if not isinstance(raw, dict):
            raw = {}
        return PreprocessOptions(
            deskew=bool(raw.get("deskew", False)),
            denoise=bool(raw.get("denoise", False)),
            contrast=bool(raw.get("contrast", False)),
        )


async def run_ocr_job(ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
    """ARQ entrypoint: ``enqueue('run_ocr_job', job_id)``."""
    runner_factory = ctx.get("ocr_runner_factory")
    with SessionLocal() as session:
        if callable(runner_factory):
            runner = runner_factory(session)
        else:
            runner = OcrJobRunner(session)
        outcome = runner.run(uuid.UUID(job_id))

    if outcome.should_retry:
        redis = ctx.get("redis")
        if redis is not None:
            await redis.enqueue_job(
                _OCR_JOB_NAME,
                job_id,
                _defer_by=outcome.retry_delay_seconds,
            )
        else:
            logger.error(
                "ocr retry requested but ctx['redis'] missing job_id=%s delay=%s",
                job_id,
                outcome.retry_delay_seconds,
            )

    return {
        "job_id": job_id,
        "status": outcome.status,
        "attempt_count": outcome.attempt_count,
        "retry_delay_seconds": outcome.retry_delay_seconds,
        "error": outcome.error,
    }
