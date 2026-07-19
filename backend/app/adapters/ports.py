"""Adapter ports / protocols (SDS ADR-012, ADR-014).

T-3.02 StoragePort · T-4.03 ImagePreprocessPort · T-4.04 OcrEnginePort ·
T-5.02 LlmProviderPort · T-15.01 EmbeddingPort.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, Sequence, runtime_checkable


@runtime_checkable
class StoragePort(Protocol):
    """Provider-agnostic object storage (local volume now; S3 later)."""

    def build_document_key(
        self,
        document_id: uuid.UUID,
        *,
        at: datetime | None = None,
    ) -> str:
        """Return storage_key like ``documents/YYYY/MM/{uuid}/original.bin``."""
        ...

    def put(self, storage_key: str, data: bytes) -> None:
        """Write bytes to the given key."""
        ...

    def get(self, storage_key: str) -> bytes:
        """Read bytes for the key. Raises FileNotFoundError if missing."""
        ...

    def exists(self, storage_key: str) -> bool:
        ...

    def delete(self, storage_key: str) -> None:
        """Delete object if present (no error if missing)."""
        ...


@dataclass(frozen=True)
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass(frozen=True)
class LlmUsageStats:
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cost_estimate: float = 0.0


@dataclass(frozen=True)
class LlmChatParams:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class LlmVisionParams:
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ChatResult:
    provider: str
    model: str
    message: ChatMessage
    usage: LlmUsageStats
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class VisionResult:
    provider: str
    model: str
    result: str | dict[str, Any]
    usage: LlmUsageStats
    raw: dict[str, Any] | None = None


@runtime_checkable
class LlmProviderPort(Protocol):
    """LLM chat/vision adapter (PRD §16.3 / SDS ADR-012)."""

    @property
    def name(self) -> str:
        """Provider id: ``openai`` | ``gemini`` | …"""
        ...

    def chat(
        self,
        messages: Sequence[ChatMessage],
        params: LlmChatParams | None = None,
    ) -> ChatResult:
        ...

    def vision(
        self,
        *,
        images: Sequence[bytes | str],
        prompt: str,
        params: LlmVisionParams | None = None,
    ) -> VisionResult:
        """``images``: raw bytes (encoded as data-URL) or http(s)/data URL strings."""
        ...

    def health(self) -> bool:
        ...


@dataclass(frozen=True)
class OcrPageResult:
    """Single-page OCR output (maps to ``ocr_results`` / SDS §9.5)."""

    page: int
    text: str
    boxes: list[dict[str, Any]] = field(default_factory=list)
    confidence: float | None = None


@runtime_checkable
class OcrEnginePort(Protocol):
    """OCR engine — PaddleOCR adapter (T-4.04 / SDS ADR-011)."""

    def extract(
        self,
        image_bytes: bytes,
        *,
        lang: str | None = None,
        page: int = 1,
    ) -> OcrPageResult:
        """Extract text + boxes from image bytes."""
        ...


@dataclass(frozen=True)
class PreprocessOptions:
    """OCR preprocess flags (SDS §9.5 / PRD OCR-03)."""

    deskew: bool = False
    denoise: bool = False
    contrast: bool = False


@runtime_checkable
class ImagePreprocessPort(Protocol):
    """Image preprocess before OCR (OpenCV adapter — T-4.03)."""

    def process(
        self,
        image_bytes: bytes,
        options: PreprocessOptions | None = None,
    ) -> bytes:
        """Return processed image as PNG bytes."""
        ...


@runtime_checkable
class EmbeddingPort(Protocol):
    """Text embedding adapter (T-15.01 / B-1.1-RAG)."""

    @property
    def name(self) -> str:
        """Provider id: ``openai`` | ``hash`` | …"""
        ...

    @property
    def model(self) -> str:
        ...

    @property
    def dimensions(self) -> int:
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text (same order)."""
        ...
