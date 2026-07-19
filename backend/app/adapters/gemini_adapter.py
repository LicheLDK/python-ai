"""Gemini LlmProviderPort adapter (T-5.03 / SDS ADR-012, PRD §16.3)."""

from __future__ import annotations

import base64
import binascii
import time
from typing import Any, Sequence
from urllib.parse import urlparse

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

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

PROVIDER_NAME = "gemini"
DEFAULT_CHAT_MODEL = "gemini-2.0-flash"
DEFAULT_VISION_MODEL = "gemini-2.0-flash"

# Rough public pricing for cost_estimate (USD / token). Tunable later.
_COST_IN_PER_TOKEN = 0.10 / 1_000_000
_COST_OUT_PER_TOKEN = 0.40 / 1_000_000


class GeminiAdapter:
    """google-genai SDK wrapper — services must not import the SDK directly."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any | None = None,
        default_chat_model: str = DEFAULT_CHAT_MODEL,
        default_vision_model: str = DEFAULT_VISION_MODEL,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._default_chat_model = default_chat_model
        self._default_vision_model = default_vision_model
        if client is not None:
            self._client = client
        else:
            self._client = genai.Client(api_key=self._api_key or "missing-key")

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
        system_instruction, contents = self._to_gemini_contents(messages)
        config = self._build_config(params, system_instruction=system_instruction)

        started = time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            self._raise_mapped(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = (getattr(response, "text", None) or "").strip()
        usage = self._usage_from_response(response, latency_ms=latency_ms)
        return ChatResult(
            provider=PROVIDER_NAME,
            model=model,
            message=ChatMessage(role="assistant", content=text),
            usage=usage,
            raw=self._raw_dump(response),
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

        parts: list[Any] = [types.Part.from_text(text=prompt)]
        for image in images:
            parts.append(self._to_image_part(image))

        config = self._build_config(params, system_instruction=None)
        started = time.perf_counter()
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=[types.Content(role="user", parts=parts)],
                config=config,
            )
        except Exception as exc:
            self._raise_mapped(exc)
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = (getattr(response, "text", None) or "").strip()
        usage = self._usage_from_response(response, latency_ms=latency_ms)
        return VisionResult(
            provider=PROVIDER_NAME,
            model=model,
            result=text,
            usage=usage,
            raw=self._raw_dump(response),
        )

    def health(self) -> bool:
        if not self._api_key:
            return False
        try:
            # Lightweight listing; mocked clients can stub this.
            self._client.models.list()
            return True
        except Exception:  # noqa: BLE001 — health is best-effort
            return False

    @staticmethod
    def _to_gemini_contents(
        messages: Sequence[ChatMessage],
    ) -> tuple[str | None, list[types.Content]]:
        system_chunks = [m.content for m in messages if m.role == "system" and m.content]
        system_instruction = "\n\n".join(system_chunks) if system_chunks else None
        contents: list[types.Content] = []
        for message in messages:
            if message.role == "system":
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=message.content)],
                )
            )
        if not contents:
            raise ValidationAppError("chat requires at least one non-system message")
        return system_instruction, contents

    @staticmethod
    def _build_config(
        params: LlmChatParams | LlmVisionParams,
        *,
        system_instruction: str | None,
    ) -> types.GenerateContentConfig:
        kwargs: dict[str, Any] = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if params.max_tokens is not None:
            kwargs["max_output_tokens"] = params.max_tokens
        return types.GenerateContentConfig(**kwargs)

    @staticmethod
    def _to_image_part(image: bytes | str) -> types.Part:
        if isinstance(image, bytes):
            return types.Part.from_bytes(data=image, mime_type="image/png")
        if image.startswith("data:") and ";base64," in image:
            header, b64 = image.split(";base64,", 1)
            mime = header.removeprefix("data:") or "image/png"
            try:
                data = base64.b64decode(b64)
            except (binascii.Error, ValueError) as exc:
                raise ValidationAppError("Invalid data-URL image") from exc
            return types.Part.from_bytes(data=data, mime_type=mime)
        parsed = urlparse(image)
        if parsed.scheme in {"http", "https"}:
            # Let the SDK fetch remote URLs when supported; otherwise treat as text URI part.
            return types.Part.from_uri(file_uri=image, mime_type="image/png")
        raise ValidationAppError("Unsupported image input for Gemini vision")

    @staticmethod
    def _usage_from_response(response: Any, *, latency_ms: int) -> LlmUsageStats:
        meta = getattr(response, "usage_metadata", None)
        tokens_in = int(getattr(meta, "prompt_token_count", 0) or 0) if meta else 0
        tokens_out = int(getattr(meta, "candidates_token_count", 0) or 0) if meta else 0
        cost = tokens_in * _COST_IN_PER_TOKEN + tokens_out * _COST_OUT_PER_TOKEN
        return LlmUsageStats(
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_estimate=round(cost, 6),
        )

    @staticmethod
    def _raw_dump(response: Any) -> dict[str, Any] | None:
        if hasattr(response, "model_dump"):
            try:
                return response.model_dump()
            except Exception:  # noqa: BLE001
                return None
        return None

    @staticmethod
    def _raise_mapped(exc: Exception) -> None:
        code = getattr(exc, "code", None)
        status = getattr(exc, "status", None)
        if isinstance(exc, genai_errors.ClientError):
            if code == 429 or status == "RESOURCE_EXHAUSTED":
                raise RateLimitError(
                    "Gemini rate limit exceeded",
                    details={"provider": PROVIDER_NAME},
                ) from exc
            if code in {400, 401, 403}:
                raise ValidationAppError(
                    str(exc) or "Invalid Gemini request",
                    details={"provider": PROVIDER_NAME, "status_code": code},
                ) from exc
            raise ProviderError(
                str(exc) or "Gemini provider error",
                details={"provider": PROVIDER_NAME, "status_code": code},
            ) from exc
        if isinstance(exc, genai_errors.ServerError):
            raise ProviderError(
                "Gemini upstream unavailable",
                details={"provider": PROVIDER_NAME, "reason": type(exc).__name__},
            ) from exc
        if isinstance(exc, genai_errors.APIError):
            if code == 429:
                raise RateLimitError(
                    "Gemini rate limit exceeded",
                    details={"provider": PROVIDER_NAME},
                ) from exc
            raise ProviderError(
                str(exc) or "Gemini provider error",
                details={"provider": PROVIDER_NAME, "status_code": code},
            ) from exc
        raise ProviderError(
            str(exc) or "Gemini provider error",
            details={"provider": PROVIDER_NAME},
        ) from exc
