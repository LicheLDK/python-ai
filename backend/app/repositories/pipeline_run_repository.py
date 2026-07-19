"""PipelineRunRepository — DB access only (T-6.01 / SDS §10.14)."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.pipeline import PipelineRun, PipelineRunStatus, initial_stages
from app.utils.pagination import PageParams


class PipelineRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, run_id: uuid.UUID) -> PipelineRun | None:
        return self._session.get(PipelineRun, run_id)

    def create(
        self,
        *,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        stages: list[dict[str, Any]] | None = None,
        run_id: uuid.UUID | None = None,
        status: PipelineRunStatus = PipelineRunStatus.queued,
    ) -> PipelineRun:
        row = PipelineRun(
            id=run_id or uuid.uuid4(),
            user_id=user_id,
            document_id=document_id,
            status=status,
            stages=stages if stages is not None else initial_stages(),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_user(
        self,
        *,
        user_id: uuid.UUID,
        page: PageParams,
        status: PipelineRunStatus | None = None,
    ) -> tuple[list[PipelineRun], int]:
        filters = [PipelineRun.user_id == user_id]
        if status is not None:
            filters.append(PipelineRun.status == status)

        count_stmt = select(func.count()).select_from(PipelineRun).where(*filters)
        list_stmt = (
            select(PipelineRun)
            .where(*filters)
            .order_by(PipelineRun.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(self._session.scalars(list_stmt).all())
        return rows, total

    def mark_running(self, run: PipelineRun) -> PipelineRun:
        run.status = PipelineRunStatus.running
        run.error = None
        run.finished_at = None
        self._session.flush()
        return run

    def mark_succeeded(
        self,
        run: PipelineRun,
        *,
        finished_at: datetime,
        stages: list[dict[str, Any]],
    ) -> PipelineRun:
        run.status = PipelineRunStatus.succeeded
        run.stages = copy.deepcopy(stages)
        flag_modified(run, "stages")
        run.error = None
        run.finished_at = finished_at
        self._session.flush()
        return run

    def mark_failed(
        self,
        run: PipelineRun,
        *,
        finished_at: datetime,
        stages: list[dict[str, Any]],
        error: str,
    ) -> PipelineRun:
        run.status = PipelineRunStatus.failed
        run.stages = copy.deepcopy(stages)
        flag_modified(run, "stages")
        run.error = error
        run.finished_at = finished_at
        self._session.flush()
        return run

    def update_stages(
        self,
        run: PipelineRun,
        stages: list[dict[str, Any]],
        *,
        ocr_job_id: uuid.UUID | None = None,
        ai_request_id: uuid.UUID | None = None,
    ) -> PipelineRun:
        run.stages = copy.deepcopy(stages)
        flag_modified(run, "stages")
        if ocr_job_id is not None:
            run.ocr_job_id = ocr_job_id
        if ai_request_id is not None:
            run.ai_request_id = ai_request_id
        self._session.flush()
        return run
