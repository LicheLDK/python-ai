"""Shared fixtures for backend tests (T-1.06)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.constants import REDIS_KEY_LOGIN_RATE_IP
from app.core.redis import get_redis
from app.main import app

# FastAPI TestClient reports this as client.host
_TESTCLIENT_IP = "testclient"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def redis_client():
    return get_redis()


@pytest.fixture(autouse=True)
def _clear_testclient_login_rate_limit(redis_client):
    """Prevent IP rate-limit bleed across tests (all share host `testclient`)."""
    key = REDIS_KEY_LOGIN_RATE_IP.format(ip=_TESTCLIENT_IP)
    redis_client.delete(key)
    yield
    redis_client.delete(key)


@pytest.fixture()
def unique_email() -> str:
    return f"t106-{uuid.uuid4().hex[:12]}@example.com"


def assert_error_envelope(response, *, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body.get("code") == code
    assert "message" in body
    assert "request_id" in body
    return body
