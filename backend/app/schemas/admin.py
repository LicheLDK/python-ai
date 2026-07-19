"""Admin filter/list DTOs (T-2.03 / T-10.01 / SDS §9.9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.ocr import OcrPageResultRead
from app.schemas.user import UserRead


class AdminUserRole(str, Enum):
    user = "user"
    admin = "admin"


class AdminUserStatus(str, Enum):
    active = "active"
    inactive = "inactive"


# Admin read shape matches UserRead for v1.
UserAdminRead = UserRead


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AdminUserRole | None = None
    status: AdminUserStatus | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)


UserAdminPage = Page[UserAdminRead]


class AiUsageRead(BaseModel):
    """Joined AiUsage + AiRequest row for admin usage table."""

    id: uuid.UUID
    request_id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    model: str
    request_type: str
    status: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_estimate: float
    created_at: datetime


AiUsagePage = Page[AiUsageRead]


class OcrJobAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    error: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


OcrJobAdminPage = Page[OcrJobAdminRead]


class OcrJobAdminDetail(BaseModel):
    job: OcrJobAdminRead
    pages: list[OcrPageResultRead] = Field(default_factory=list)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    ip: str | None = None
    request_id: str | None = None
    created_at: datetime


AuditLogPage = Page[AuditLogRead]


class DashboardTopUser(BaseModel):
    user_id: uuid.UUID
    email: str | None = None
    ocr_jobs: int = 0
    ai_requests: int = 0


class DashboardProviderBreakdown(BaseModel):
    provider: str
    requests: int
    tokens_in: int = 0
    tokens_out: int = 0
    cost_estimate: float = 0.0


class AdminDashboardResponse(BaseModel):
    users_total: int
    ocr_jobs_24h: int
    ai_requests_24h: int
    error_rate_24h: float
    top_users: list[DashboardTopUser] = Field(default_factory=list)
    provider_breakdown: list[DashboardProviderBreakdown] = Field(default_factory=list)


def to_ocr_job_admin_read(job) -> OcrJobAdminRead:
    status = job.status.value if hasattr(job.status, "value") else str(job.status)
    return OcrJobAdminRead(
        id=job.id,
        document_id=job.document_id,
        user_id=job.user_id,
        status=status,
        error=job.error,
        options=dict(job.options or {}),
        attempt_count=int(job.attempt_count or 0),
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


def to_audit_log_read(row) -> AuditLogRead:
    return AuditLogRead(
        id=row.id,
        actor_id=row.actor_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        payload=dict(row.payload or {}),
        ip=row.ip,
        request_id=row.request_id,
        created_at=row.created_at,
    )
