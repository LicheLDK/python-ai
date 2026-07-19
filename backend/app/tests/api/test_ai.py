"""AI API tests (T-5.11) — provider mock, prompt resolve, authz, rate limit, SSE."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Sequence

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.llm_factory import LlmFactory
from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmUsageStats,
    LlmVisionParams,
    VisionResult,
)
from app.core.config import Settings
from app.core.constants import REDIS_KEY_AI_RATE_USER
from app.core.database import SessionLocal
from app.core.deps import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.ai import AiRequest, AiUsage
from app.routers.ai import get_ai_service
from app.routers.documents import get_document_service
from app.services.ai_service import AiService
from app.services.document_service import DocumentService
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    admin_bearer_headers,
    login_access_token,
    register_user,
    unique_email,
    user_id_by_email,
)

pytestmark = [pytest.mark.api]


class _FakeLlm:
    name = "openai"

    def __init__(self) -> None:
        self.chat_calls = 0
        self.vision_calls = 0

    def chat(
        self,
        messages: Sequence[ChatMessage],
        params: LlmChatParams | None = None,
    ) -> ChatResult:
        self.chat_calls += 1
        return ChatResult(
            provider="openai",
            model=(params.model if params and params.model else "fake-chat"),
            message=ChatMessage(role="assistant", content="hello-from-fake"),
            usage=LlmUsageStats(tokens_in=3, tokens_out=5, latency_ms=12, cost_estimate=0.001),
        )

    def vision(
        self,
        *,
        images: Sequence[bytes | str],
        prompt: str,
        params: LlmVisionParams | None = None,
    ) -> VisionResult:
        self.vision_calls += 1
        return VisionResult(
            provider="openai",
            model=(params.model if params and params.model else "fake-vision"),
            result={"summary": "ok", "prompt_len": len(prompt), "images": len(images)},
            usage=LlmUsageStats(tokens_in=10, tokens_out=8, latency_ms=20, cost_estimate=0.002),
        )

    def health(self) -> bool:
        return True


@pytest.fixture()
def fake_llm() -> _FakeLlm:
    return _FakeLlm()


@pytest.fixture()
def client(tmp_path: Path, fake_llm: _FakeLlm):
    storage = LocalStorageAdapter(root=tmp_path)
    factory = LlmFactory(openai=fake_llm, gemini=fake_llm)
    cfg = Settings(ai_rate_limit_max=60, ai_rate_limit_window_seconds=60)

    def _docs(db: Session = Depends(get_db)) -> DocumentService:
        return DocumentService(db, storage=storage)

    def _ai(db: Session = Depends(get_db)) -> AiService:
        return AiService(
            db,
            storage=storage,
            llm_factory=factory,
            redis_client=get_redis(),
            cfg=cfg,
        )

    app.dependency_overrides[get_document_service] = _docs
    app.dependency_overrides[get_ai_service] = _ai
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_document_service, None)
        app.dependency_overrides.pop(get_ai_service, None)


def _user_headers(client: TestClient, *, prefix: str = "ai") -> tuple[dict[str, str], str]:
    email = unique_email(prefix)
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}, email


def _admin_headers(client: TestClient) -> dict[str, str]:
    email = unique_email("ai-admin")
    register_user(client, email=email, name="Admin")
    return admin_bearer_headers(email)


def _png_file() -> dict:
    return {"file": ("sample.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")}


def test_prompt_write_forbidden_for_user(client: TestClient) -> None:
    headers, _ = _user_headers(client)
    res = client.post(
        "/api/v1/ai/prompts",
        headers=headers,
        json={"name": "x", "template": "hi"},
    )
    assert_error_envelope(res, status_code=403, code="forbidden")


def test_prompt_create_version_activate(client: TestClient) -> None:
    admin = _admin_headers(client)
    user_headers, _ = _user_headers(client, prefix="ai-reader")

    created = client.post(
        "/api/v1/ai/prompts",
        headers=admin,
        json={
            "name": f"demo-{uuid.uuid4().hex[:8]}",
            "template": "Hello {name}",
            "variables_schema": {"required": ["name"]},
            "activate": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["version"] == 1
    assert body["active"] is True
    prompt_id = body["id"]
    name = body["name"]

    listed = client.get("/api/v1/ai/prompts", headers=user_headers, params={"name": name})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    detail = client.get(f"/api/v1/ai/prompts/{prompt_id}", headers=user_headers)
    assert detail.status_code == 200
    assert detail.json()["template"] == "Hello {name}"

    v2 = client.patch(
        f"/api/v1/ai/prompts/{prompt_id}",
        headers=admin,
        json={"template": "Hi {name}", "create_new_version": True},
    )
    assert v2.status_code == 200, v2.text
    assert v2.json()["version"] == 2
    assert v2.json()["active"] is False
    v2_id = v2.json()["id"]

    activated = client.post(f"/api/v1/ai/prompts/{v2_id}/activate", headers=admin)
    assert activated.status_code == 200
    assert activated.json()["active"] is True

    listed2 = client.get(
        "/api/v1/ai/prompts",
        headers=user_headers,
        params={"name": name, "active": True},
    )
    assert listed2.status_code == 200
    assert listed2.json()["total"] == 1
    assert listed2.json()["items"][0]["id"] == v2_id


def test_chat_persists_usage_and_resolves_prompt(client: TestClient, fake_llm: _FakeLlm) -> None:
    admin = _admin_headers(client)
    headers, email = _user_headers(client)
    name = f"chat-sys-{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/ai/prompts",
        headers=admin,
        json={"name": name, "template": "SYSTEM:{topic}", "activate": True},
    )
    assert created.status_code == 201, created.text

    res = client.post(
        "/api/v1/ai/chat",
        headers=headers,
        json={
            "messages": [{"role": "user", "content": "ping"}],
            "prompt_name": name,
            "variables": {"topic": "ocr"},
            "provider": "openai",
            "model": "fake-chat",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["message"]["content"] == "hello-from-fake"
    assert body["usage"]["tokens_in"] == 3
    assert body["usage"]["tokens_out"] == 5
    assert fake_llm.chat_calls == 1
    request_id = uuid.UUID(body["request_id"])

    with SessionLocal() as db:
        req = db.get(AiRequest, request_id)
        assert req is not None
        assert req.user_id == user_id_by_email(email)
        usage = db.scalars(select(AiUsage).where(AiUsage.request_id == request_id)).one()
        assert usage.tokens_out == 5


def test_chat_missing_prompt_vars(client: TestClient) -> None:
    admin = _admin_headers(client)
    headers, _ = _user_headers(client)
    name = f"vars-{uuid.uuid4().hex[:8]}"
    assert (
        client.post(
            "/api/v1/ai/prompts",
            headers=admin,
            json={"name": name, "template": "Need {x}", "activate": True},
        ).status_code
        == 201
    )
    res = client.post(
        "/api/v1/ai/chat",
        headers=headers,
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "prompt_name": name,
            "variables": {},
        },
    )
    assert_error_envelope(res, status_code=422, code="validation_error")


def test_vision_with_document(client: TestClient, fake_llm: _FakeLlm) -> None:
    headers, _ = _user_headers(client)
    uploaded = client.post("/api/v1/documents", headers=headers, files=_png_file())
    assert uploaded.status_code == 201, uploaded.text
    doc_id = uploaded.json()["id"]

    res = client.post(
        "/api/v1/ai/vision",
        headers=headers,
        json={
            "document_id": doc_id,
            "instruction": "Describe",
            "provider": "openai",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["result"]["summary"] == "ok"
    assert fake_llm.vision_calls == 1


def test_chat_stream_sse(client: TestClient) -> None:
    headers, _ = _user_headers(client)
    with client.stream(
        "POST",
        "/api/v1/ai/chat/stream",
        headers=headers,
        json={"messages": [{"role": "user", "content": "stream"}]},
    ) as res:
        assert res.status_code == 200, res.text
        assert "text/event-stream" in res.headers.get("content-type", "")
        raw = "".join(res.iter_text())
    assert "event: meta" in raw
    assert "event: delta" in raw
    assert "event: done" in raw
    assert "hello-from-fake" in raw


def test_ai_rate_limit_429(client: TestClient, fake_llm: _FakeLlm, tmp_path: Path) -> None:
    headers, email = _user_headers(client, prefix="ai-rl")
    user_id = user_id_by_email(email)
    redis = get_redis()
    key = REDIS_KEY_AI_RATE_USER.format(user_id=str(user_id))
    try:
        # Override service with tiny limit for this test only.
        storage = LocalStorageAdapter(root=tmp_path)
        factory = LlmFactory(openai=fake_llm, gemini=fake_llm)
        cfg = Settings(ai_rate_limit_max=2, ai_rate_limit_window_seconds=60)

        def _ai(db: Session = Depends(get_db)) -> AiService:
            return AiService(
                db,
                storage=storage,
                llm_factory=factory,
                redis_client=redis,
                cfg=cfg,
            )

        app.dependency_overrides[get_ai_service] = _ai
        redis.delete(key)

        for _ in range(2):
            ok = client.post(
                "/api/v1/ai/chat",
                headers=headers,
                json={"messages": [{"role": "user", "content": "x"}]},
            )
            assert ok.status_code == 200, ok.text

        blocked = client.post(
            "/api/v1/ai/chat",
            headers=headers,
            json={"messages": [{"role": "user", "content": "x"}]},
        )
        assert_error_envelope(blocked, status_code=429, code="rate_limited")
    finally:
        redis.delete(key)


def test_seed_prompts_idempotent() -> None:
    from app.scripts.seed_prompts import seed_prompts

    assert seed_prompts() == 0
    assert seed_prompts() == 0
    with SessionLocal() as db:
        from app.models.ai import AiPrompt

        rows = db.scalars(
            select(AiPrompt).where(AiPrompt.name == "ocr.analyze.summary")
        ).all()
        assert len(rows) >= 1
        assert sum(1 for r in rows if r.active) == 1
