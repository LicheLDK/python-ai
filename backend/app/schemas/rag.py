"""RAG index / search DTOs (T-15.05 / T-15.06)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RagIndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID | None = None
    ocr_job_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _require_one(self) -> RagIndexRequest:
        if self.document_id is None and self.ocr_job_id is None:
            raise ValueError("document_id or ocr_job_id is required")
        return self


class RagIndexResponse(BaseModel):
    document_id: uuid.UUID
    ocr_job_id: uuid.UUID
    chunk_count: int
    embedding_provider: str
    embedding_model: str


class RagSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    document_ids: list[uuid.UUID] = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class RagCitationOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    ocr_job_id: uuid.UUID
    page: int
    chunk_index: int
    score: float
    snippet: str


class RagSearchResponse(BaseModel):
    query: str
    citations: list[RagCitationOut]
