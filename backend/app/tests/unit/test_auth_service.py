"""AuthService tests (T-1.03) — success / fail / reuse / rate limit.

Requires local Postgres + Redis (Compose). Uses unique emails per run.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.config import settings
from app.core.constants import LOGIN_RATE_LIMIT_MAX_ATTEMPTS
from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.exceptions.auth import ForbiddenError, TokenError, UnauthorizedError
from app.exceptions.domain import ConflictError, RateLimitError
from app.models.user import UserStatus
from app.services.auth_service import AuthService

pytestmark = [pytest.mark.auth, pytest.mark.unit]


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def redis_client():
    client = get_redis()
    yield client


@pytest.fixture()
def auth(db, redis_client) -> AuthService:
    return AuthService(db, redis_client)


def _email() -> str:
    return f"t103-{uuid.uuid4().hex[:12]}@example.com"


def test_register_and_login_success(auth: AuthService, redis_client) -> None:
    email = _email()
    user = auth.register(email=email, password="Str0ng-P@ss!", name="Alice")
    assert user.email == email
    assert user.role.value == "user"
    assert user.status.value == "active"

    session = auth.login(email=email, password="Str0ng-P@ss!", ip="127.0.0.1")
    claims = decode_access_token(session.access_token)
    assert claims.sub == user.id
    assert claims.role == "user"
    assert session.refresh_token
    assert session.expires_in > 0
    assert session.token_type == "bearer"


def test_register_duplicate_email(auth: AuthService) -> None:
    email = _email()
    auth.register(email=email, password="Str0ng-P@ss!", name="A")
    with pytest.raises(ConflictError):
        auth.register(email=email, password="Str0ng-P@ss!", name="B")


def test_login_invalid_password(auth: AuthService) -> None:
    email = _email()
    auth.register(email=email, password="Str0ng-P@ss!", name="A")
    with pytest.raises(UnauthorizedError):
        auth.login(email=email, password="wrong-password")


def test_login_inactive_user(auth: AuthService, db) -> None:
    email = _email()
    user = auth.register(email=email, password="Str0ng-P@ss!", name="A")
    user.status = UserStatus.inactive
    db.commit()

    with pytest.raises(ForbiddenError):
        auth.login(email=email, password="Str0ng-P@ss!")


def test_refresh_rotation_and_reuse_detection(auth: AuthService) -> None:
    email = _email()
    auth.register(email=email, password="Str0ng-P@ss!", name="A")
    first = auth.login(email=email, password="Str0ng-P@ss!")
    old_refresh = first.refresh_token

    second = auth.refresh(raw_refresh_token=old_refresh)
    assert second.access_token != first.access_token
    assert second.refresh_token != old_refresh

    # Old refresh must not work again → reuse detection.
    with pytest.raises(TokenError, match="reuse"):
        auth.refresh(raw_refresh_token=old_refresh)

    # New refresh should also be revoked after reuse family wipe.
    with pytest.raises(TokenError):
        auth.refresh(raw_refresh_token=second.refresh_token)


def test_logout_revokes_refresh(auth: AuthService) -> None:
    email = _email()
    auth.register(email=email, password="Str0ng-P@ss!", name="A")
    session = auth.login(email=email, password="Str0ng-P@ss!")
    auth.logout(raw_refresh_token=session.refresh_token)

    with pytest.raises(TokenError):
        auth.refresh(raw_refresh_token=session.refresh_token)


def test_login_rate_limit(auth: AuthService, redis_client) -> None:
    email = _email()
    auth.register(email=email, password="Str0ng-P@ss!", name="A")
    ip = "10.0.0.99"
    redis_client.delete(
        f"aisaas:rl:login:email:{email}",
        f"aisaas:rl:login:ip:{ip}",
    )

    for _ in range(LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
        with pytest.raises(UnauthorizedError):
            auth.login(email=email, password="wrong", ip=ip)

    with pytest.raises(RateLimitError):
        auth.login(email=email, password="wrong", ip=ip)

    redis_client.delete(
        f"aisaas:rl:login:email:{email}",
        f"aisaas:rl:login:ip:{ip}",
    )


def test_settings_loaded_for_ttl() -> None:
    assert settings.refresh_token_ttl_days >= 1
    assert settings.access_token_ttl_minutes >= 1
