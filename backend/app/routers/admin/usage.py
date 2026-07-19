"""Admin AI usage routes (T-10.01 / SDS §9.9). Controller only."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import AdminUser, get_db
from app.schemas.admin import AiUsagePage
from app.services.admin_service import AdminService

router = APIRouter(prefix="/usage", tags=["admin-usage"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)


@router.get("", response_model=AiUsagePage)
def list_usage(
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    provider: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AiUsagePage:
    items, params, total = service.list_usage(
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        provider=provider,
        user_id=user_id,
    )
    return AiUsagePage(
        items=items,
        page=params.page,
        page_size=params.page_size,
        total=total,
    )
