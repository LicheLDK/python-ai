"""OCR job use cases (T-4.05 / SDS §9.5)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.queue_publisher import QueuePublisher
from app.core.config import settings
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import ConflictError, NotFoundError, ValidationAppError
from app.models.document import Document, DocumentStatus
from app.models.ocr import OcrJob, OcrJobStatus
from app.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.utils.pagination import PageParams, normalize_page
from app.utils.pdf_pages import PdfError, count_pdf_pages, is_pdf_mime

_OCR_ELIGIBLE = frozenset({DocumentStatus.uploaded, DocumentStatus.ready})


class OcrService:
    def __init__(
        self,
        session: Session,
        *,
        jobs: OcrJobRepository | None = None,
        results: OcrResultRepository | None = None,
        documents: DocumentRepository | None = None,
        queue: QueuePublisher | None = None,
        storage=None,
    ) -> None:
        self._session = session
        self._jobs = jobs or OcrJobRepository(session)
        self._results = results or OcrResultRepository(session)
        self._documents = documents or DocumentRepository(session)
        self._queue = queue
        # Lazy default storage — used only when page_count is missing for PDFs.
        self._storage = storage

    def create_job(
        self,
        *,
        actor: User,
        document_id: uuid.UUID,
        options: dict[str, Any] | None = None,
    ) -> OcrJob:
        doc = self._require_document_for_ocr(actor=actor, document_id=document_id)
        page_count = self._resolve_page_count(doc)
        self._enforce_page_limit(page_count)

        opts = dict(options or {})
        if "lang" not in opts or not opts.get("lang"):
            opts["lang"] = settings.ocr_lang
        opts["page_count"] = page_count

        # Persist discovered page_count on legacy rows that lack it.
        if doc.page_count is None:
            doc.page_count = page_count
            self._session.flush()

        row = self._jobs.create(
            document_id=doc.id,
            user_id=actor.id,
            options=opts,
            status=OcrJobStatus.queued,
        )
        self._session.commit()
        self._session.refresh(row)
        return row

    async def enqueue_job(self, job_id: uuid.UUID) -> None:
        """Enqueue ARQ ``run_ocr_job``. No-op if queue publisher is not configured."""
        if self._queue is None:
            return
        await self._queue.enqueue_ocr_job(str(job_id))

    def list_mine(
        self,
        *,
        owner: User,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[OcrJob], PageParams, int]:
        params = normalize_page(page, page_size)
        status_enum = self._parse_status(status) if status else None
        rows, total = self._jobs.list_for_user(
            user_id=owner.id,
            page=params,
            status=status_enum,
        )
        return rows, params, total

    def get_for_actor(self, *, actor: User, job_id: uuid.UUID) -> OcrJob:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("OCR job not found")
        if job.user_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to access this OCR job")
        return job

    def get_results_for_actor(
        self,
        *,
        actor: User,
        job_id: uuid.UUID,
    ) -> tuple[OcrJob, list]:
        job = self.get_for_actor(actor=actor, job_id=job_id)
        if job.status != OcrJobStatus.succeeded:
            raise ConflictError(
                "OCR results not ready",
                details={"status": job.status.value},
            )
        return job, self._results.list_for_job(job.id)

    def _require_document_for_ocr(
        self,
        *,
        actor: User,
        document_id: uuid.UUID,
    ) -> Document:
        doc = self._documents.get_by_id(document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise NotFoundError("Document not found")
        if doc.owner_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to OCR this document")
        if doc.status not in _OCR_ELIGIBLE:
            raise ConflictError(
                "Document not ready for OCR",
                details={"status": doc.status.value},
            )
        return doc

    def _resolve_page_count(self, doc: Document) -> int:
        if doc.page_count is not None and doc.page_count > 0:
            return int(doc.page_count)
        if is_pdf_mime(doc.mime_type):
            from app.adapters.local_storage_adapter import get_local_storage

            storage = self._storage or get_local_storage()
            try:
                data = storage.get(doc.storage_key)
                return count_pdf_pages(data)
            except FileNotFoundError as exc:
                raise NotFoundError("Document file missing from storage") from exc
            except PdfError as exc:
                raise ValidationAppError(
                    "Invalid PDF",
                    details={"reason": str(exc)},
                ) from exc
        return 1

    def _enforce_page_limit(self, page_count: int) -> None:
        if page_count > settings.ocr_max_pages:
            raise ValidationAppError(
                "Document exceeds OCR page limit",
                details={
                    "page_count": page_count,
                    "max_pages": settings.ocr_max_pages,
                },
            )

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value

    @staticmethod
    def _parse_status(value: str) -> OcrJobStatus:
        try:
            return OcrJobStatus(value)
        except ValueError as exc:
            raise ValidationAppError("Invalid OCR job status") from exc
