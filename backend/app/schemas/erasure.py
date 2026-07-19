"""Erasure DTOs (T-17.03 / B-P1-ERASURE)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ErasureScope = Literal["account", "documents"]


class ErasureJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID
    scopes: list[ErasureScope] = Field(default_factory=lambda: ["account"], min_length=1)

    @field_validator("scopes")
    @classmethod
    def _unique_scopes(cls, value: list[ErasureScope]) -> list[ErasureScope]:
        seen: list[ErasureScope] = []
        for item in value:
            if item not in seen:
                seen.append(item)
        if not seen:
            raise ValueError("scopes must not be empty")
        return seen


class ErasureJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_user_id: uuid.UUID
    requested_by_id: uuid.UUID | None = None
    scopes: list[str]
    status: str
    error: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ErasureJobAccepted(BaseModel):
    job_id: uuid.UUID
    status: str
    scopes: list[str]


def to_erasure_job_read(job) -> ErasureJobRead:
    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    scopes = list(job.scopes or [])
    return ErasureJobRead(
        id=job.id,
        target_user_id=job.target_user_id,
        requested_by_id=job.requested_by_id,
        scopes=scopes,
        status=status,
        error=job.error,
        stats=dict(job.stats or {}),
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def to_erasure_job_accepted(job) -> ErasureJobAccepted:
    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    return ErasureJobAccepted(
        job_id=job.id,
        status=status,
        scopes=list(job.scopes or []),
    )
