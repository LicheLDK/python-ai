"""Admin seed tests (T-1.07) — idempotent create + login."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.scripts.seed_admin import seed_admin

pytestmark = [pytest.mark.auth]


def test_seed_admin_creates_and_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    email = f"seed-admin-{uuid.uuid4().hex[:10]}@example.com"
    password = "SeedAdminPass1!"
    monkeypatch.setenv("SEED_ADMIN_EMAIL", email)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", password)
    monkeypatch.setenv("SEED_ADMIN_NAME", "Seed Admin")
    get_settings.cache_clear()

    assert seed_admin() == 0
    assert seed_admin() == 0  # idempotent

    with SessionLocal() as db:
        user = UserRepository(db).get_by_email(email)
        assert user is not None
        assert user.role == UserRole.admin

    client = TestClient(app)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    probe = client.get(
        "/api/v1/_probe/admin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert probe.status_code == 200, probe.text

    get_settings.cache_clear()
