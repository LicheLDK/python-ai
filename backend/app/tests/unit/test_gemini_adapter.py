"""Gemini adapter contract tests with mocked SDK (T-5.03)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.genai.errors import ClientError, ServerError

from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.ports import ChatMessage, LlmChatParams, LlmVisionParams
from app.exceptions.domain import ProviderError, RateLimitError, ValidationAppError


def _response(*, text: str, prompt_tokens: int = 11, candidates_tokens: int = 7):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_tokens,
            candidates_token_count=candidates_tokens,
        ),
        model_dump=lambda: {"text": text, "ok": True},
    )


@pytest.fixture()
def client() -> MagicMock:
    mock = MagicMock()
    mock.models = MagicMock()
    return mock


@pytest.fixture()
def adapter(client: MagicMock) -> GeminiAdapter:
    return GeminiAdapter(api_key="g-test", client=client)


@pytest.mark.unit
def test_chat_maps_response(adapter: GeminiAdapter, client: MagicMock) -> None:
    client.models.generate_content.return_value = _response(text="안녕하세요")

    result = adapter.chat(
        [
            ChatMessage(role="system", content="be brief"),
            ChatMessage(role="user", content="hi"),
        ],
        LlmChatParams(temperature=0.1, max_tokens=128),
    )

    assert result.provider == "gemini"
    assert result.model == "gemini-2.0-flash"
    assert result.message.content == "안녕하세요"
    assert result.usage.tokens_in == 11
    assert result.usage.tokens_out == 7
    assert result.usage.latency_ms >= 0

    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.0-flash"
    assert kwargs["config"].temperature == 0.1
    assert kwargs["config"].max_output_tokens == 128
    assert kwargs["config"].system_instruction == "be brief"
    assert len(kwargs["contents"]) == 1
    assert kwargs["contents"][0].role == "user"


@pytest.mark.unit
def test_vision_accepts_bytes(adapter: GeminiAdapter, client: MagicMock) -> None:
    client.models.generate_content.return_value = _response(text="a cat")

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 8
    result = adapter.vision(images=[png], prompt="what is this?")

    assert result.provider == "gemini"
    assert result.result == "a cat"
    contents = client.models.generate_content.call_args.kwargs["contents"]
    assert contents[0].role == "user"
    assert len(contents[0].parts) == 2


@pytest.mark.unit
def test_vision_empty_images_validation(adapter: GeminiAdapter) -> None:
    with pytest.raises(ValidationAppError):
        adapter.vision(images=[], prompt="x")


@pytest.mark.unit
def test_rate_limit_maps_to_429(adapter: GeminiAdapter, client: MagicMock) -> None:
    client.models.generate_content.side_effect = ClientError(
        429,
        {"error": {"message": "quota"}},
    )
    with pytest.raises(RateLimitError) as ei:
        adapter.chat([ChatMessage(role="user", content="x")])
    assert ei.value.status_code == 429


@pytest.mark.unit
def test_server_error_maps_to_502(adapter: GeminiAdapter, client: MagicMock) -> None:
    client.models.generate_content.side_effect = ServerError(
        503,
        {"error": {"message": "unavailable"}},
    )
    with pytest.raises(ProviderError) as ei:
        adapter.chat([ChatMessage(role="user", content="x")])
    assert ei.value.status_code == 502


@pytest.mark.unit
def test_health_false_without_key() -> None:
    assert GeminiAdapter(api_key="", client=MagicMock()).health() is False


@pytest.mark.unit
def test_health_true_when_models_list_ok(client: MagicMock) -> None:
    client.models.list.return_value = []
    assert GeminiAdapter(api_key="g-test", client=client).health() is True
