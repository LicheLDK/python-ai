"""OpenAI LlmProviderPort adapter (T-5.02 / SDS ADR-012, PRD §16.3)."""

from __future__ import annotations

import base64
import time
from typing import Any, Sequence

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError as OpenAIRateLimitError,
)

from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmUsageStats,
    LlmVisionParams,
    VisionResult,
)
from app.core.config import settings
from app.exceptions.domain import ProviderError, RateLimitError, ValidationAppError

PROVIDER_NAME = "openai"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_VISION_MODEL = "gpt-4o-mini"

# Rough public pricing for cost_estimate (USD / token). Tunable later.
_COST_IN_PER_TOKEN = 0.15 / 1_000_000
_COST_OUT_PER_TOKEN = 0.60 / 1_000_000


class OpenAiAdapter:
    """Official OpenAI SDK wrapper — services must not import ``openai`` directly."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: OpenAI | None = None,
        default_chat_model: str = DEFAULT_CHAT_MODEL,
        default_vision_model: str = DEFAULT_VISION_MODEL,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._default_chat_model = default_chat_model
        self._default_vision_model = default_vision_model
        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(api_key=self._api_key or "missing-key")

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    def chat(
        self,
        messages: Sequence[ChatMessage],
        params: LlmChatParams | None = None,
    ) -> ChatResult:
        params = params or LlmChatParams()
        model = params.model or self._default_chat_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if params.temperature is not None:
            payload["temperature"] = params.temperature
        if params.max_tokens is not None:
            payload["max_tokens"] = params.max_tokens

        started = time.perf_counter()
        try:
            response = self._client.chat.completions.create(**payload)
        except Exception as exc:
            self._raise_mapped(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)

        choice = response.choices[0].message if response.choices else None
        content = (choice.content or "") if choice else ""
        usage = self._usage_from_response(response, latency_ms=latency_ms)
        return ChatResult(
            provider=PROVIDER_NAME,
            model=getattr(response, "model", None) or model,
            message=ChatMessage(role="assistant", content=content),
            usage=usage,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    def vision(
        self,
        *,
        images: Sequence[bytes | str],
        prompt: str,
        params: LlmVisionParams | None = None,
    ) -> VisionResult:
        if not images:
            raise ValidationAppError("vision requires at least one image")
        params = params or LlmVisionParams()
        model = params.model or self._default_vision_model

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._to_image_url(image)},
                }
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
        }
        if params.temperature is not None:
            payload["temperature"] = params.temperature
        if params.max_tokens is not None:
            payload["max_tokens"] = params.max_tokens

        started = time.perf_counter()
        try:
            response = self._client.chat.completions.create(**payload)
        except Exception as exc:
            self._raise_mapped(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)

        choice = response.choices[0].message if response.choices else None
        text = (choice.content or "") if choice else ""
        usage = self._usage_from_response(response, latency_ms=latency_ms)
        return VisionResult(
            provider=PROVIDER_NAME,
            model=getattr(response, "model", None) or model,
            result=text,
            usage=usage,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    def health(self) -> bool:
        if not self._api_key:
            return False
        try:
            self._client.models.list()
            return True
        except Exception:  # noqa: BLE001 — health is best-effort
            return False

    @staticmethod
    def _to_image_url(image: bytes | str) -> str:
        if isinstance(image, str):
            return image
        b64 = base64.b64encode(image).decode("ascii")
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def _usage_from_response(response: Any, *, latency_ms: int) -> LlmUsageStats:
        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        tokens_out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        cost = tokens_in * _COST_IN_PER_TOKEN + tokens_out * _COST_OUT_PER_TOKEN
        return LlmUsageStats(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_estimate=round(cost, 6),
        )

    @staticmethod
    def _raise_mapped(exc: Exception) -> None:
        if isinstance(exc, OpenAIRateLimitError):
            raise RateLimitError(
                "OpenAI rate limit exceeded",
                details={"provider": PROVIDER_NAME},
            ) from exc
        if isinstance(exc, (BadRequestError, AuthenticationError)):
            raise ValidationAppError(
                str(exc) or "Invalid OpenAI request",
                details={"provider": PROVIDER_NAME},
            ) from exc
        if isinstance(exc, (APITimeoutError, APIConnectionError)):
            raise ProviderError(
                "OpenAI upstream unavailable",
                details={"provider": PROVIDER_NAME, "reason": type(exc).__name__},
            ) from exc
        if isinstance(exc, APIStatusError):
            status = getattr(exc, "status_code", None)
            if status == 429:
                raise RateLimitError(
                    "OpenAI rate limit exceeded",
                    details={"provider": PROVIDER_NAME},
                ) from exc
            raise ProviderError(
                str(exc) or "OpenAI provider error",
                details={"provider": PROVIDER_NAME, "status_code": status},
            ) from exc
        raise ProviderError(
            str(exc) or "OpenAI provider error",
            details={"provider": PROVIDER_NAME},
        ) from exc
