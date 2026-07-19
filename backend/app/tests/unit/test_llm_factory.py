"""LLM factory selection / fallback tests (T-5.04)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.adapters.llm_factory import FallbackLlmProvider, LlmFactory
from app.adapters.ports import ChatMessage, ChatResult, LlmUsageStats
from app.exceptions.domain import ProviderError, RateLimitError, ValidationAppError


def _chat_result(provider: str) -> ChatResult:
    return ChatResult(
        provider=provider,
        model="m",
        message=ChatMessage(role="assistant", content=f"from-{provider}"),
        usage=LlmUsageStats(tokens_in=1, tokens_out=1, latency_ms=1),
    )


def _mock_provider(name: str) -> MagicMock:
    mock = MagicMock()
    mock.name = name
    mock.chat.return_value = _chat_result(name)
    mock.vision.return_value = SimpleNamespace(provider=name)
    mock.health.return_value = True
    return mock


@pytest.mark.unit
def test_resolve_primary_from_settings() -> None:
    cfg = SimpleNamespace(
        ai_primary_provider="openai",
        ai_fallback_provider="gemini",
        ai_fallback_enabled=False,
    )
    openai = _mock_provider("openai")
    gemini = _mock_provider("gemini")
    factory = LlmFactory(cfg=cfg, openai=openai, gemini=gemini)  # type: ignore[arg-type]

    provider = factory.resolve()
    assert provider is openai
    assert provider.name == "openai"


@pytest.mark.unit
def test_switch_primary_via_env_only() -> None:
    """Zero code change: flip AI_PRIMARY_PROVIDER → different adapter."""
    cfg = SimpleNamespace(
        ai_primary_provider="gemini",
        ai_fallback_provider="openai",
        ai_fallback_enabled=False,
    )
    openai = _mock_provider("openai")
    gemini = _mock_provider("gemini")
    factory = LlmFactory(cfg=cfg, openai=openai, gemini=gemini)  # type: ignore[arg-type]

    assert factory.resolve() is gemini


@pytest.mark.unit
def test_explicit_request_overrides_primary() -> None:
    cfg = SimpleNamespace(
        ai_primary_provider="openai",
        ai_fallback_provider="gemini",
        ai_fallback_enabled=True,
    )
    openai = _mock_provider("openai")
    gemini = _mock_provider("gemini")
    factory = LlmFactory(cfg=cfg, openai=openai, gemini=gemini)  # type: ignore[arg-type]

    provider = factory.resolve("gemini")
    assert provider is gemini
    # Explicit choice is not wrapped in FallbackLlmProvider
    assert not isinstance(provider, FallbackLlmProvider)


@pytest.mark.unit
def test_fallback_used_on_provider_error() -> None:
    cfg = SimpleNamespace(
        ai_primary_provider="openai",
        ai_fallback_provider="gemini",
        ai_fallback_enabled=True,
    )
    openai = _mock_provider("openai")
    gemini = _mock_provider("gemini")
    openai.chat.side_effect = ProviderError("openai down")
    factory = LlmFactory(cfg=cfg, openai=openai, gemini=gemini)  # type: ignore[arg-type]

    provider = factory.resolve()
    assert isinstance(provider, FallbackLlmProvider)
    result = provider.chat([ChatMessage(role="user", content="hi")])
    assert result.provider == "gemini"
    assert result.message.content == "from-gemini"
    gemini.chat.assert_called_once()


@pytest.mark.unit
def test_fallback_not_used_for_rate_limit() -> None:
    cfg = SimpleNamespace(
        ai_primary_provider="openai",
        ai_fallback_provider="gemini",
        ai_fallback_enabled=True,
    )
    openai = _mock_provider("openai")
    gemini = _mock_provider("gemini")
    openai.chat.side_effect = RateLimitError("slow down")
    factory = LlmFactory(cfg=cfg, openai=openai, gemini=gemini)  # type: ignore[arg-type]

    provider = factory.resolve()
    with pytest.raises(RateLimitError):
        provider.chat([ChatMessage(role="user", content="hi")])
    gemini.chat.assert_not_called()


@pytest.mark.unit
def test_fallback_disabled_propagates_provider_error() -> None:
    cfg = SimpleNamespace(
        ai_primary_provider="openai",
        ai_fallback_provider="gemini",
        ai_fallback_enabled=False,
    )
    openai = _mock_provider("openai")
    gemini = _mock_provider("gemini")
    openai.chat.side_effect = ProviderError("openai down")
    factory = LlmFactory(cfg=cfg, openai=openai, gemini=gemini)  # type: ignore[arg-type]

    provider = factory.resolve()
    with pytest.raises(ProviderError):
        provider.chat([ChatMessage(role="user", content="hi")])
    gemini.chat.assert_not_called()


@pytest.mark.unit
def test_unknown_provider_raises() -> None:
    factory = LlmFactory(
        cfg=SimpleNamespace(
            ai_primary_provider="openai",
            ai_fallback_provider="gemini",
            ai_fallback_enabled=False,
        ),  # type: ignore[arg-type]
        openai=_mock_provider("openai"),
        gemini=_mock_provider("gemini"),
    )
    with pytest.raises(ValidationAppError):
        factory.create("ollama")
