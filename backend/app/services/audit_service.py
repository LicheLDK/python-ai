"""Audit logging service (T-2.04 / SDS §7 / §10.15).

Write API for mutations. Admin list API is T-10.01; hooks into admin user
patch land in T-2.03.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.models.audit import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    def __init__(
        self,
        session: Session,
        *,
        audit_logs: AuditLogRepository | None = None,
    ) -> None:
        self._session = session
        self._audit_logs = audit_logs or AuditLogRepository(session)

    def write(
        self,
        *,
        action: str,
        resource_type: str,
        actor_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
        ip: str | None = None,
        request_id: str | None = None,
        commit: bool = False,
    ) -> AuditLog:
        """Persist an audit row.

        When ``commit`` is False (default), the caller owns the transaction
        (typical inside another service mutation). Set ``commit=True`` for
        standalone writes.
        """
        rid = request_id if request_id is not None else (get_request_id() or None)
        if rid == "":
            rid = None

        row = self._audit_logs.create(
            action=action,
            resource_type=resource_type,
            actor_id=actor_id,
            resource_id=resource_id,
            payload=payload,
            ip=ip,
            request_id=rid,
        )
        if commit:
            self._session.commit()
            self._session.refresh(row)
        return row
