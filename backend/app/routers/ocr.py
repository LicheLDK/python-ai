"""OCR routes (T-4.05 / SDS §9.5). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import get_local_storage
from app.adapters.queue_publisher import QueuePublisher
from app.core.deps import CurrentUser, get_db
from app.schemas.ocr import (
    OcrJobCreate,
    OcrJobCreated,
    OcrJobPage,
    OcrJobRead,
    OcrJobResultsRead,
    to_ocr_job_created,
    to_ocr_job_read,
    to_ocr_results_read,
)
from app.services.ocr_service import OcrService

router = APIRouter(prefix="/ocr", tags=["ocr"])


def get_ocr_service(db: Session = Depends(get_db)) -> OcrService:
    return OcrService(db, queue=QueuePublisher(), storage=get_local_storage())


@router.post(
    "/jobs",
    response_model=OcrJobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ocr_job(
    body: OcrJobCreate,
    user: CurrentUser,
    service: OcrService = Depends(get_ocr_service),
) -> OcrJobCreated:
    options: dict | None = None
    if body.options is not None:
        options = body.options.model_dump(exclude_none=True)
    job = service.create_job(
        actor=user,
        document_id=body.document_id,
        options=options,
    )
    await service.enqueue_job(job.id)
    return to_ocr_job_created(job)


@router.get("/jobs", response_model=OcrJobPage)
def list_ocr_jobs(
    user: CurrentUser,
    service: OcrService = Depends(get_ocr_service),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OcrJobPage:
    rows, params, total = service.list_mine(
        owner=user,
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return OcrJobPage(
        items=[to_ocr_job_read(j) for j in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/jobs/{job_id}", response_model=OcrJobRead)
def get_ocr_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    service: OcrService = Depends(get_ocr_service),
) -> OcrJobRead:
    return to_ocr_job_read(service.get_for_actor(actor=user, job_id=job_id))


@router.get("/jobs/{job_id}/results", response_model=OcrJobResultsRead)
def get_ocr_job_results(
    job_id: uuid.UUID,
    user: CurrentUser,
    service: OcrService = Depends(get_ocr_service),
) -> OcrJobResultsRead:
    job, rows = service.get_results_for_actor(actor=user, job_id=job_id)
    return to_ocr_results_read(job.id, rows)
