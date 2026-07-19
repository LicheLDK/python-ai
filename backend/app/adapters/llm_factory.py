"""LLM provider factory (T-5.04 / SDS ADR-012).

Selection is env-driven (``AI_PRIMARY_PROVIDER``, ``AI_FALLBACK_*``).
Services depend on ``LlmProviderPort`` / this factory — never on concrete SDKs.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.openai_adapter import OpenAiAdapter
from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmProviderPort,
    LlmVisionParams,
    VisionResult,
)
from app.core.config import Settings, settings
from app.exceptions.domain import ProviderError, ValidationAppError

SUPPORTED_PROVIDERS = frozenset({"openai", "gemini"})


class FallbackLlmProvider:
    """Try primary; on upstream ``ProviderError`` only, call fallback once."""

    def __init__(self, primary: LlmProviderPort, fallback: LlmProviderPort) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def name(self) -> str:
        return self._primary.name

    @property
    def primary(self) -> LlmProviderPort:
        return self._primary

    @property
    def fallback(self) -> LlmProviderPort:
        return self._fallback

    def chat(
        self,
        messages: Sequence[ChatMessage],
        params: LlmChatParams | None = None,
    ) -> ChatResult:
        try:
            return self._primary.chat(messages, params)
        except ProviderError:
            return self._fallback.chat(messages, params)

    def vision(
        self,
        *,
        images: Sequence[bytes | str],
        prompt: str,
        params: LlmVisionParams | None = None,
    ) -> VisionResult:
        try:
            return self._primary.vision(images=images, prompt=prompt, params=params)
        except ProviderError:
            return self._fallback.vision(images=images, prompt=prompt, params=params)

    def health(self) -> bool:
        return self._primary.health() or self._fallback.health()


class LlmFactory:
    """Build ``LlmProviderPort`` instances from config / request override."""

    def __init__(
        self,
        *,
        cfg: Settings | None = None,
        openai: LlmProviderPort | None = None,
        gemini: LlmProviderPort | None = None,
    ) -> None:
        self._settings = cfg or settings
        self._openai = openai
        self._gemini = gemini

    def create(self, name: str) -> LlmProviderPort:
        key = name.strip().lower()
        if key not in SUPPORTED_PROVIDERS:
            raise ValidationAppError(
                f"Unsupported AI provider: {name}",
                details={"supported": sorted(SUPPORTED_PROVIDERS)},
            )
        if key == "openai":
            return self._openai if self._openai is not None else OpenAiAdapter()
        return self._gemini if self._gemini is not None else GeminiAdapter()

    def resolve(self, requested: str | None = None) -> LlmProviderPort:
        """Return primary (or requested) provider.

        When ``requested`` is None and ``AI_FALLBACK_ENABLED`` is true, wrap with
        fallback. Explicit ``requested`` skips fallback wrapping (caller chose).
        """
        primary_name = (requested or self._settings.ai_primary_provider).strip().lower()
        primary = self.create(primary_name)
        if requested is not None:
            return primary
        if not self._settings.ai_fallback_enabled:
            return primary
        fallback_name = self._settings.ai_fallback_provider.strip().lower()
        if fallback_name == primary_name:
            return primary
        return FallbackLlmProvider(primary, self.create(fallback_name))


@lru_cache(maxsize=1)
def get_llm_factory() -> LlmFactory:
    """Process-wide factory singleton for FastAPI DI."""
    return LlmFactory()
