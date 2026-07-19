"""DocumentRepository — DB access only (T-3.03 / SDS §10.8)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.utils.pagination import PageParams


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return self._session.get(Document, document_id)

    def create(
        self,
        *,
        owner_id: uuid.UUID,
        filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        storage_key: str,
        page_count: int | None = None,
        status: DocumentStatus = DocumentStatus.uploaded,
        document_id: uuid.UUID | None = None,
    ) -> Document:
        row = Document(
            id=document_id or uuid.uuid4(),
            owner_id=owner_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            storage_key=storage_key,
            page_count=page_count,
            status=status,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        page: PageParams,
        status: DocumentStatus | None = None,
        include_deleted: bool = False,
    ) -> tuple[list[Document], int]:
        filters = [Document.owner_id == owner_id]
        if status is not None:
            filters.append(Document.status == status)
        elif not include_deleted:
            filters.append(Document.status != DocumentStatus.deleted)

        count_stmt = select(func.count()).select_from(Document).where(*filters)
        list_stmt = (
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
            .offset(page.offset)
            .limit(page.limit)
        )
        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(self._session.scalars(list_stmt).all())
        return rows, total

    def soft_delete(self, document: Document) -> Document:
        document.status = DocumentStatus.deleted
        self._session.flush()
        return document

    def list_all_for_owner(self, owner_id: uuid.UUID) -> list[Document]:
        """All documents for owner including soft-deleted (erasure)."""
        stmt = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def hard_delete(self, document: Document) -> None:
        self._session.delete(document)
        self._session.flush()
