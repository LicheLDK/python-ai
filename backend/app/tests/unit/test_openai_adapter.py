"""OpenAI adapter contract tests with mocked SDK (T-5.02)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.adapters.openai_adapter import OpenAiAdapter
from app.adapters.ports import ChatMessage, LlmChatParams, LlmVisionParams
from app.exceptions.domain import ProviderError, RateLimitError, ValidationAppError
from openai import APITimeoutError, RateLimitError as OpenAIRateLimitError


def _completion(*, content: str, model: str = "gpt-4o-mini", prompt_tokens=10, completion_tokens=5):
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content, role="assistant"))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        model_dump=lambda: {"model": model, "ok": True},
    )


@pytest.fixture()
def client() -> MagicMock:
    return MagicMock()


@pytest.fixture()
def adapter(client: MagicMock) -> OpenAiAdapter:
    return OpenAiAdapter(api_key="sk-test", client=client)


@pytest.mark.unit
def test_chat_maps_response(adapter: OpenAiAdapter, client: MagicMock) -> None:
    client.chat.completions.create.return_value = _completion(content="hello world")

    result = adapter.chat(
        [ChatMessage(role="user", content="hi")],
        LlmChatParams(temperature=0.2, max_tokens=64),
    )

    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert result.message.role == "assistant"
    assert result.message.content == "hello world"
    assert result.usage.tokens_in == 10
    assert result.usage.tokens_out == 5
    assert result.usage.latency_ms >= 0
    assert result.usage.cost_estimate >= 0

    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 64
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.unit
def test_vision_encodes_bytes_as_data_url(adapter: OpenAiAdapter, client: MagicMock) -> None:
    client.chat.completions.create.return_value = _completion(content='{"ok":true}')

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 8
    result = adapter.vision(
        images=[png],
        prompt="describe",
        params=LlmVisionParams(model="gpt-4o-mini"),
    )

    assert result.provider == "openai"
    assert result.result == '{"ok":true}'
    content = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "describe"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.unit
def test_vision_empty_images_validation(adapter: OpenAiAdapter) -> None:
    with pytest.raises(ValidationAppError):
        adapter.vision(images=[], prompt="x")


@pytest.mark.unit
def test_rate_limit_maps_to_429(adapter: OpenAiAdapter, client: MagicMock) -> None:
    client.chat.completions.create.side_effect = OpenAIRateLimitError(
        "rate",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    with pytest.raises(RateLimitError) as ei:
        adapter.chat([ChatMessage(role="user", content="x")])
    assert ei.value.status_code == 429


@pytest.mark.unit
def test_timeout_maps_to_502(adapter: OpenAiAdapter, client: MagicMock) -> None:
    client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())
    with pytest.raises(ProviderError) as ei:
        adapter.chat([ChatMessage(role="user", content="x")])
    assert ei.value.status_code == 502


@pytest.mark.unit
def test_health_false_without_key() -> None:
    assert OpenAiAdapter(api_key="", client=MagicMock()).health() is False


@pytest.mark.unit
def test_health_true_when_models_list_ok(client: MagicMock) -> None:
    client.models.list.return_value = []
    assert OpenAiAdapter(api_key="sk-test", client=client).health() is True
