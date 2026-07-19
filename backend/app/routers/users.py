"""User profile routes (T-2.02 / SDS §9.3). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.adapters.queue_publisher import QueuePublisher
from app.core.deps import CurrentUser, get_db
from app.schemas.erasure import (
    ErasureJobAccepted,
    ErasureJobRead,
    to_erasure_job_accepted,
    to_erasure_job_read,
)
from app.schemas.user import UserRead, UserUpdateRequest, to_user_read
from app.services.erasure_service import ErasureService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_erasure_service(db: Session = Depends(get_db)) -> ErasureService:
    return ErasureService(db, queue=QueuePublisher())


@router.get("/me", response_model=UserRead)
def get_me(
    user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return to_user_read(service.get_me(user))


@router.patch("/me", response_model=UserRead)
def patch_me(
    body: UserUpdateRequest,
    user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    updated = service.update_me(user, name=body.name)
    return to_user_read(updated)


@router.delete(
    "/me/data",
    response_model=ErasureJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def erase_my_data(
    user: CurrentUser,
    service: ErasureService = Depends(get_erasure_service),
) -> ErasureJobAccepted:
    """Self-service account erasure request (T-17.03 / B-P1-ERASURE)."""
    job = service.request_self_erasure(actor=user)
    await service.enqueue_job(job.id)
    return to_erasure_job_accepted(job)


@router.get("/me/erasure-jobs/{job_id}", response_model=ErasureJobRead)
def get_my_erasure_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    service: ErasureService = Depends(get_erasure_service),
) -> ErasureJobRead:
    return to_erasure_job_read(service.get_for_actor(actor=user, job_id=job_id))
