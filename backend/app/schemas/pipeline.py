"""Pipeline DTOs (T-6.02 / SDS §9.7)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page


class PipelineAiOptionsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_name: str = Field(min_length=1, max_length=120)
    provider: str | None = None
    model: str | None = None


class PipelineRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    ocr_options: dict[str, Any] | None = None
    ai: PipelineAiOptionsIn | None = None


class PipelineRunCreated(BaseModel):
    id: uuid.UUID
    status: str
    document_id: uuid.UUID
    created_at: datetime


class PipelineStageRead(BaseModel):
    name: str
    status: str
    error: str | None = None
    output_ref: dict[str, Any] | None = None


class PipelineRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    stages: list[PipelineStageRead] = Field(default_factory=list)
    ocr_job_id: uuid.UUID | None = None
    ai_request_id: uuid.UUID | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


PipelineRunPage = Page[PipelineRunRead]


def to_pipeline_run_created(run) -> PipelineRunCreated:
    status = run.status.value if hasattr(run.status, "value") else str(run.status)
    return PipelineRunCreated(
        id=run.id,
        status=status,
        document_id=run.document_id,
        created_at=run.created_at,
    )


def to_pipeline_run_read(run) -> PipelineRunRead:
    status = run.status.value if hasattr(run.status, "value") else str(run.status)
    stages_raw = run.stages or []
    stages: list[PipelineStageRead] = []
    for item in stages_raw:
        if not isinstance(item, dict):
            continue
        stages.append(
            PipelineStageRead(
                name=str(item.get("name", "")),
                status=str(item.get("status", "pending")),
                error=item.get("error"),
                output_ref=item.get("output_ref"),
            )
        )
    return PipelineRunRead(
        id=run.id,
        document_id=run.document_id,
        status=status,
        stages=stages,
        ocr_job_id=run.ocr_job_id,
        ai_request_id=run.ai_request_id,
        error=run.error,
        created_at=run.created_at,
        finished_at=run.finished_at,
    )
