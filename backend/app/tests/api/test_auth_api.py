"""Auth API test suite (T-1.06) — CI-ready HTTP contract tests.

Covers: register/login/refresh/logout, rate limit, inactive user, CSRF failure,
error envelope, reuse detection via refresh cookie.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.core.constants import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    REDIS_KEY_LOGIN_RATE_EMAIL,
    REFRESH_COOKIE_NAME,
)
from app.core.database import SessionLocal
from app.models.user import User, UserStatus
from app.tests.conftest import assert_error_envelope

pytestmark = pytest.mark.auth


def _register(
    client: TestClient,
    *,
    email: str,
    password: str = "Str0ng-P@ss!",
    name: str = "T106",
):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": name},
    )


def _login(
    client: TestClient,
    *,
    email: str,
    password: str = "Str0ng-P@ss!",
):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.api
def test_register_validation_error(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "short", "name": ""},
    )
    assert_error_envelope(res, status_code=422, code="validation_error")


@pytest.mark.api
def test_register_conflict(client: TestClient, unique_email: str) -> None:
    assert _register(client, email=unique_email).status_code == 201
    res = _register(client, email=unique_email)
    assert_error_envelope(res, status_code=409, code="conflict")


@pytest.mark.api
def test_login_invalid_credentials(client: TestClient, unique_email: str) -> None:
    assert _register(client, email=unique_email).status_code == 201
    res = _login(client, email=unique_email, password="wrong-password")
    assert_error_envelope(res, status_code=401, code="unauthorized")


@pytest.mark.api
def test_login_inactive_user(client: TestClient, unique_email: str) -> None:
    assert _register(client, email=unique_email).status_code == 201
    with SessionLocal() as db:
        db.execute(
            update(User)
            .where(User.email == unique_email)
            .values(status=UserStatus.inactive)
        )
        db.commit()

    res = _login(client, email=unique_email)
    assert_error_envelope(res, status_code=403, code="forbidden")


@pytest.mark.api
def test_login_rate_limit(
    client: TestClient,
    redis_client,
    unique_email: str,
) -> None:
    assert _register(client, email=unique_email).status_code == 201
    email_key = REDIS_KEY_LOGIN_RATE_EMAIL.format(email=unique_email.lower())
    ip_key = "aisaas:rl:login:ip:testclient"
    redis_client.delete(email_key, ip_key)

    for i in range(LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
        res = _login(client, email=unique_email, password="wrong-password")
        assert res.status_code == 401, f"attempt {i + 1}: {res.text}"

    res = _login(client, email=unique_email, password="wrong-password")
    assert_error_envelope(res, status_code=429, code="rate_limited")
    redis_client.delete(email_key, ip_key)


@pytest.mark.api
def test_refresh_csrf_missing_header(client: TestClient, unique_email: str) -> None:
    assert _register(client, email=unique_email).status_code == 201
    login = _login(client, email=unique_email)
    assert login.status_code == 200
    assert REFRESH_COOKIE_NAME in login.cookies

    # Cookie present, CSRF header absent → 403
    res = client.post("/api/v1/auth/refresh")
    assert_error_envelope(res, status_code=403, code="forbidden")


@pytest.mark.api
def test_refresh_csrf_mismatch(client: TestClient, unique_email: str) -> None:
    assert _register(client, email=unique_email).status_code == 201
    login = _login(client, email=unique_email)
    assert login.status_code == 200

    res = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: "definitely-wrong"},
    )
    assert_error_envelope(res, status_code=403, code="forbidden")


@pytest.mark.api
def test_refresh_missing_cookie_unauthorized(client: TestClient) -> None:
    # Fresh client — no refresh cookie; CSRF double-submit with issued token.
    csrf_res = client.get("/api/v1/auth/csrf")
    assert csrf_res.status_code == 200
    token = csrf_res.json()["csrf_token"]

    res = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: token},
    )
    assert_error_envelope(res, status_code=401, code="unauthorized")


@pytest.mark.api
def test_refresh_reuse_detection(client: TestClient, unique_email: str) -> None:
    assert _register(client, email=unique_email).status_code == 201
    login = _login(client, email=unique_email)
    assert login.status_code == 200
    csrf = login.cookies.get(CSRF_COOKIE_NAME)
    old_refresh = login.cookies.get(REFRESH_COOKIE_NAME)

    first = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf},
    )
    assert first.status_code == 200, first.text

    # Replay the pre-rotation refresh cookie → reuse → 401
    client.cookies.set(REFRESH_COOKIE_NAME, old_refresh, path="/api/v1/auth")
    csrf2 = first.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)
    replay = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf2},
    )
    assert_error_envelope(replay, status_code=401, code="unauthorized")


@pytest.mark.api
def test_logout_requires_csrf_when_refresh_present(
    client: TestClient,
    unique_email: str,
) -> None:
    assert _register(client, email=unique_email).status_code == 201
    login = _login(client, email=unique_email)
    assert login.status_code == 200

    res = client.post("/api/v1/auth/logout")
    assert_error_envelope(res, status_code=403, code="forbidden")


@pytest.mark.api
def test_full_auth_happy_path(client: TestClient, unique_email: str) -> None:
    reg = _register(client, email=unique_email)
    assert reg.status_code == 201

    login = _login(client, email=unique_email)
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == unique_email

    csrf = login.cookies.get(CSRF_COOKIE_NAME)
    refresh = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf},
    )
    assert refresh.status_code == 200
    csrf2 = refresh.cookies.get(CSRF_COOKIE_NAME) or client.cookies.get(CSRF_COOKIE_NAME)

    logout = client.post(
        "/api/v1/auth/logout",
        headers={CSRF_HEADER_NAME: csrf2},
    )
    assert logout.status_code == 204

    # After logout, refresh must fail (cookie cleared or token revoked).
    again = client.post(
        "/api/v1/auth/refresh",
        headers={CSRF_HEADER_NAME: csrf2},
    )
    assert again.status_code in {401, 403}
