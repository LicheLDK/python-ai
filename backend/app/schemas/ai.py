"""AI chat / vision / prompt DTOs (T-5.05–T-5.08 / SDS §9.6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Page


class PromptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: int
    template: str
    variables_schema: dict[str, Any] = Field(default_factory=dict)
    active: bool
    created_at: datetime


PromptPage = Page[PromptRead]


class PromptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    template: str = Field(min_length=1)
    variables_schema: dict[str, Any] | None = None
    activate: bool = False


class PromptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: str | None = Field(default=None, min_length=1)
    variables_schema: dict[str, Any] | None = None
    create_new_version: bool = False


class ChatMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessageIn] = Field(min_length=1)
    prompt_name: str | None = None
    prompt_version: int | None = Field(default=None, ge=1)
    variables: dict[str, Any] | None = None
    provider: Literal["openai", "gemini", "ollama"] | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    # RAG (T-15.06): when set, retrieve chunks and inject as system context
    document_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class UsageBlock(BaseModel):
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_estimate: float


class ChatMessageOut(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class RagCitationBlock(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    ocr_job_id: uuid.UUID
    page: int
    chunk_index: int
    score: float
    snippet: str


class ChatResponse(BaseModel):
    request_id: uuid.UUID
    provider: str
    model: str
    message: ChatMessageOut
    usage: UsageBlock
    citations: list[RagCitationBlock] = Field(default_factory=list)


class VisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID | None = None
    ocr_job_id: uuid.UUID | None = None
    image_document_id: uuid.UUID | None = None
    prompt_name: str | None = None
    prompt_version: int | None = Field(default=None, ge=1)
    variables: dict[str, Any] | None = None
    instruction: str | None = None
    provider: Literal["openai", "gemini", "ollama"] | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _require_source(self) -> VisionRequest:
        if not any((self.document_id, self.ocr_job_id, self.image_document_id)):
            raise ValueError(
                "At least one of document_id, ocr_job_id, image_document_id is required"
            )
        return self


class VisionResponse(BaseModel):
    request_id: uuid.UUID
    provider: str
    model: str
    result: Any
    usage: UsageBlock


def to_prompt_read(row) -> PromptRead:
    return PromptRead.model_validate(row)


def to_usage_block(*, tokens_in: int, tokens_out: int, latency_ms: int, cost_estimate: float) -> UsageBlock:
    return UsageBlock(
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        cost_estimate=float(cost_estimate),
    )
