"""Ollama LlmProviderPort adapter (T-13.01 / B-1.1-OLLAMA).

Talks to the Ollama HTTP API (``/api/chat``, ``/api/tags``).
No API key required; local/LAN endpoint via ``OLLAMA_BASE_URL``.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Sequence

import httpx

from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmUsageStats,
    LlmVisionParams,
    VisionResult,
)
from app.core.config import settings
from app.exceptions.domain import ProviderError, ValidationAppError

PROVIDER_NAME = "ollama"
DEFAULT_CHAT_MODEL = "llama3.2"
DEFAULT_VISION_MODEL = "llava"


class OllamaAdapter:
    """httpx client for Ollama — services must not call Ollama HTTP directly."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        default_chat_model: str | None = None,
        default_vision_model: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else float(settings.ollama_timeout_seconds)
        )
        self._default_chat_model = default_chat_model or settings.ollama_chat_model
        self._default_vision_model = (
            default_vision_model or settings.ollama_vision_model
        )
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
        )

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
            "stream": False,
        }
        options = self._options(params.temperature, params.max_tokens)
        if options:
            payload["options"] = options

        started = time.perf_counter()
        data = self._post_json("/api/chat", payload)
        latency_ms = int((time.perf_counter() - started) * 1000)

        message = data.get("message") or {}
        content = str(message.get("content") or "")
        usage = self._usage_from_response(data, latency_ms=latency_ms)
        return ChatResult(
            provider=PROVIDER_NAME,
            model=str(data.get("model") or model),
            message=ChatMessage(role="assistant", content=content),
            usage=usage,
            raw=data if isinstance(data, dict) else None,
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

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [self._to_b64(image) for image in images],
                }
            ],
            "stream": False,
        }
        options = self._options(params.temperature, params.max_tokens)
        if options:
            payload["options"] = options

        started = time.perf_counter()
        data = self._post_json("/api/chat", payload)
        latency_ms = int((time.perf_counter() - started) * 1000)

        message = data.get("message") or {}
        text = str(message.get("content") or "")
        usage = self._usage_from_response(data, latency_ms=latency_ms)
        return VisionResult(
            provider=PROVIDER_NAME,
            model=str(data.get("model") or model),
            result=text,
            usage=usage,
            raw=data if isinstance(data, dict) else None,
        )

    def health(self) -> bool:
        try:
            res = self._client.get("/api/tags")
            return res.status_code == 200
        except Exception:  # noqa: BLE001 — health is best-effort
            return False

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            res = self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "Ollama request timed out",
                details={"provider": PROVIDER_NAME, "reason": "timeout"},
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "Ollama upstream unavailable",
                details={"provider": PROVIDER_NAME, "reason": type(exc).__name__},
            ) from exc

        if res.status_code >= 400:
            detail = self._error_detail(res)
            if res.status_code in {400, 404}:
                raise ValidationAppError(
                    detail or "Invalid Ollama request",
                    details={"provider": PROVIDER_NAME, "status_code": res.status_code},
                )
            raise ProviderError(
                detail or "Ollama provider error",
                details={"provider": PROVIDER_NAME, "status_code": res.status_code},
            )

        try:
            data = res.json()
        except ValueError as exc:
            raise ProviderError(
                "Ollama returned non-JSON response",
                details={"provider": PROVIDER_NAME},
            ) from exc
        if not isinstance(data, dict):
            raise ProviderError(
                "Ollama returned unexpected payload",
                details={"provider": PROVIDER_NAME},
            )
        return data

    @staticmethod
    def _options(
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        opts: dict[str, Any] = {}
        if temperature is not None:
            opts["temperature"] = temperature
        if max_tokens is not None:
            opts["num_predict"] = max_tokens
        return opts

    @staticmethod
    def _to_b64(image: bytes | str) -> str:
        if isinstance(image, str):
            if image.startswith("data:") and "," in image:
                return image.split(",", 1)[1]
            # Already base64 or opaque string — pass through.
            return image
        return base64.b64encode(image).decode("ascii")

    @staticmethod
    def _usage_from_response(data: dict[str, Any], *, latency_ms: int) -> LlmUsageStats:
        tokens_in = int(data.get("prompt_eval_count") or 0)
        tokens_out = int(data.get("eval_count") or 0)
        return LlmUsageStats(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_estimate=0.0,
        )

    @staticmethod
    def _error_detail(res: httpx.Response) -> str:
        try:
            body = res.json()
            if isinstance(body, dict):
                err = body.get("error")
                if isinstance(err, str) and err.strip():
                    return err
        except ValueError:
            pass
        text = (res.text or "").strip()
        return text[:500] if text else f"HTTP {res.status_code}"
