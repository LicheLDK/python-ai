"""OCR API + worker lifecycle tests (T-4.05)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.ports import OcrPageResult, PreprocessOptions
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.main import app
from app.models.document import Document, DocumentStatus
from app.routers.documents import get_document_service
from app.routers.ocr import get_ocr_service
from app.services.document_service import DocumentService
from app.services.ocr_service import OcrService
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    login_access_token,
    register_user,
    unique_email,
)
from app.workers.ocr_jobs import OcrJobRunner

pytestmark = [pytest.mark.api]

FIXTURE_PNG = (
    Path(__file__).resolve().parent.parent / "fixtures" / "sample_ocr_text.png"
)


class _IdentityPreprocess:
    def process(self, image_bytes: bytes, options: PreprocessOptions | None = None) -> bytes:
        return image_bytes


class _FakeOcr:
    def extract(
        self,
        image_bytes: bytes,
        *,
        lang: str | None = None,
        page: int = 1,
    ) -> OcrPageResult:
        assert image_bytes
        return OcrPageResult(
            page=page,
            text="HELLO OCR",
            boxes=[
                {
                    "text": "HELLO OCR",
                    "confidence": 0.99,
                    "points": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
                }
            ],
            confidence=0.99,
        )


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageAdapter:
    return LocalStorageAdapter(root=tmp_path)


@pytest.fixture()
def client(storage: LocalStorageAdapter):
    def _doc_override(db: Session = Depends(get_db)) -> DocumentService:
        return DocumentService(db, storage=storage)

    def _ocr_override(db: Session = Depends(get_db)) -> OcrService:
        # Tests drive the worker directly; skip ARQ enqueue.
        return OcrService(db, queue=None, storage=storage)

    app.dependency_overrides[get_document_service] = _doc_override
    app.dependency_overrides[get_ocr_service] = _ocr_override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_document_service, None)
        app.dependency_overrides.pop(get_ocr_service, None)


def _user_headers(client: TestClient, *, prefix: str = "ocr") -> dict[str, str]:
    email = unique_email(prefix)
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _upload_fixture(client: TestClient, headers: dict[str, str]) -> str:
    data = FIXTURE_PNG.read_bytes()
    files = {"file": ("sample_ocr_text.png", data, "image/png")}
    res = client.post("/api/v1/documents", headers=headers, files=files)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _run_worker(
    job_id: str,
    storage: LocalStorageAdapter,
    *,
    ocr=None,
    max_attempts: int = 3,
    retry_base_seconds: float = 2.0,
):
    with SessionLocal() as session:
        return OcrJobRunner(
            session,
            storage=storage,
            preprocess=_IdentityPreprocess(),
            ocr=ocr or _FakeOcr(),
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
        ).run(uuid.UUID(job_id))


class _FailingOcr:
    def extract(
        self,
        image_bytes: bytes,
        *,
        lang: str | None = None,
        page: int = 1,
    ) -> OcrPageResult:
        raise RuntimeError("forced OCR failure")


def test_create_list_get_poll_until_succeeded_and_results(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    headers = _user_headers(client)
    doc_id = _upload_fixture(client, headers)

    created = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={
            "document_id": doc_id,
            "options": {
                "lang": "korean+en",
                "preprocess": {"deskew": True, "denoise": False, "contrast": True},
            },
        },
    )
    assert created.status_code == 202, created.text
    body = created.json()
    job_id = body["id"]
    assert body["status"] == "queued"
    assert body["document_id"] == doc_id

    listed = client.get("/api/v1/ocr/jobs", headers=headers)
    assert listed.status_code == 200
    assert any(i["id"] == job_id for i in listed.json()["items"])

    detail = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "queued"

    # Results not ready yet
    assert_error_envelope(
        client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=headers),
        status_code=409,
        code="conflict",
    )

    _run_worker(job_id, storage)

    polled = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert polled.status_code == 200, polled.text
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["finished_at"] is not None

    results = client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=headers)
    assert results.status_code == 200, results.text
    payload = results.json()
    assert payload["job_id"] == job_id
    assert len(payload["pages"]) == 1
    assert "HELLO" in payload["pages"][0]["text"].upper()
    assert payload["pages"][0]["confidence"] == 0.99


def test_create_404_unknown_document(client: TestClient) -> None:
    headers = _user_headers(client)
    res = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": str(uuid.uuid4())},
    )
    assert_error_envelope(res, status_code=404, code="not_found")


def test_create_409_document_not_ready(client: TestClient) -> None:
    headers = _user_headers(client)
    doc_id = _upload_fixture(client, headers)
    with SessionLocal() as db:
        doc = db.get(Document, uuid.UUID(doc_id))
        assert doc is not None
        doc.status = DocumentStatus.failed
        db.commit()

    res = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": doc_id},
    )
    assert_error_envelope(res, status_code=409, code="conflict")


def test_ownership_isolation(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    owner = _user_headers(client, prefix="ocr-owner")
    other = _user_headers(client, prefix="ocr-other")
    doc_id = _upload_fixture(client, owner)

    created = client.post(
        "/api/v1/ocr/jobs",
        headers=owner,
        json={"document_id": doc_id},
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]
    _run_worker(job_id, storage)

    assert_error_envelope(
        client.get(f"/api/v1/ocr/jobs/{job_id}", headers=other),
        status_code=403,
        code="forbidden",
    )
    assert_error_envelope(
        client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=other),
        status_code=403,
        code="forbidden",
    )


def test_get_404_unknown_job(client: TestClient) -> None:
    headers = _user_headers(client)
    res = client.get(f"/api/v1/ocr/jobs/{uuid.uuid4()}", headers=headers)
    assert_error_envelope(res, status_code=404, code="not_found")


def test_forced_failure_retries_then_persists_failed(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    """T-4.06: exhaust attempts → status=failed + error + attempt_count."""
    headers = _user_headers(client, prefix="ocr-fail")
    doc_id = _upload_fixture(client, headers)
    created = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": doc_id},
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]

    # Attempt 1 → queued for retry
    out1 = _run_worker(
        job_id,
        storage,
        ocr=_FailingOcr(),
        max_attempts=3,
        retry_base_seconds=2.0,
    )
    assert out1.status == "queued"
    assert out1.attempt_count == 1
    assert out1.retry_delay_seconds == 2.0
    assert "forced OCR failure" in (out1.error or "")

    mid = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert mid.status_code == 200
    assert mid.json()["status"] == "queued"
    assert mid.json()["attempt_count"] == 1
    assert "forced OCR failure" in (mid.json()["error"] or "")

    # Attempt 2 → queued for retry (4s)
    out2 = _run_worker(
        job_id,
        storage,
        ocr=_FailingOcr(),
        max_attempts=3,
        retry_base_seconds=2.0,
    )
    assert out2.status == "queued"
    assert out2.attempt_count == 2
    assert out2.retry_delay_seconds == 4.0

    # Attempt 3 → permanent failed
    out3 = _run_worker(
        job_id,
        storage,
        ocr=_FailingOcr(),
        max_attempts=3,
        retry_base_seconds=2.0,
    )
    assert out3.status == "failed"
    assert out3.attempt_count == 3
    assert out3.retry_delay_seconds is None

    final = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert final.status_code == 200, final.text
    body = final.json()
    assert body["status"] == "failed"
    assert body["attempt_count"] == 3
    assert "forced OCR failure" in (body["error"] or "")
    assert body["finished_at"] is not None

    assert_error_envelope(
        client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=headers),
        status_code=409,
        code="conflict",
    )