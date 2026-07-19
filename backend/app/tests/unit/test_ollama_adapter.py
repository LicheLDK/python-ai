"""Ollama adapter unit tests (T-13.01 / T-13.04)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.llm_factory import LlmFactory, SUPPORTED_PROVIDERS
from app.adapters.ollama_adapter import OllamaAdapter, PROVIDER_NAME
from app.adapters.ports import ChatMessage
from app.exceptions.domain import ProviderError, ValidationAppError


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/tags":
        return httpx.Response(200, json={"models": [{"name": "llama3.2"}]})
    if request.url.path == "/api/chat":
        body = json.loads(request.content.decode())
        assert body.get("stream") is False
        if "images" in (body.get("messages") or [{}])[0]:
            content = "I see an image."
        else:
            content = "hello-local"
        return httpx.Response(
            200,
            json={
                "model": body.get("model"),
                "message": {"role": "assistant", "content": content},
                "prompt_eval_count": 3,
                "eval_count": 5,
            },
        )
    return httpx.Response(404, json={"error": "not found"})


@pytest.fixture
def adapter() -> OllamaAdapter:
    transport = httpx.MockTransport(_handler)
    client = httpx.Client(base_url="http://ollama.test", transport=transport)
    return OllamaAdapter(
        base_url="http://ollama.test",
        client=client,
        default_chat_model="llama3.2",
        default_vision_model="llava",
    )


@pytest.mark.unit
def test_ollama_in_factory_supported() -> None:
    assert PROVIDER_NAME == "ollama"
    assert "ollama" in SUPPORTED_PROVIDERS


@pytest.mark.unit
def test_ollama_chat(adapter: OllamaAdapter) -> None:
    result = adapter.chat([ChatMessage(role="user", content="hi")])
    assert result.provider == "ollama"
    assert result.model == "llama3.2"
    assert result.message.content == "hello-local"
    assert result.usage.tokens_in == 3
    assert result.usage.tokens_out == 5
    assert result.usage.cost_estimate == 0.0


@pytest.mark.unit
def test_ollama_vision(adapter: OllamaAdapter) -> None:
    result = adapter.vision(images=[b"\x89PNG"], prompt="describe")
    assert result.provider == "ollama"
    assert result.model == "llava"
    assert "image" in str(result.result).lower()


@pytest.mark.unit
def test_ollama_health(adapter: OllamaAdapter) -> None:
    assert adapter.health() is True


@pytest.mark.unit
def test_ollama_maps_404_to_validation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'nope' not found"})

    client = httpx.Client(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )
    adapter = OllamaAdapter(client=client)
    with pytest.raises(ValidationAppError, match="not found"):
        adapter.chat([ChatMessage(role="user", content="hi")])


@pytest.mark.unit
def test_ollama_maps_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(handler),
    )
    adapter = OllamaAdapter(client=client)
    with pytest.raises(ProviderError, match="unavailable"):
        adapter.chat([ChatMessage(role="user", content="hi")])


@pytest.mark.unit
def test_factory_resolves_ollama() -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    ollama = MagicMock()
    ollama.name = "ollama"
    factory = LlmFactory(
        cfg=SimpleNamespace(
            ai_primary_provider="ollama",
            ai_fallback_provider="openai",
            ai_fallback_enabled=False,
        ),  # type: ignore[arg-type]
        ollama=ollama,
    )
    assert factory.resolve() is ollama
    assert factory.create("ollama") is ollama
