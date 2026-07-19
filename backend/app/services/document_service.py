"""Document use cases (T-3.03 / SDS §9.4)."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import LocalStorageAdapter, get_local_storage
from app.adapters.ports import StoragePort
from app.core.config import settings
from app.core.constants import ALLOWED_DOCUMENT_MIME_TYPES
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import (
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationAppError,
)
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository
from app.utils.pagination import PageParams, normalize_page
from app.utils.pdf_pages import PdfError, count_pdf_pages, is_pdf_mime

_EXT_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


class DocumentService:
    def __init__(
        self,
        session: Session,
        *,
        documents: DocumentRepository | None = None,
        storage: StoragePort | None = None,
    ) -> None:
        self._session = session
        self._documents = documents or DocumentRepository(session)
        self._storage = storage or get_local_storage()

    def upload(
        self,
        *,
        owner: User,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> Document:
        mime = self._resolve_mime(filename=filename, content_type=content_type)
        if mime not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise UnsupportedMediaTypeError(
                f"Unsupported media type: {mime}",
                details={"allowed": sorted(ALLOWED_DOCUMENT_MIME_TYPES)},
            )
        if len(data) > settings.upload_max_bytes:
            raise PayloadTooLargeError(
                "File exceeds upload size limit",
                details={
                    "size_bytes": len(data),
                    "max_bytes": settings.upload_max_bytes,
                },
            )
        if len(data) == 0:
            raise ValidationAppError("Empty file")

        document_id = uuid.uuid4()
        storage_key = self._storage.build_document_key(document_id)
        checksum = hashlib.sha256(data).hexdigest()
        safe_name = PurePosixPath(filename.replace("\\", "/")).name or "upload.bin"
        page_count = self._detect_page_count(mime=mime, data=data)

        self._storage.put(storage_key, data)
        try:
            row = self._documents.create(
                document_id=document_id,
                owner_id=owner.id,
                filename=safe_name[:512],
                mime_type=mime,
                size_bytes=len(data),
                checksum_sha256=checksum,
                storage_key=storage_key,
                page_count=page_count,
                status=DocumentStatus.uploaded,
            )
            self._session.commit()
            self._session.refresh(row)
            return row
        except Exception:
            # Best-effort cleanup if DB write fails after put.
            try:
                self._storage.delete(storage_key)
            except Exception:  # noqa: BLE001
                pass
            self._session.rollback()
            raise

    def list_mine(
        self,
        *,
        owner: User,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Document], PageParams, int]:
        params = normalize_page(page, page_size)
        status_enum = self._parse_status(status) if status else None
        rows, total = self._documents.list_for_owner(
            owner_id=owner.id,
            page=params,
            status=status_enum,
        )
        return rows, params, total

    def get_for_actor(self, *, actor: User, document_id: uuid.UUID) -> Document:
        doc = self._documents.get_by_id(document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise NotFoundError("Document not found")
        if doc.owner_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to access this document")
        return doc

    def soft_delete(self, *, actor: User, document_id: uuid.UUID) -> None:
        doc = self._documents.get_by_id(document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise NotFoundError("Document not found")
        if doc.owner_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to delete this document")
        self._documents.soft_delete(doc)
        self._session.commit()

    @staticmethod
    def _detect_page_count(*, mime: str, data: bytes) -> int:
        if is_pdf_mime(mime):
            try:
                return count_pdf_pages(data)
            except PdfError as exc:
                raise ValidationAppError(
                    "Invalid PDF",
                    details={"reason": str(exc)},
                ) from exc
        return 1

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value

    @staticmethod
    def _parse_status(value: str) -> DocumentStatus:
        try:
            return DocumentStatus(value)
        except ValueError as exc:
            raise ValidationAppError("Invalid document status") from exc

    @staticmethod
    def _resolve_mime(*, filename: str, content_type: str | None) -> str:
        if content_type:
            # Strip charset etc.
            mime = content_type.split(";")[0].strip().lower()
            if mime and mime != "application/octet-stream":
                return mime
        ext = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        return _EXT_MIME.get(ext, content_type or "application/octet-stream")
