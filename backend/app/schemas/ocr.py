"""OCR job DTOs (T-4.05 / SDS §9.5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page


class PreprocessOptionsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deskew: bool = False
    denoise: bool = False
    contrast: bool = False


class OcrJobOptionsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lang: str | None = None
    preprocess: PreprocessOptionsIn | None = None


class OcrJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    options: OcrJobOptionsIn | None = None


class OcrJobCreated(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    created_at: datetime


class OcrJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    error: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


OcrJobPage = Page[OcrJobRead]


class OcrPageResultRead(BaseModel):
    page: int
    text: str
    boxes: list[Any] = Field(default_factory=list)
    confidence: float | None = None


class OcrJobResultsRead(BaseModel):
    job_id: uuid.UUID
    pages: list[OcrPageResultRead]


def to_ocr_job_created(job) -> OcrJobCreated:
    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    return OcrJobCreated(
        id=job.id,
        document_id=job.document_id,
        status=status,
        created_at=job.created_at,
    )


def to_ocr_job_read(job) -> OcrJobRead:
    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    return OcrJobRead(
        id=job.id,
        document_id=job.document_id,
        status=status,
        error=job.error,
        options=dict(job.options or {}),
        attempt_count=int(job.attempt_count or 0),
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


def to_ocr_results_read(job_id: uuid.UUID, rows) -> OcrJobResultsRead:
    pages: list[OcrPageResultRead] = []
    for row in rows:
        conf = float(row.confidence) if row.confidence is not None else None
        pages.append(
            OcrPageResultRead(
                page=row.page,
                text=row.text,
                boxes=list(row.boxes or []),
                confidence=conf,
            )
        )
    return OcrJobResultsRead(job_id=job_id, pages=pages)
