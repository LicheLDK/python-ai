"""Deterministic hash EmbeddingPort for tests / offline RAG (T-15.01)."""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

PROVIDER_NAME = "hash"
DEFAULT_MODEL = "hash-v1"
DEFAULT_DIMENSIONS = 64


class HashEmbeddingAdapter:
    """Pseudo-embeddings from token hashes — stable, no network."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS,
    ) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be >= 8")
        self._model = model
        self._dimensions = dimensions

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dimensions
        tokens = text.lower().split() or [" "]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(0, min(len(digest), self._dimensions)):
                # Map byte to [-1, 1]
                vec[i] += (digest[i] / 127.5) - 1.0
            # Spread remaining dims with rotated hash
            extra = hashlib.sha256(digest).digest()
            for i in range(len(digest), self._dimensions):
                vec[i] += (extra[i % len(extra)] / 127.5) - 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
