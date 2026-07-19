"""OcrJobRepository — DB access only (T-4.05 / SDS §10.9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ocr import OcrJob, OcrJobStatus
from app.utils.pagination import PageParams


class OcrJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, job_id: uuid.UUID) -> OcrJob | None:
        return self._session.get(OcrJob, job_id)

    def create(
        self,
        *,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        options: dict[str, Any] | None = None,
        job_id: uuid.UUID | None = None,
        status: OcrJobStatus = OcrJobStatus.queued,
    ) -> OcrJob:
        row = OcrJob(
            id=job_id or uuid.uuid4(),
            document_id=document_id,
            user_id=user_id,
            status=status,
            options=options or {},
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        page: PageParams,
        status: OcrJobStatus | None = None,
    ) -> tuple[list[OcrJob], int]:
        filters = [OcrJob.user_id == user_id]
        if status is not None:
            filters.append(OcrJob.status == status)

        count_stmt = select(func.count()).select_from(OcrJob).where(*filters)
        list_stmt = (
            select(OcrJob)
            .where(*filters)
            .order_by(OcrJob.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(self._session.scalars(list_stmt).all())
        return rows, total

    def list_all(
        self,
        *,
        page: PageParams,
        status: OcrJobStatus | None = None,
        user_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[OcrJob], int]:
        """Global OCR job list for admin (T-10.01)."""
        filters: list = []
        if status is not None:
            filters.append(OcrJob.status == status)
        if user_id is not None:
            filters.append(OcrJob.user_id == user_id)
        if date_from is not None:
            filters.append(OcrJob.created_at >= date_from)
        if date_to is not None:
            filters.append(OcrJob.created_at <= date_to)

        count_stmt = select(func.count()).select_from(OcrJob)
        list_stmt = select(OcrJob).order_by(OcrJob.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)
        list_stmt = list_stmt.offset(page.offset).limit(page.limit)

        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(self._session.scalars(list_stmt).all())
        return rows, total

    def mark_running(self, job: OcrJob, *, started_at: datetime) -> OcrJob:
        job.status = OcrJobStatus.running
        if job.started_at is None:
            job.started_at = started_at
        job.attempt_count = int(job.attempt_count or 0) + 1
        job.error = None
        job.finished_at = None
        self._session.flush()
        return job

    def mark_succeeded(self, job: OcrJob, *, finished_at: datetime) -> OcrJob:
        job.status = OcrJobStatus.succeeded
        job.finished_at = finished_at
        job.error = None
        self._session.flush()
        return job

    def mark_failed(
        self,
        job: OcrJob,
        *,
        finished_at: datetime,
        error: str,
    ) -> OcrJob:
        job.status = OcrJobStatus.failed
        job.finished_at = finished_at
        job.error = error[:4000]
        self._session.flush()
        return job

    def mark_retry_queued(self, job: OcrJob, *, error: str) -> OcrJob:
        """Persist last error and return to queued for deferred re-enqueue."""
        job.status = OcrJobStatus.queued
        job.error = error[:4000]
        job.finished_at = None
        self._session.flush()
        return job

    def mark_stale_requeue(self, job: OcrJob, *, note: str) -> OcrJob:
        """Reset a stuck running job to queued without bumping attempt_count."""
        job.status = OcrJobStatus.queued
        job.error = note[:4000]
        job.finished_at = None
        self._session.flush()
        return job

    def touch(self, job: OcrJob, *, at: datetime) -> OcrJob:
        """Bump updated_at so reconciler does not thrash the same row every tick."""
        job.updated_at = at
        self._session.flush()
        return job

    def list_stale_queued(
        self,
        *,
        older_than: datetime,
        limit: int = 100,
    ) -> list[OcrJob]:
        stmt = (
            select(OcrJob)
            .where(
                OcrJob.status == OcrJobStatus.queued,
                OcrJob.updated_at < older_than,
            )
            .order_by(OcrJob.updated_at.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def list_stale_running(
        self,
        *,
        older_than: datetime,
        limit: int = 100,
    ) -> list[OcrJob]:
        # Prefer started_at; fall back to updated_at if missing.
        age_col = func.coalesce(OcrJob.started_at, OcrJob.updated_at)
        stmt = (
            select(OcrJob)
            .where(
                OcrJob.status == OcrJobStatus.running,
                age_col < older_than,
            )
            .order_by(age_col.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())
