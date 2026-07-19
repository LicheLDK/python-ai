"""Auth dependency tests (T-1.05) — protected stub 401/403."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.user import User, UserRole, UserStatus

pytestmark = [pytest.mark.auth, pytest.mark.api]


def _register_and_login(client: TestClient, *, email: str, password: str = "Str0ng-P@ss!") -> str:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Probe"},
    )
    assert reg.status_code == 201, reg.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_probe_me_requires_auth() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/_probe/me")
    assert res.status_code == 401


def test_probe_me_with_bearer() -> None:
    client = TestClient(app)
    email = f"t105-{uuid.uuid4().hex[:12]}@example.com"
    token = _register_and_login(client, email=email)

    res = client.get(
        "/api/v1/_probe/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["email"] == email


def test_probe_me_rejects_invalid_token() -> None:
    client = TestClient(app)
    res = client.get(
        "/api/v1/_probe/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert res.status_code == 401


def test_probe_admin_forbidden_for_user_role() -> None:
    client = TestClient(app)
    email = f"t105-{uuid.uuid4().hex[:12]}@example.com"
    token = _register_and_login(client, email=email)

    res = client.get(
        "/api/v1/_probe/admin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_probe_admin_ok_for_admin_role() -> None:
    client = TestClient(app)
    email = f"t105-admin-{uuid.uuid4().hex[:12]}@example.com"
    token = _register_and_login(client, email=email)

    # Elevate role in DB, then mint a matching admin access token.
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        db.execute(
            update(User).where(User.id == user.id).values(role=UserRole.admin)
        )
        db.commit()
        user_id = user.id

    admin_token = create_access_token(subject=user_id, role=UserRole.admin.value)
    res = client.get(
        "/api/v1/_probe/admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "ok"


def test_probe_me_forbidden_when_inactive() -> None:
    client = TestClient(app)
    email = f"t105-inactive-{uuid.uuid4().hex[:12]}@example.com"
    token = _register_and_login(client, email=email)

    with SessionLocal() as db:
        db.execute(
            update(User).where(User.email == email).values(status=UserStatus.inactive)
        )
        db.commit()

    res = client.get(
        "/api/v1/_probe/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
