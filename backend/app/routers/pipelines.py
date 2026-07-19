"""Pipeline routes (T-6.02 / SDS §9.7). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import get_local_storage
from app.adapters.queue_publisher import QueuePublisher
from app.core.deps import CurrentUser, get_db
from app.schemas.pipeline import (
    PipelineRunCreate,
    PipelineRunCreated,
    PipelineRunPage,
    PipelineRunRead,
    to_pipeline_run_created,
    to_pipeline_run_read,
)
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def get_pipeline_service(db: Session = Depends(get_db)) -> PipelineService:
    return PipelineService(
        db,
        queue=QueuePublisher(),
        storage=get_local_storage(),
    )


@router.post(
    "/runs",
    response_model=PipelineRunCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_pipeline_run(
    body: PipelineRunCreate,
    user: CurrentUser,
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineRunCreated:
    ai = body.ai.model_dump(exclude_none=True) if body.ai is not None else None
    run = service.create_run(
        actor=user,
        document_id=body.document_id,
        ocr_options=body.ocr_options,
        ai=ai,
    )
    await service.enqueue_run(run.id)
    return to_pipeline_run_created(run)


@router.get("/runs", response_model=PipelineRunPage)
def list_pipeline_runs(
    user: CurrentUser,
    service: PipelineService = Depends(get_pipeline_service),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PipelineRunPage:
    rows, params, total = service.list_mine(
        owner=user,
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return PipelineRunPage(
        items=[to_pipeline_run_read(r) for r in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/runs/{run_id}", response_model=PipelineRunRead)
def get_pipeline_run(
    run_id: uuid.UUID,
    user: CurrentUser,
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineRunRead:
    return to_pipeline_run_read(service.get_for_actor(actor=user, run_id=run_id))
