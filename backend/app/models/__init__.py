"""ORM models package.

Import domain models here so Base.metadata is complete for Alembic.
"""

from app.models.ai import (
    AiPrompt,
    AiProvider,
    AiRequest,
    AiRequestStatus,
    AiRequestType,
    AiUsage,
)
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.document import Document, DocumentStatus
from app.models.erasure import ErasureJob, ErasureJobStatus
from app.models.ocr import OcrJob, OcrJobStatus, OcrResult
from app.models.organization import Organization, OrganizationStatus
from app.models.permission import Permission, RolePermission
from app.models.pipeline import PipelineRun, PipelineRunStatus
from app.models.rag import DocumentChunk
from app.models.refresh_token import RefreshToken
from app.models.stats import StatDaily
from app.models.user import User, UserRole, UserStatus

__all__ = [
    "AiPrompt",
    "AiProvider",
    "AiRequest",
    "AiRequestStatus",
    "AiRequestType",
    "AiUsage",
    "AuditLog",
    "Base",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "ErasureJob",
    "ErasureJobStatus",
    "OcrJob",
    "OcrJobStatus",
    "OcrResult",
    "Organization",
    "OrganizationStatus",
    "Permission",
    "PipelineRun",
    "PipelineRunStatus",
    "RefreshToken",
    "RolePermission",
    "StatDaily",
    "User",
    "UserRole",
    "UserStatus",
]
