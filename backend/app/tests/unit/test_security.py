"""Unit tests for core security primitives (T-1.02)."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core.security import (
    AccessTokenClaims,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.exceptions.auth import TokenError

pytestmark = [pytest.mark.auth, pytest.mark.unit]


def test_password_hash_round_trip() -> None:
    password = "Str0ng-P@ssw0rd!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_claim_round_trip() -> None:
    user_id = uuid.uuid4()
    jti = uuid.uuid4()
    token = create_access_token(subject=user_id, role="admin", jti=jti)

    claims = decode_access_token(token)

    assert isinstance(claims, AccessTokenClaims)
    assert claims.sub == user_id
    assert claims.role == "admin"
    assert claims.jti == jti
    assert claims.typ == "access"
    assert claims.exp > claims.iat


def test_decode_access_token_rejects_tampered() -> None:
    token = create_access_token(subject=uuid.uuid4(), role="user")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_decode_access_token_rejects_expired() -> None:
    token = create_access_token(
        subject=uuid.uuid4(),
        role="user",
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(TokenError, match="expired"):
        decode_access_token(token)


def test_refresh_token_hash_is_sha256_hex() -> None:
    raw = generate_refresh_token()
    digest = hash_token(raw)

    assert len(digest) == 64
    assert digest == hash_token(raw)
    assert digest != hash_token(raw + "x")
