"""RagService — index OCR text, retrieve chunks, build citations (T-15.05 / T-15.06)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy.orm import Session

from app.adapters.embedding_factory import get_embedding
from app.adapters.ports import EmbeddingPort
from app.core.config import Settings, settings
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import NotFoundError, ValidationAppError
from app.models.ocr import OcrJobStatus
from app.models.rag import DocumentChunk
from app.models.user import User, UserRole
from app.repositories.document_chunk_repository import DocumentChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.utils.rag_chunking import chunk_text, cosine_similarity


@dataclass(frozen=True)
class RagCitation:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    ocr_job_id: uuid.UUID
    page: int
    chunk_index: int
    score: float
    snippet: str


@dataclass(frozen=True)
class RagIndexResult:
    document_id: uuid.UUID
    ocr_job_id: uuid.UUID
    chunk_count: int
    embedding_provider: str
    embedding_model: str


class RagService:
    def __init__(
        self,
        session: Session,
        *,
        chunks: DocumentChunkRepository | None = None,
        documents: DocumentRepository | None = None,
        ocr_jobs: OcrJobRepository | None = None,
        ocr_results: OcrResultRepository | None = None,
        embedding: EmbeddingPort | None = None,
        cfg: Settings | None = None,
    ) -> None:
        self._session = session
        self._chunks = chunks or DocumentChunkRepository(session)
        self._documents = documents or DocumentRepository(session)
        self._ocr_jobs = ocr_jobs or OcrJobRepository(session)
        self._ocr_results = ocr_results or OcrResultRepository(session)
        self._embedding = embedding or get_embedding()
        self._settings = cfg or settings

    def index(
        self,
        *,
        actor: User,
        document_id: uuid.UUID | None = None,
        ocr_job_id: uuid.UUID | None = None,
    ) -> RagIndexResult:
        if not document_id and not ocr_job_id:
            raise ValidationAppError("document_id or ocr_job_id is required")

        job = None
        if ocr_job_id is not None:
            job = self._ocr_jobs.get_by_id(ocr_job_id)
            if job is None:
                raise NotFoundError("OCR job not found")
            if job.status != OcrJobStatus.succeeded:
                raise ValidationAppError(
                    "OCR job must be succeeded before indexing",
                    details={"status": job.status.value},
                )
            document_id = job.document_id
        else:
            assert document_id is not None
            job = self._ocr_jobs.get_latest_succeeded_for_document(document_id)
            if job is None:
                raise ValidationAppError(
                    "No succeeded OCR job for document",
                    details={"document_id": str(document_id)},
                )

        doc = self._documents.get_by_id(document_id)
        if doc is None:
            raise NotFoundError("Document not found")
        self._assert_doc_access(actor, doc.owner_id)
        self._assert_job_access(actor, job.user_id)

        pages = self._ocr_results.list_for_job(job.id)
        if not pages:
            raise ValidationAppError("OCR job has no results to index")

        prepared: list[tuple[int, str]] = []
        chunk_size = self._settings.rag_chunk_size
        overlap = self._settings.rag_chunk_overlap
        for page in pages:
            for piece in chunk_text(page.text, chunk_size=chunk_size, overlap=overlap):
                prepared.append((page.page, piece))

        if not prepared:
            raise ValidationAppError("No non-empty text chunks after splitting")

        vectors = self._embedding.embed([t for _, t in prepared])
        if len(vectors) != len(prepared):
            raise ValidationAppError("Embedding count mismatch")

        self._chunks.delete_for_document(owner_id=doc.owner_id, document_id=doc.id)
        rows = [
            {
                "owner_id": doc.owner_id,
                "document_id": doc.id,
                "ocr_job_id": job.id,
                "page": page_no,
                "chunk_index": idx,
                "text": text,
                "embedding": vectors[idx],
                "embedding_model": self._embedding.model,
                "meta": {
                    "provider": self._embedding.name,
                    "dimensions": len(vectors[idx]),
                },
            }
            for idx, (page_no, text) in enumerate(prepared)
        ]
        self._chunks.bulk_create(rows=rows)
        self._session.commit()

        return RagIndexResult(
            document_id=doc.id,
            ocr_job_id=job.id,
            chunk_count=len(rows),
            embedding_provider=self._embedding.name,
            embedding_model=self._embedding.model,
        )

    def retrieve(
        self,
        *,
        actor: User,
        query: str,
        document_ids: Sequence[uuid.UUID],
        top_k: int | None = None,
    ) -> list[RagCitation]:
        q = (query or "").strip()
        if not q:
            raise ValidationAppError("query must not be empty")
        if not document_ids:
            raise ValidationAppError("document_ids is required")

        for doc_id in document_ids:
            doc = self._documents.get_by_id(doc_id)
            if doc is None:
                raise NotFoundError("Document not found", details={"document_id": str(doc_id)})
            self._assert_doc_access(actor, doc.owner_id)

        k = top_k if top_k is not None else self._settings.rag_top_k
        k = max(1, min(int(k), 20))

        candidates: list[DocumentChunk] = []
        seen: set[uuid.UUID] = set()
        for doc_id in document_ids:
            doc = self._documents.get_by_id(doc_id)
            if doc is None:
                continue
            for row in self._chunks.list_for_owner(
                owner_id=doc.owner_id,
                document_ids=[doc_id],
            ):
                if row.id not in seen:
                    seen.add(row.id)
                    candidates.append(row)

        if not candidates:
            return []

        query_vec = self._embedding.embed([q])[0]
        scored: list[tuple[float, DocumentChunk]] = []
        for row in candidates:
            emb = row.embedding if isinstance(row.embedding, list) else []
            score = cosine_similarity(query_vec, [float(x) for x in emb])
            scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)

        citations: list[RagCitation] = []
        for score, row in scored[:k]:
            snippet = row.text if len(row.text) <= 400 else f"{row.text[:397]}..."
            citations.append(
                RagCitation(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    ocr_job_id=row.ocr_job_id,
                    page=row.page,
                    chunk_index=row.chunk_index,
                    score=round(float(score), 6),
                    snippet=snippet,
                )
            )
        return citations

    def build_context(self, citations: Sequence[RagCitation]) -> str:
        if not citations:
            return ""
        blocks: list[str] = []
        for i, c in enumerate(citations, start=1):
            blocks.append(
                f"[{i}] document={c.document_id} page={c.page} score={c.score:.4f}\n{c.snippet}"
            )
        return (
            "Use the following retrieved document excerpts. "
            "Cite sources as [n] when relevant.\n\n" + "\n\n".join(blocks)
        )

    def citations_as_dicts(self, citations: Sequence[RagCitation]) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "ocr_job_id": str(c.ocr_job_id),
                "page": c.page,
                "chunk_index": c.chunk_index,
                "score": c.score,
                "snippet": c.snippet,
            }
            for c in citations
        ]

    def _assert_doc_access(self, actor: User, owner_id: uuid.UUID) -> None:
        if self._is_admin(actor):
            return
        if actor.id != owner_id:
            raise ForbiddenError("Not allowed to access this document")

    def _assert_job_access(self, actor: User, user_id: uuid.UUID) -> None:
        if self._is_admin(actor):
            return
        if actor.id != user_id:
            raise ForbiddenError("Not allowed to access this OCR job")

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value
