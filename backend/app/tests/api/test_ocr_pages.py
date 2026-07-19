"""PDF page helpers + OCR page-limit tests (T-4.07)."""

from __future__ import annotations

import uuid
from pathlib import Path

import fitz
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.services.ocr_service as ocr_service_mod
from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.ports import OcrPageResult, PreprocessOptions
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.main import app
from app.routers.documents import get_document_service
from app.routers.ocr import get_ocr_service
from app.services.document_service import DocumentService
from app.services.ocr_service import OcrService
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import login_access_token, register_user, unique_email
from app.utils.pdf_pages import count_pdf_pages, render_pdf_pages_as_png
from app.workers.ocr_jobs import OcrJobRunner

pytestmark = [pytest.mark.api]


def _make_pdf(pages: int = 2) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=300, height=200)
        page.insert_text((40, 100), f"PDF PAGE {i + 1}", fontsize=16)
    data = doc.tobytes()
    doc.close()
    return data


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
        assert image_bytes.startswith(b"\x89PNG") or len(image_bytes) > 0
        return OcrPageResult(
            page=page,
            text=f"PAGE {page} TEXT",
            boxes=[{"text": f"PAGE {page}", "confidence": 0.9, "points": [[0, 0], [1, 0], [1, 1], [0, 1]]}],
            confidence=0.9,
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


def _user_headers(client: TestClient, *, prefix: str = "pdf") -> dict[str, str]:
    email = unique_email(prefix)
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
def test_count_and_render_pdf_pages() -> None:
    data = _make_pdf(3)
    assert count_pdf_pages(data) == 3
    pngs = render_pdf_pages_as_png(data, max_pages=2)
    assert len(pngs) == 2
    assert all(p.startswith(b"\x89PNG") for p in pngs)


def test_upload_pdf_sets_page_count(client: TestClient) -> None:
    headers = _user_headers(client)
    files = {"file": ("multi.pdf", _make_pdf(3), "application/pdf")}
    res = client.post("/api/v1/documents", headers=headers, files=files)
    assert res.status_code == 201, res.text
    assert res.json()["page_count"] == 3
    assert res.json()["mime_type"] == "application/pdf"


def test_create_ocr_job_422_when_over_page_limit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ocr_service_mod.settings, "ocr_max_pages", 2)
    headers = _user_headers(client, prefix="pdf-limit")
    files = {"file": ("big.pdf", _make_pdf(3), "application/pdf")}
    up = client.post("/api/v1/documents", headers=headers, files=files)
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    res = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": doc_id},
    )
    assert_error_envelope(res, status_code=422, code="validation_error")
    assert res.json()["details"]["page_count"] == 3
    assert res.json()["details"]["max_pages"] == 2


def test_pdf_split_ocr_multi_page_results(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    headers = _user_headers(client, prefix="pdf-ocr")
    files = {"file": ("two.pdf", _make_pdf(2), "application/pdf")}
    up = client.post("/api/v1/documents", headers=headers, files=files)
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]

    created = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": doc_id},
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]

    with SessionLocal() as session:
        outcome = OcrJobRunner(
            session,
            storage=storage,
            preprocess=_IdentityPreprocess(),
            ocr=_FakeOcr(),
            max_pages=20,
        ).run(uuid.UUID(job_id))
    assert outcome.status == "succeeded"

    results = client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=headers)
    assert results.status_code == 200, results.text
    pages = results.json()["pages"]
    assert len(pages) == 2
    assert pages[0]["page"] == 1 and "PAGE 1" in pages[0]["text"]
    assert pages[1]["page"] == 2 and "PAGE 2" in pages[1]["text"]


def test_worker_permanent_fail_when_over_page_limit(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    """Worker enforces limit even if job was queued with a higher limit."""
    headers = _user_headers(client, prefix="pdf-worker-limit")
    files = {"file": ("two.pdf", _make_pdf(2), "application/pdf")}
    up = client.post("/api/v1/documents", headers=headers, files=files)
    assert up.status_code == 201, up.text

    created = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={"document_id": up.json()["id"]},
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]

    with SessionLocal() as session:
        outcome = OcrJobRunner(
            session,
            storage=storage,
            preprocess=_IdentityPreprocess(),
            ocr=_FakeOcr(),
            max_pages=1,  # force over-limit at worker
            max_attempts=3,
        ).run(uuid.UUID(job_id))

    assert outcome.status == "failed"
    assert outcome.retry_delay_seconds is None
    assert "page limit" in (outcome.error or "").lower()

    detail = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "failed"
    assert "page limit" in (detail.json()["error"] or "").lower()
    # Permanent — only one attempt consumed
    assert detail.json()["attempt_count"] == 1
