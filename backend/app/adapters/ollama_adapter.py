"""Ollama LlmProviderPort stub (T-5.10) — reserved for v1.1.

Not registered in ``LlmFactory`` / ``SUPPORTED_PROVIDERS``. Interface-only
placeholder so services can later wire a local model without reshaping ports.
"""

from __future__ import annotations

from typing import Sequence

from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmVisionParams,
    VisionResult,
)

PROVIDER_NAME = "ollama"


class OllamaAdapter:
    """v1.1 stub — raises ``NotImplementedError`` on all operations."""

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    def chat(
        self,
        messages: Sequence[ChatMessage],
        params: LlmChatParams | None = None,
    ) -> ChatResult:
        raise NotImplementedError(
            "OllamaAdapter is reserved for v1.1 and is not wired in LlmFactory"
        )

    def vision(
        self,
        *,
        images: Sequence[bytes | str],
        prompt: str,
        params: LlmVisionParams | None = None,
    ) -> VisionResult:
        raise NotImplementedError(
            "OllamaAdapter is reserved for v1.1 and is not wired in LlmFactory"
        )

    def health(self) -> bool:
        return False
