"""OpenAI EmbeddingPort adapter (T-15.01 / B-1.1-RAG)."""

from __future__ import annotations

from typing import Sequence

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError as OpenAIRateLimitError,
)

from app.core.config import settings
from app.exceptions.domain import ProviderError, RateLimitError, ValidationAppError

PROVIDER_NAME = "openai"
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 1536


class OpenAiEmbeddingAdapter:
    """OpenAI embeddings API wrapper."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: OpenAI | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._model = model or settings.embedding_model or DEFAULT_MODEL
        self._dimensions = (
            dimensions
            if dimensions is not None
            else (settings.embedding_dimensions or DEFAULT_DIMENSIONS)
        )
        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(api_key=self._api_key or "missing-key")

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
        if not texts:
            return []
        cleaned = [t if t.strip() else " " for t in texts]
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=cleaned,
                dimensions=self._dimensions,
            )
        except AuthenticationError as exc:
            raise ProviderError("OpenAI embedding auth failed") from exc
        except OpenAIRateLimitError as exc:
            raise RateLimitError("OpenAI embedding rate limited") from exc
        except BadRequestError as exc:
            raise ValidationAppError(f"OpenAI embedding bad request: {exc}") from exc
        except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
            raise ProviderError(f"OpenAI embedding error: {exc}") from exc

        by_index = {item.index: list(item.embedding) for item in response.data}
        return [by_index[i] for i in range(len(cleaned))]
