"""OCR API + worker integration tests (T-4.08).

Covers:
1. Mocked OCR engine — full upload → job → worker → results path
2. Real-ish fixture path — sample PNG through OpenCV preprocess + PaddleOCR
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.opencv_preprocess_adapter import OpenCvPreprocessAdapter
from app.adapters.paddle_ocr_adapter import PaddleOcrAdapter
from app.adapters.ports import OcrPageResult, PreprocessOptions
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.main import app
from app.routers.documents import get_document_service
from app.routers.ocr import get_ocr_service
from app.services.document_service import DocumentService
from app.services.ocr_service import OcrService
from app.tests.helpers import login_access_token, register_user, unique_email
from app.workers.ocr_jobs import OcrJobRunner

pytestmark = [pytest.mark.integration]

FIXTURE_PNG = (
    Path(__file__).resolve().parent.parent / "fixtures" / "sample_ocr_text.png"
)


class _IdentityPreprocess:
    def process(self, image_bytes: bytes, options: PreprocessOptions | None = None) -> bytes:
        return image_bytes


class _MockOcrEngine:
    """Deterministic stand-in for PaddleOCR in the mocked path."""

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
            text="MOCKED HELLO OCR",
            boxes=[
                {
                    "text": "MOCKED HELLO OCR",
                    "confidence": 0.98,
                    "points": [[1.0, 1.0], [100.0, 1.0], [100.0, 40.0], [1.0, 40.0]],
                }
            ],
            confidence=0.98,
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


def _auth_headers(client: TestClient, *, prefix: str) -> dict[str, str]:
    email = unique_email(prefix)
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _upload_fixture(client: TestClient, headers: dict[str, str]) -> str:
    assert FIXTURE_PNG.is_file(), f"missing fixture: {FIXTURE_PNG}"
    files = {
        "file": ("sample_ocr_text.png", FIXTURE_PNG.read_bytes(), "image/png"),
    }
    res = client.post("/api/v1/documents", headers=headers, files=files)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["page_count"] == 1
    return body["id"]


def test_mocked_engine_upload_job_worker_results(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    """Mocked engine: API create → worker run → poll succeeded → results."""
    headers = _auth_headers(client, prefix="ocr-int-mock")
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
    job_id = created.json()["id"]
    assert created.json()["status"] == "queued"

    with SessionLocal() as session:
        outcome = OcrJobRunner(
            session,
            storage=storage,
            preprocess=_IdentityPreprocess(),
            ocr=_MockOcrEngine(),
        ).run(uuid.UUID(job_id))
    assert outcome.status == "succeeded"
    assert outcome.attempt_count == 1

    polled = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"
    assert polled.json()["attempt_count"] == 1
    assert polled.json()["error"] is None

    results = client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=headers)
    assert results.status_code == 200, results.text
    pages = results.json()["pages"]
    assert len(pages) == 1
    assert pages[0]["page"] == 1
    assert "MOCKED" in pages[0]["text"].upper()
    assert pages[0]["confidence"] == 0.98
    assert isinstance(pages[0]["boxes"], list) and len(pages[0]["boxes"]) >= 1


def test_real_fixture_opencv_paddle_pipeline(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    """Real-ish path: fixture PNG → OpenCV preprocess → PaddleOCR → persisted results."""
    headers = _auth_headers(client, prefix="ocr-int-real")
    doc_id = _upload_fixture(client, headers)

    created = client.post(
        "/api/v1/ocr/jobs",
        headers=headers,
        json={
            "document_id": doc_id,
            "options": {
                "lang": "korean+en",
                "preprocess": {"deskew": False, "denoise": False, "contrast": True},
            },
        },
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]

    with SessionLocal() as session:
        outcome = OcrJobRunner(
            session,
            storage=storage,
            preprocess=OpenCvPreprocessAdapter(),
            ocr=PaddleOcrAdapter(default_lang="korean+en"),
        ).run(uuid.UUID(job_id))

    assert outcome.status == "succeeded", outcome.error
    assert outcome.attempt_count == 1

    polled = client.get(f"/api/v1/ocr/jobs/{job_id}", headers=headers)
    assert polled.status_code == 200
    assert polled.json()["status"] == "succeeded"

    results = client.get(f"/api/v1/ocr/jobs/{job_id}/results", headers=headers)
    assert results.status_code == 200, results.text
    pages = results.json()["pages"]
    assert len(pages) == 1
    text = (pages[0]["text"] or "").strip()
    assert text, "expected non-empty OCR text from fixture"
    normalized = text.upper().replace(" ", "")
    assert "HELLO" in normalized or "OCR" in normalized
    assert pages[0]["confidence"] is not None
    assert 0.0 <= float(pages[0]["confidence"]) <= 1.0
    assert isinstance(pages[0]["boxes"], list) and len(pages[0]["boxes"]) >= 1
