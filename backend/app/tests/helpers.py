"""Shared HTTP test helpers."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User, UserRole


DEFAULT_PASSWORD = "Str0ng-P@ss!"


def unique_email(prefix: str = "t") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def register_user(
    client: TestClient,
    *,
    email: str,
    password: str = DEFAULT_PASSWORD,
    name: str = "User",
) -> None:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert res.status_code == 201, res.text


def login_access_token(
    client: TestClient,
    *,
    email: str,
    password: str = DEFAULT_PASSWORD,
) -> str:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def promote_to_admin(email: str) -> uuid.UUID:
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        db.execute(update(User).where(User.id == user.id).values(role=UserRole.admin))
        db.commit()
        return user.id


def admin_bearer_headers(email: str) -> dict[str, str]:
    user_id = promote_to_admin(email)
    token = create_access_token(subject=user_id, role=UserRole.admin.value)
    return {"Authorization": f"Bearer {token}"}


def user_id_by_email(email: str) -> uuid.UUID:
    with SessionLocal() as db:
        return db.scalars(select(User).where(User.email == email)).one().id
