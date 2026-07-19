"""Users / Admin RBAC matrix tests (T-2.06).

Matrix:
  anonymous → 401 on /users/me and /admin/users
  role=user → /users/me OK, /admin/* 403
  role=admin → /users/me OK, /admin/* OK
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    admin_bearer_headers,
    login_access_token,
    register_user,
    unique_email,
    user_id_by_email,
)

pytestmark = [pytest.mark.api, pytest.mark.rbac]


def test_anonymous_denied(client: TestClient) -> None:
    assert_error_envelope(
        client.get("/api/v1/users/me"),
        status_code=401,
        code="unauthorized",
    )
    assert_error_envelope(
        client.get("/api/v1/admin/users"),
        status_code=401,
        code="unauthorized",
    )


def test_user_role_matrix(client: TestClient) -> None:
    email = unique_email("rbac-user")
    register_user(client, email=email, name="Rbac User")
    token = login_access_token(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "user"

    for method, path in (
        ("GET", "/api/v1/admin/users"),
        ("GET", f"/api/v1/admin/users/{uuid.uuid4()}"),
        ("PATCH", f"/api/v1/admin/users/{uuid.uuid4()}"),
    ):
        if method == "GET":
            res = client.get(path, headers=headers)
        else:
            res = client.patch(path, headers=headers, json={"name": "X"})
        assert_error_envelope(res, status_code=403, code="forbidden")


def test_admin_role_matrix(client: TestClient) -> None:
    admin_email = unique_email("rbac-admin")
    target_email = unique_email("rbac-target")
    register_user(client, email=admin_email, name="Rbac Admin")
    register_user(client, email=target_email, name="Rbac Target")
    headers = admin_bearer_headers(admin_email)
    target_id = user_id_by_email(target_email)

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    listed = client.get(
        "/api/v1/admin/users",
        headers=headers,
        params={"q": "rbac-target", "page": 1, "page_size": 10},
    )
    assert listed.status_code == 200, listed.text
    page = listed.json()
    assert set(page.keys()) >= {"items", "page", "page_size", "total"}
    assert page["page"] == 1
    assert any(i["email"] == target_email for i in page["items"])

    detail = client.get(f"/api/v1/admin/users/{target_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == str(target_id)

    patched = client.patch(
        f"/api/v1/admin/users/{target_id}",
        headers=headers,
        json={"role": "admin", "status": "active"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["role"] == "admin"

    with SessionLocal() as db:
        audits = list(
            db.scalars(
                select(AuditLog).where(
                    AuditLog.action == "admin.user.update",
                    AuditLog.resource_id == str(target_id),
                )
            ).all()
        )
        assert audits
        assert "role" in audits[-1].payload.get("changes", {})


def test_admin_filter_by_role_and_status(client: TestClient) -> None:
    admin_email = unique_email("rbac-filt-admin")
    register_user(client, email=admin_email)
    headers = admin_bearer_headers(admin_email)

    res = client.get(
        "/api/v1/admin/users",
        headers=headers,
        params={"role": "admin", "status": "active", "page_size": 5},
    )
    assert res.status_code == 200, res.text
    for item in res.json()["items"]:
        assert item["role"] == "admin"
        assert item["status"] == "active"
