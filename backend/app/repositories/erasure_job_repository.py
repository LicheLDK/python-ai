"""ErasureJobRepository — DB access only (T-17.02)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.erasure import ErasureJob, ErasureJobStatus


class ErasureJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, job_id: uuid.UUID) -> ErasureJob | None:
        return self._session.get(ErasureJob, job_id)

    def create(
        self,
        *,
        target_user_id: uuid.UUID,
        requested_by_id: uuid.UUID | None,
        scopes: Sequence[str],
        job_id: uuid.UUID | None = None,
    ) -> ErasureJob:
        row = ErasureJob(
            id=job_id or uuid.uuid4(),
            target_user_id=target_user_id,
            requested_by_id=requested_by_id,
            scopes=list(scopes),
            status=ErasureJobStatus.queued,
            stats={},
        )
        self._session.add(row)
        self._session.flush()
        return row

    def has_active_for_user(self, user_id: uuid.UUID) -> bool:
        stmt = (
            select(ErasureJob.id)
            .where(
                ErasureJob.target_user_id == user_id,
                ErasureJob.status.in_(
                    [ErasureJobStatus.queued, ErasureJobStatus.running]
                ),
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first() is not None

    def mark_running(self, job: ErasureJob, *, started_at: datetime) -> ErasureJob:
        job.status = ErasureJobStatus.running
        if job.started_at is None:
            job.started_at = started_at
        job.error = None
        self._session.flush()
        return job

    def mark_succeeded(
        self,
        job: ErasureJob,
        *,
        finished_at: datetime,
        stats: dict[str, Any],
    ) -> ErasureJob:
        job.status = ErasureJobStatus.succeeded
        job.finished_at = finished_at
        job.stats = stats
        job.error = None
        self._session.flush()
        return job

    def mark_failed(
        self,
        job: ErasureJob,
        *,
        finished_at: datetime,
        error: str,
        stats: dict[str, Any] | None = None,
    ) -> ErasureJob:
        job.status = ErasureJobStatus.failed
        job.finished_at = finished_at
        job.error = error
        if stats is not None:
            job.stats = stats
        self._session.flush()
        return job
