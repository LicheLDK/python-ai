"""AuditService write tests (T-2.04)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.request_context import reset_request_id, set_request_id
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.user import UserRole, UserStatus
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

pytestmark = [pytest.mark.unit]


def test_audit_service_write_persists_row() -> None:
    session = SessionLocal()
    try:
        users = UserRepository(session)
        actor = users.create(
            email=f"audit-actor-{uuid.uuid4().hex[:10]}@example.com",
            password_hash=hash_password("AuditPass1!"),
            name="Auditor",
            role=UserRole.admin,
            status=UserStatus.active,
        )
        session.commit()

        token = set_request_id("req-audit-test-001")
        try:
            audit = AuditService(session)
            row = audit.write(
                action="user.update",
                resource_type="user",
                actor_id=actor.id,
                resource_id=str(actor.id),
                payload={"fields": ["role"], "role": "admin"},
                ip="127.0.0.1",
                commit=True,
            )
        finally:
            reset_request_id(token)

        assert row.id is not None
        assert row.action == "user.update"
        assert row.request_id == "req-audit-test-001"

        loaded = session.scalars(
            select(AuditLog).where(AuditLog.id == row.id)
        ).one()
        assert loaded.payload["role"] == "admin"
        assert loaded.actor_id == actor.id
    finally:
        session.close()
