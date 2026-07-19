"""Admin audit log routes (T-10.01 / SDS §9.9). Controller only."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import AdminUser, get_db
from app.schemas.admin import AuditLogPage, to_audit_log_read
from app.services.admin_service import AdminService

router = APIRouter(prefix="/audit-logs", tags=["admin-audit"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)


@router.get("", response_model=AuditLogPage)
def list_audit_logs(
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
    actor_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditLogPage:
    rows, params, total = service.list_audit_logs(
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )
    return AuditLogPage(
        items=[to_audit_log_read(r) for r in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )
