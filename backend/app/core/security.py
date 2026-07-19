"""JWT and password hashing primitives (T-1.02 / SDS ADR-008, ADR-024, §11).

Unit-testable without HTTP. Auth flows (login/refresh cookies) belong to T-1.03+.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.exceptions.auth import TokenError

# Argon2id is the PasswordHasher default (SDS ADR-024).
_password_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Decoded access-token claims used by later auth dependencies."""

    sub: uuid.UUID
    role: str
    jti: uuid.UUID
    exp: datetime
    iat: datetime
    typ: str = ACCESS_TOKEN_TYPE


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if password matches the Argon2id hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    *,
    subject: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None,
    jti: uuid.UUID | None = None,
) -> str:
    """Issue a signed HS256 access JWT (Bearer).

    Claims: sub, role, jti, typ, iat, exp.
    """
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(minutes=settings.access_token_ttl_minutes)
    token_jti = jti or uuid.uuid4()
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "jti": str(token_jti),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + delta,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    """Verify signature/expiry and return typed access claims.

    Raises TokenError when the token is invalid, expired, or wrong type.
    """
    try:
        raw = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat", "jti", "typ", "role"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Access token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid access token") from exc

    if raw.get("typ") != ACCESS_TOKEN_TYPE:
        raise TokenError("Invalid access token type")

    try:
        return AccessTokenClaims(
            sub=uuid.UUID(str(raw["sub"])),
            role=str(raw["role"]),
            jti=uuid.UUID(str(raw["jti"])),
            exp=_as_utc_datetime(raw["exp"]),
            iat=_as_utc_datetime(raw["iat"]),
            typ=str(raw["typ"]),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise TokenError("Invalid access token claims") from exc


def generate_refresh_token() -> str:
    """Generate an opaque refresh token (stored hashed; T-1.03+)."""
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex digest for refresh token storage (SDS §10.7)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def access_token_expires_in_seconds(
    expires_delta: timedelta | None = None,
) -> int:
    """expires_in value for login/refresh API responses."""
    delta = expires_delta or timedelta(minutes=settings.access_token_ttl_minutes)
    return int(delta.total_seconds())


def _as_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    # PyJWT may return exp/iat as POSIX timestamp (int/float).
    return datetime.fromtimestamp(float(value), tz=UTC)
