"""Admin erasure job routes (T-17.03 / B-P1-ERASURE). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.adapters.queue_publisher import QueuePublisher
from app.core.cookies import client_ip
from app.core.deps import AdminUser, get_db
from app.schemas.erasure import (
    ErasureJobCreate,
    ErasureJobRead,
    to_erasure_job_read,
)
from app.services.erasure_service import ErasureService

router = APIRouter(prefix="/erasure-jobs", tags=["admin-erasure"])


def get_erasure_service(db: Session = Depends(get_db)) -> ErasureService:
    return ErasureService(db, queue=QueuePublisher())


@router.post(
    "",
    response_model=ErasureJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_erasure_job(
    body: ErasureJobCreate,
    request: Request,
    admin: AdminUser,
    service: ErasureService = Depends(get_erasure_service),
) -> ErasureJobRead:
    job = service.request_admin_erasure(
        actor=admin,
        target_user_id=body.user_id,
        scopes=body.scopes,
        ip=client_ip(request),
    )
    await service.enqueue_job(job.id)
    return to_erasure_job_read(job)


@router.get("/{job_id}", response_model=ErasureJobRead)
def get_erasure_job(
    job_id: uuid.UUID,
    admin: AdminUser,
    service: ErasureService = Depends(get_erasure_service),
) -> ErasureJobRead:
    return to_erasure_job_read(service.get_for_actor(actor=admin, job_id=job_id))
