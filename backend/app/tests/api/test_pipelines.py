"""Pipeline API + worker tests (T-6.04) with mocked OCR/LLM."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Sequence

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.llm_factory import LlmFactory
from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmUsageStats,
    OcrPageResult,
    PreprocessOptions,
)
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.main import app
from app.repositories.ai_prompt_repository import AiPromptRepository
from app.routers.documents import get_document_service
from app.routers.pipelines import get_pipeline_service
from app.services.document_service import DocumentService
from app.services.pipeline_service import PipelineService
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    login_access_token,
    register_user,
    unique_email,
)
from app.workers.ocr_jobs import OcrJobRunner, OcrRunOutcome
from app.workers.pipeline_jobs import PipelineRunner

pytestmark = [pytest.mark.api]


class _FakeLlm:
    name = "openai"

    def chat(
        self,
        messages: Sequence[ChatMessage],
        params: LlmChatParams | None = None,
    ) -> ChatResult:
        return ChatResult(
            provider="openai",
            model=(params.model if params and params.model else "fake"),
            message=ChatMessage(role="assistant", content="pipeline-summary"),
            usage=LlmUsageStats(tokens_in=2, tokens_out=4, latency_ms=5, cost_estimate=0.0),
        )

    def vision(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def health(self) -> bool:
        return True


class _FakeOcr:
    def extract(self, image: bytes, *, lang: str | None = None, page: int = 1) -> OcrPageResult:
        return OcrPageResult(page=page, text="hello ocr", boxes=[], confidence=0.9)


class _FakePreprocess:
    def process(self, image: bytes, options: PreprocessOptions | None = None) -> bytes:
        return image


class _FailOcrRunner(OcrJobRunner):
    def run(self, job_id: uuid.UUID) -> OcrRunOutcome:
        from app.models.ocr import OcrJobStatus
        from datetime import UTC, datetime

        job = self._jobs.get_by_id(job_id)
        assert job is not None
        self._jobs.mark_running(job, started_at=datetime.now(UTC))
        self._jobs.mark_failed(
            job,
            finished_at=datetime.now(UTC),
            error="forced ocr failure",
        )
        self._session.commit()
        return OcrRunOutcome(
            status=OcrJobStatus.failed.value,
            attempt_count=1,
            error="forced ocr failure",
        )


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageAdapter:
    return LocalStorageAdapter(root=tmp_path)


@pytest.fixture()
def client(storage: LocalStorageAdapter):
    def _docs(db: Session = Depends(get_db)) -> DocumentService:
        return DocumentService(db, storage=storage)

    def _pipes(db: Session = Depends(get_db)) -> PipelineService:
        # No queue — tests run worker synchronously.
        return PipelineService(db, queue=None, storage=storage)

    app.dependency_overrides[get_document_service] = _docs
    app.dependency_overrides[get_pipeline_service] = _pipes
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_document_service, None)
        app.dependency_overrides.pop(get_pipeline_service, None)


def _headers(client: TestClient) -> dict[str, str]:
    email = unique_email("pipe")
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _png() -> dict:
    return {"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * 32, "image/png")}


def _ensure_prompt() -> None:
    with SessionLocal() as db:
        repo = AiPromptRepository(db)
        if repo.get_by_name_version("ocr.analyze.summary", 1) is None:
            repo.deactivate_active_for_name("ocr.analyze.summary")
            repo.create(
                name="ocr.analyze.summary",
                version=1,
                template="Summarize:\n{ocr_text}",
                variables_schema={"required": ["ocr_text"]},
                active=True,
            )
            db.commit()


def _run_pipeline_sync(
    *,
    run_id: uuid.UUID,
    storage: LocalStorageAdapter,
    fail_ocr: bool = False,
) -> dict:
    fake = _FakeLlm()
    factory = LlmFactory(openai=fake, gemini=fake)
    with SessionLocal() as session:
        if fail_ocr:
            ocr_runner = _FailOcrRunner(session, storage=storage, max_attempts=1)
        else:
            ocr_runner = OcrJobRunner(
                session,
                storage=storage,
                preprocess=_FakePreprocess(),
                ocr=_FakeOcr(),
                max_attempts=1,
            )
        runner = PipelineRunner(
            session,
            storage=storage,
            llm_factory=factory,
            ocr_runner=ocr_runner,
        )
        return runner.run(run_id)


def test_pipeline_create_list_get_and_succeed(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    _ensure_prompt()
    headers = _headers(client)
    uploaded = client.post("/api/v1/documents", headers=headers, files=_png())
    assert uploaded.status_code == 201, uploaded.text
    doc_id = uploaded.json()["id"]

    created = client.post(
        "/api/v1/pipelines/runs",
        headers=headers,
        json={"document_id": doc_id, "ai": {"prompt_name": "ocr.analyze.summary"}},
    )
    assert created.status_code == 202, created.text
    run_id = uuid.UUID(created.json()["id"])
    assert created.json()["status"] == "queued"

    outcome = _run_pipeline_sync(run_id=run_id, storage=storage)
    assert outcome["status"] == "succeeded"

    detail = client.get(f"/api/v1/pipelines/runs/{run_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "succeeded"
    names = [s["name"] for s in body["stages"]]
    assert names == ["preprocess", "ocr", "ai_analyze", "persist"]
    assert all(s["status"] == "succeeded" for s in body["stages"])
    assert body["ocr_job_id"] is not None
    assert body["ai_request_id"] is not None

    listed = client.get("/api/v1/pipelines/runs", headers=headers)
    assert listed.status_code == 200
    assert any(i["id"] == str(run_id) for i in listed.json()["items"])


def test_pipeline_partial_failure_keeps_prior_stages(
    client: TestClient,
    storage: LocalStorageAdapter,
) -> None:
    _ensure_prompt()
    headers = _headers(client)
    uploaded = client.post("/api/v1/documents", headers=headers, files=_png())
    doc_id = uploaded.json()["id"]
    created = client.post(
        "/api/v1/pipelines/runs",
        headers=headers,
        json={"document_id": doc_id},
    )
    run_id = uuid.UUID(created.json()["id"])

    outcome = _run_pipeline_sync(run_id=run_id, storage=storage, fail_ocr=True)
    assert outcome["status"] == "failed"
    assert outcome.get("failed_stage") == "ocr"

    detail = client.get(f"/api/v1/pipelines/runs/{run_id}", headers=headers)
    body = detail.json()
    assert body["status"] == "failed"
    by_name = {s["name"]: s for s in body["stages"]}
    assert by_name["preprocess"]["status"] == "succeeded"
    assert by_name["preprocess"].get("output_ref")
    assert by_name["ocr"]["status"] == "failed"
    assert "forced ocr failure" in (by_name["ocr"].get("error") or "")
    assert by_name["ocr"].get("output_ref", {}).get("ocr_job_id")
    assert by_name["ai_analyze"]["status"] == "pending"
    assert by_name["persist"]["status"] == "pending"


def test_pipeline_ownership_404(client: TestClient) -> None:
    headers_a = _headers(client)
    headers_b = _headers(client)
    uploaded = client.post("/api/v1/documents", headers=headers_a, files=_png())
    doc_id = uploaded.json()["id"]
    created = client.post(
        "/api/v1/pipelines/runs",
        headers=headers_a,
        json={"document_id": doc_id},
    )
    run_id = created.json()["id"]
    assert_error_envelope(
        client.get(f"/api/v1/pipelines/runs/{run_id}", headers=headers_b),
        status_code=403,
        code="forbidden",
    )
