"""AuditLogRepository — DB access only (T-2.04 / T-10.01 / SDS §10.15)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.utils.pagination import PageParams


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        action: str,
        resource_type: str,
        actor_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
        ip: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload if payload is not None else {},
            ip=ip,
            request_id=request_id,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_filtered(
        self,
        *,
        page: PageParams,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        filters: list = []
        if actor_id is not None:
            filters.append(AuditLog.actor_id == actor_id)
        if action:
            filters.append(AuditLog.action == action)
        if date_from is not None:
            filters.append(AuditLog.created_at >= date_from)
        if date_to is not None:
            filters.append(AuditLog.created_at <= date_to)

        count_stmt = select(func.count()).select_from(AuditLog)
        list_stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)
        list_stmt = list_stmt.offset(page.offset).limit(page.limit)

        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(self._session.scalars(list_stmt).all())
        return rows, total
