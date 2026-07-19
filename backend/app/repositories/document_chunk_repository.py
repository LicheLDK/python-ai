"""DocumentChunkRepository — DB access only (T-15.04)."""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.rag import DocumentChunk


class DocumentChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        document_ids: Sequence[uuid.UUID] | None = None,
    ) -> list[DocumentChunk]:
        filters = [DocumentChunk.owner_id == owner_id]
        if document_ids:
            filters.append(DocumentChunk.document_id.in_(list(document_ids)))
        stmt = select(DocumentChunk).where(*filters)
        return list(self._session.scalars(stmt).all())

    def count_for_document(
        self,
        *,
        owner_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> int:
        rows = self.list_for_owner(owner_id=owner_id, document_ids=[document_id])
        return len(rows)

    def delete_for_document(
        self,
        *,
        owner_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> int:
        stmt = delete(DocumentChunk).where(
            DocumentChunk.owner_id == owner_id,
            DocumentChunk.document_id == document_id,
        )
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)

    def delete_for_ocr_job(self, *, ocr_job_id: uuid.UUID) -> int:
        stmt = delete(DocumentChunk).where(DocumentChunk.ocr_job_id == ocr_job_id)
        result = self._session.execute(stmt)
        self._session.flush()
        return int(result.rowcount or 0)

    def bulk_create(
        self,
        *,
        rows: Sequence[dict[str, Any]],
    ) -> list[DocumentChunk]:
        created: list[DocumentChunk] = []
        for payload in rows:
            row = DocumentChunk(
                id=payload.get("id") or uuid.uuid4(),
                owner_id=payload["owner_id"],
                document_id=payload["document_id"],
                ocr_job_id=payload["ocr_job_id"],
                page=payload.get("page", 1),
                chunk_index=payload["chunk_index"],
                text=payload["text"],
                embedding=payload["embedding"],
                embedding_model=payload["embedding_model"],
                meta=payload.get("meta") or {},
            )
            self._session.add(row)
            created.append(row)
        self._session.flush()
        return created
