"""PipelineService — create/list/get pipeline runs (T-6.02 / SDS §9.7)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.queue_publisher import QueuePublisher
from app.core.config import settings
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import ConflictError, NotFoundError, ValidationAppError
from app.models.document import Document, DocumentStatus
from app.models.pipeline import PipelineRun, PipelineRunStatus, initial_stages
from app.models.user import User, UserRole
from app.repositories.document_repository import DocumentRepository
from app.repositories.pipeline_run_repository import PipelineRunRepository
from app.utils.pagination import PageParams, normalize_page
from app.utils.pdf_pages import PdfError, count_pdf_pages, is_pdf_mime

_ELIGIBLE = frozenset({DocumentStatus.uploaded, DocumentStatus.ready})
_DEFAULT_PROMPT = "ocr.analyze.summary"


class PipelineService:
    def __init__(
        self,
        session: Session,
        *,
        runs: PipelineRunRepository | None = None,
        documents: DocumentRepository | None = None,
        queue: QueuePublisher | None = None,
        storage=None,
    ) -> None:
        self._session = session
        self._runs = runs or PipelineRunRepository(session)
        self._documents = documents or DocumentRepository(session)
        self._queue = queue
        self._storage = storage

    def create_run(
        self,
        *,
        actor: User,
        document_id: uuid.UUID,
        ocr_options: dict[str, Any] | None = None,
        ai: dict[str, Any] | None = None,
    ) -> PipelineRun:
        doc = self._require_document(actor=actor, document_id=document_id)
        page_count = self._resolve_page_count(doc)
        self._enforce_page_limit(page_count)
        if doc.page_count is None:
            doc.page_count = page_count
            self._session.flush()

        opts: dict[str, Any] = {
            "ocr_options": dict(ocr_options or {}),
            "ai": dict(ai or {}),
        }
        if not opts["ocr_options"].get("lang"):
            opts["ocr_options"]["lang"] = settings.ocr_lang
        opts["ocr_options"]["page_count"] = page_count
        if not opts["ai"].get("prompt_name"):
            opts["ai"]["prompt_name"] = _DEFAULT_PROMPT

        # Stash options inside stages[0] meta is awkward — keep on a synthetic field
        # via stages list: store options in a dedicated first-class way by embedding
        # into stages as run-level options under a reserved key on the row… SDS only
        # has stages JSONB. Store options as sibling key in stages wrapper? Better:
        # put options into stages list item "__options__" is hacky.
        # Use stages as list and put options in PipelineRun via... we don't have options column.
        # Common pattern: store options inside stages JSON as:
        # {"_options": {...}, "stages": [...]} — but SDS says stages is array.
        # Keep options only for worker by writing them into pending stage output_ref of preprocess
        # as input, OR add to create and worker loads from... 
        # Simplest: encode options into stages[0] before enqueue:
        stages = initial_stages()
        stages[0]["input"] = opts

        row = self._runs.create(
            user_id=actor.id,
            document_id=doc.id,
            stages=stages,
            status=PipelineRunStatus.queued,
        )
        self._session.commit()
        self._session.refresh(row)
        return row

    async def enqueue_run(self, run_id: uuid.UUID) -> None:
        if self._queue is None:
            return
        await self._queue.enqueue_pipeline_run(str(run_id))

    def list_mine(
        self,
        *,
        owner: User,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[PipelineRun], PageParams, int]:
        params = normalize_page(page, page_size)
        status_enum = self._parse_status(status) if status else None
        rows, total = self._runs.list_for_user(
            user_id=owner.id,
            page=params,
            status=status_enum,
        )
        return rows, params, total

    def get_for_actor(self, *, actor: User, run_id: uuid.UUID) -> PipelineRun:
        run = self._runs.get_by_id(run_id)
        if run is None:
            raise NotFoundError("Pipeline run not found")
        if run.user_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to access this pipeline run")
        return run

    def _require_document(self, *, actor: User, document_id: uuid.UUID) -> Document:
        doc = self._documents.get_by_id(document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise NotFoundError("Document not found")
        if doc.owner_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to pipeline this document")
        if doc.status not in _ELIGIBLE:
            raise ConflictError(
                "Document not eligible for pipeline",
                details={"status": doc.status.value},
            )
        return doc

    def _resolve_page_count(self, doc: Document) -> int:
        if doc.page_count is not None:
            return int(doc.page_count)
        if not is_pdf_mime(doc.mime_type or ""):
            return 1
        if self._storage is None:
            return 1
        try:
            raw = self._storage.get(doc.storage_key)
            return count_pdf_pages(raw)
        except (FileNotFoundError, PdfError):
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
    def _parse_status(value: str) -> PipelineRunStatus:
        try:
            return PipelineRunStatus(value)
        except ValueError as exc:
            raise ValidationAppError("Invalid pipeline status") from exc

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value
