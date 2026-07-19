"""Users /me API tests (T-2.02)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import assert_error_envelope

pytestmark = [pytest.mark.api]


def _register_login(client: TestClient, *, email: str, password: str = "Str0ng-P@ss!") -> str:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "name": "Original"},
        ).status_code
        == 201
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_get_me_requires_auth(client: TestClient) -> None:
    res = client.get("/api/v1/users/me")
    assert_error_envelope(res, status_code=401, code="unauthorized")


def test_get_and_patch_me(client: TestClient) -> None:
    email = f"t202-{uuid.uuid4().hex[:12]}@example.com"
    token = _register_login(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["email"] == email
    assert body["name"] == "Original"

    patched = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"name": "Renamed"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Renamed"
    assert patched.json()["email"] == email

    again = client.get("/api/v1/users/me", headers=headers)
    assert again.json()["name"] == "Renamed"


def test_patch_me_rejects_email_field(client: TestClient) -> None:
    email = f"t202-{uuid.uuid4().hex[:12]}@example.com"
    token = _register_login(client, email=email)
    res = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "X", "email": "hacker@example.com"},
    )
    assert_error_envelope(res, status_code=422, code="validation_error")
