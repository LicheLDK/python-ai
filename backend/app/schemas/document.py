"""Document DTOs (T-3.03 / SDS §9.4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Page


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    status: str
    created_at: datetime
    page_count: int | None = None


DocumentPage = Page[DocumentRead]


def to_document_read(doc) -> DocumentRead:
    status = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    return DocumentRead(
        id=doc.id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        checksum_sha256=doc.checksum_sha256,
        status=status,
        created_at=doc.created_at,
        page_count=doc.page_count,
    )
