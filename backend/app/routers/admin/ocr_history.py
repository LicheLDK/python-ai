"""Admin OCR history routes (T-10.01 / SDS §9.9). Controller only."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import AdminUser, get_db
from app.schemas.admin import (
    OcrJobAdminDetail,
    OcrJobAdminPage,
    to_ocr_job_admin_read,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/ocr-history", tags=["admin-ocr-history"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)


@router.get("", response_model=OcrJobAdminPage)
def list_ocr_history(
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
    status: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OcrJobAdminPage:
    rows, params, total = service.list_ocr_history(
        page=page,
        page_size=page_size,
        status=status,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return OcrJobAdminPage(
        items=[to_ocr_job_admin_read(j) for j in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/{job_id}", response_model=OcrJobAdminDetail)
def get_ocr_history_detail(
    job_id: uuid.UUID,
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
) -> OcrJobAdminDetail:
    return service.get_ocr_history_detail(job_id)
