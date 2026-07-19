"""HTTP smoke for auth routes (T-1.04) — register → login → refresh → logout."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, REFRESH_COOKIE_NAME
from app.main import app

pytestmark = [pytest.mark.auth, pytest.mark.api]


def test_auth_swagger_flow() -> None:
    email = f"t104-{uuid.uuid4().hex[:12]}@example.com"
    password = "Str0ng-P@ss!"
    client = TestClient(app)

    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "T104"},
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["user"]["email"] == email

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert REFRESH_COOKIE_NAME in login.cookies
    assert CSRF_COOKIE_NAME in login.cookies

    csrf = login.cookies.get(CSRF_COOKIE_NAME)
    refresh = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf},
    )
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["access_token"]

    # CSRF failure
    bad = client.post("/api/v1/auth/refresh", headers={CSRF_HEADER_NAME: "nope"})
    assert bad.status_code == 403

    csrf2 = refresh.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)
    logout = client.post(
        "/api/v1/auth/logout",
        headers={CSRF_HEADER_NAME: csrf2},
    )
    assert logout.status_code == 204


def test_csrf_endpoint() -> None:
    client = TestClient(app)
    res = client.get("/api/v1/auth/csrf")
    assert res.status_code == 200
    assert res.json()["csrf_token"]
    assert CSRF_COOKIE_NAME in res.cookies
