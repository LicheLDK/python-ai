"""Admin users API tests (T-2.03) — RBAC + audit side effect."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.tests.conftest import assert_error_envelope

pytestmark = [pytest.mark.api]


def _register(client: TestClient, *, email: str, name: str = "User") -> None:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Str0ng-P@ss!", "name": name},
    )
    assert res.status_code == 201, res.text


def _login_token(client: TestClient, *, email: str) -> str:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Str0ng-P@ss!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _promote_admin(email: str) -> uuid.UUID:
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        db.execute(update(User).where(User.id == user.id).values(role=UserRole.admin))
        db.commit()
        return user.id


def test_admin_users_forbidden_for_normal_user(client: TestClient) -> None:
    email = f"t203-user-{uuid.uuid4().hex[:10]}@example.com"
    _register(client, email=email)
    token = _login_token(client, email=email)
    res = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert_error_envelope(res, status_code=403, code="forbidden")


def test_admin_list_get_patch_and_audit(client: TestClient) -> None:
    admin_email = f"t203-admin-{uuid.uuid4().hex[:10]}@example.com"
    target_email = f"t203-target-{uuid.uuid4().hex[:10]}@example.com"
    _register(client, email=admin_email, name="Admin")
    _register(client, email=target_email, name="Target")
    admin_id = _promote_admin(admin_email)
    admin_token = create_access_token(subject=admin_id, role=UserRole.admin.value)
    headers = {"Authorization": f"Bearer {admin_token}"}

    listed = client.get("/api/v1/admin/users", headers=headers, params={"q": target_email})
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 1
    assert any(item["email"] == target_email for item in body["items"])

    with SessionLocal() as db:
        target = db.scalars(select(User).where(User.email == target_email)).one()
        target_id = target.id

    detail = client.get(f"/api/v1/admin/users/{target_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["email"] == target_email

    patched = client.patch(
        f"/api/v1/admin/users/{target_id}",
        headers=headers,
        json={"status": "inactive", "name": "Target Renamed"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "inactive"
    assert patched.json()["name"] == "Target Renamed"

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.action == "admin.user.update",
                    AuditLog.resource_id == str(target_id),
                )
            ).all()
        )
        assert len(rows) >= 1
        assert rows[-1].actor_id == admin_id
        assert "changes" in rows[-1].payload


def test_admin_get_user_not_found(client: TestClient) -> None:
    admin_email = f"t203-admin2-{uuid.uuid4().hex[:10]}@example.com"
    _register(client, email=admin_email)
    admin_id = _promote_admin(admin_email)
    token = create_access_token(subject=admin_id, role=UserRole.admin.value)
    res = client.get(
        f"/api/v1/admin/users/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert_error_envelope(res, status_code=404, code="not_found")
