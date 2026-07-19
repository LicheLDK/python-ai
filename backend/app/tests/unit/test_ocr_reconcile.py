"""OCR reconciler tests (T-4.09)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.main import app
from app.models.ocr import OcrJob, OcrJobStatus
from app.routers.documents import get_document_service
from app.routers.ocr import get_ocr_service
from app.services.document_service import DocumentService
from app.services.ocr_reconcile_service import OcrReconcileService
from app.services.ocr_service import OcrService
from app.tests.helpers import login_access_token, register_user, unique_email
from app.workers.reconcile_jobs import reconcile_stale_ocr_jobs

pytestmark = [pytest.mark.unit]

FIXTURE_PNG = (
    Path(__file__).resolve().parent.parent / "fixtures" / "sample_ocr_text.png"
)


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageAdapter:
    return LocalStorageAdapter(root=tmp_path)


@pytest.fixture()
def client(storage: LocalStorageAdapter):
    def _doc_override(db: Session = Depends(get_db)) -> DocumentService:
        return DocumentService(db, storage=storage)

    def _ocr_override(db: Session = Depends(get_db)) -> OcrService:
        return OcrService(db, queue=None, storage=storage)

    app.dependency_overrides[get_document_service] = _doc_override
    app.dependency_overrides[get_ocr_service] = _ocr_override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_document_service, None)
        app.dependency_overrides.pop(get_ocr_service, None)


def _auth_headers(client: TestClient) -> dict[str, str]:
    email = unique_email("ocr-rec")
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _create_queued_job(client: TestClient, headers: dict[str, str]) -> str:
    files = {
        "file": ("sample_ocr_text.png", FIXTURE_PNG.read_bytes(), "image/png"),
    }
    up = client.post("/api/v1/documents", headers=headers, files=files)
    assert up.status_code == 201, up.text
    created = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": up.json()["id"]},
    )
    assert created.status_code == 202, created.text
    return created.json()["id"]


def test_scan_requeues_stale_queued(client: TestClient) -> None:
    headers = _auth_headers(client)
    job_id = uuid.UUID(_create_queued_job(client, headers))
    now = datetime.now(UTC)

    with SessionLocal() as session:
        job = session.get(OcrJob, job_id)
        assert job is not None
        job.updated_at = now - timedelta(seconds=600)
        session.commit()

        plan = OcrReconcileService(
            session,
            stale_queued_seconds=180,
            stale_running_seconds=1200,
        ).scan(now=now)
        session.commit()

    assert job_id in plan.requeue_ids
    assert plan.reset_running_ids == []

    with SessionLocal() as session:
        job = session.get(OcrJob, job_id)
        assert job is not None
        assert job.status == OcrJobStatus.queued
        # touched so next tick won't immediately re-select unless still stale
        assert job.updated_at >= now - timedelta(seconds=5)


def test_scan_resets_stale_running(client: TestClient) -> None:
    headers = _auth_headers(client)
    job_id = uuid.UUID(_create_queued_job(client, headers))
    now = datetime.now(UTC)

    with SessionLocal() as session:
        job = session.get(OcrJob, job_id)
        assert job is not None
        job.status = OcrJobStatus.running
        job.started_at = now - timedelta(seconds=2000)
        job.attempt_count = 1
        job.updated_at = now - timedelta(seconds=2000)
        session.commit()

        plan = OcrReconcileService(
            session,
            stale_queued_seconds=180,
            stale_running_seconds=1200,
        ).scan(now=now)
        session.commit()

    assert job_id in plan.reset_running_ids
    assert job_id in plan.requeue_ids

    with SessionLocal() as session:
        job = session.get(OcrJob, job_id)
        assert job is not None
        assert job.status == OcrJobStatus.queued
        assert job.attempt_count == 1  # reconciler does not bump attempts
        assert "stale running" in (job.error or "").lower()


def test_fresh_jobs_not_selected(client: TestClient) -> None:
    headers = _auth_headers(client)
    job_id = uuid.UUID(_create_queued_job(client, headers))
    now = datetime.now(UTC)

    with SessionLocal() as session:
        plan = OcrReconcileService(
            session,
            stale_queued_seconds=180,
            stale_running_seconds=1200,
        ).scan(now=now)
        session.commit()

    assert job_id not in plan.requeue_ids


class _FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def enqueue_job(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return object()


def test_reconcile_arq_handler_enqueues(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = _auth_headers(client)
    job_id = uuid.UUID(_create_queued_job(client, headers))
    now = datetime.now(UTC)

    with SessionLocal() as session:
        job = session.get(OcrJob, job_id)
        assert job is not None
        job.updated_at = now - timedelta(seconds=600)
        session.commit()

    monkeypatch.setattr(
        "app.workers.reconcile_jobs.settings.ocr_reconcile_enabled",
        True,
    )
    # Force short threshold for this run via service defaults already on DB age;
    # also shorten settings used inside handler's OcrReconcileService.
    monkeypatch.setattr(
        "app.workers.reconcile_jobs.settings.ocr_stale_queued_seconds",
        60,
    )
    monkeypatch.setattr(
        "app.workers.reconcile_jobs.settings.ocr_stale_running_seconds",
        1200,
    )

    fake = _FakeRedis()
    result = asyncio.run(reconcile_stale_ocr_jobs({"redis": fake}))
    assert result["skipped"] is False
    assert result["planned"] >= 1
    assert result["enqueued"] >= 1
    assert any(str(job_id) in str(c) for c in fake.calls)
