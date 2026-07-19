"""Admin ops APIs (T-10.01) — usage / ocr-history / audit-logs / dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.ai import AiProvider, AiRequestStatus, AiRequestType
from app.models.ocr import OcrJobStatus
from app.models.user import User, UserRole
from app.repositories.ai_request_repository import AiRequestRepository
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    login_access_token,
    register_user,
    unique_email,
)

pytestmark = [pytest.mark.api]


def _promote_admin(email: str) -> uuid.UUID:
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        db.execute(update(User).where(User.id == user.id).values(role=UserRole.admin))
        db.commit()
        return user.id


def _admin_headers(client: TestClient) -> dict[str, str]:
    email = unique_email("adm-ops")
    register_user(client, email=email)
    admin_id = _promote_admin(email)
    token = create_access_token(subject=admin_id, role=UserRole.admin.value)
    return {"Authorization": f"Bearer {token}"}


def test_admin_ops_forbidden_for_normal_user(client: TestClient) -> None:
    email = unique_email("adm-ops-user")
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    for path in (
        "/api/v1/admin/usage",
        "/api/v1/admin/ocr-history",
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/dashboard",
    ):
        res = client.get(path, headers=headers)
        assert_error_envelope(res, status_code=403, code="forbidden")


def test_admin_usage_ocr_audit_dashboard(client: TestClient) -> None:
    headers = _admin_headers(client)
    user_email = unique_email("adm-ops-act")
    register_user(client, email=user_email)
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == user_email)).one()
        user_id = user.id
        docs = DocumentRepository(db)
        doc = docs.create(
            document_id=uuid.uuid4(),
            owner_id=user_id,
            filename="admin.png",
            mime_type="image/png",
            size_bytes=10,
            checksum_sha256="a" * 64,
            storage_key=f"documents/test/{uuid.uuid4()}/original.bin",
            page_count=1,
        )
        jobs = OcrJobRepository(db)
        now = datetime.now(UTC)
        job = jobs.create(document_id=doc.id, user_id=user_id)
        jobs.mark_running(job, started_at=now - timedelta(seconds=2))
        jobs.mark_succeeded(job, finished_at=now)
        OcrResultRepository(db).create(
            job_id=job.id,
            page=1,
            text="hello admin",
            boxes=[],
            confidence=0.9,
        )
        req = AiRequestRepository(db).create(
            user_id=user_id,
            provider=AiProvider.openai,
            model="gpt-test",
            request_type=AiRequestType.chat,
            status=AiRequestStatus.succeeded,
        )
        AiUsageRepository(db).create(
            request_id=req.id,
            tokens_in=11,
            tokens_out=7,
            latency_ms=42,
            cost_estimate=0.002,
        )
        job_id = job.id
        db.commit()

    usage = client.get("/api/v1/admin/usage", headers=headers)
    assert usage.status_code == 200, usage.text
    assert usage.json()["total"] >= 1
    assert any(item["tokens_in"] == 11 for item in usage.json()["items"])

    ocr = client.get("/api/v1/admin/ocr-history", headers=headers)
    assert ocr.status_code == 200, ocr.text
    assert ocr.json()["total"] >= 1

    detail = client.get(f"/api/v1/admin/ocr-history/{job_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["job"]["status"] == OcrJobStatus.succeeded.value
    assert body["pages"][0]["text"] == "hello admin"

    # Trigger an audited admin patch so audit-logs has a row.
    patch = client.patch(
        f"/api/v1/admin/users/{user_id}",
        headers=headers,
        json={"name": "Renamed By Admin"},
    )
    assert patch.status_code == 200, patch.text

    audits = client.get(
        "/api/v1/admin/audit-logs",
        headers=headers,
        params={"action": "admin.user.update"},
    )
    assert audits.status_code == 200, audits.text
    assert audits.json()["total"] >= 1

    dash = client.get("/api/v1/admin/dashboard", headers=headers)
    assert dash.status_code == 200, dash.text
    kpi = dash.json()
    assert kpi["users_total"] >= 2
    assert kpi["ocr_jobs_24h"] >= 1
    assert kpi["ai_requests_24h"] >= 1
    assert "error_rate_24h" in kpi
    assert isinstance(kpi["top_users"], list)
    assert isinstance(kpi["provider_breakdown"], list)
