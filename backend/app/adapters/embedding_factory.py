"""Embedding backend factory (T-15.02)."""

from __future__ import annotations

from functools import lru_cache

from app.adapters.hash_embedding_adapter import HashEmbeddingAdapter
from app.adapters.openai_embedding_adapter import OpenAiEmbeddingAdapter
from app.adapters.ports import EmbeddingPort
from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding() -> EmbeddingPort:
    """Process-wide EmbeddingPort selected by ``EMBEDDING_PROVIDER``."""
    provider = (settings.embedding_provider or "openai").strip().lower()
    if provider == "openai":
        return OpenAiEmbeddingAdapter()
    if provider == "hash":
        return HashEmbeddingAdapter(
            dimensions=settings.embedding_dimensions or 64,
        )
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}; "
        "use 'openai' or 'hash'"
    )


def reset_embedding_cache() -> None:
    """Clear factory cache (tests)."""
    get_embedding.cache_clear()
