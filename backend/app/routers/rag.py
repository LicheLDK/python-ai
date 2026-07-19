"""RAG index / search routes (T-15.05 / T-15.06). Controller only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.embedding_factory import get_embedding
from app.core.deps import CurrentUser, get_db
from app.schemas.rag import (
    RagCitationOut,
    RagIndexRequest,
    RagIndexResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


def get_rag_service(db: Session = Depends(get_db)) -> RagService:
    return RagService(db, embedding=get_embedding())


@router.post("/index", response_model=RagIndexResponse)
def index_document(
    body: RagIndexRequest,
    user: CurrentUser,
    service: RagService = Depends(get_rag_service),
) -> RagIndexResponse:
    result = service.index(
        actor=user,
        document_id=body.document_id,
        ocr_job_id=body.ocr_job_id,
    )
    return RagIndexResponse(
        document_id=result.document_id,
        ocr_job_id=result.ocr_job_id,
        chunk_count=result.chunk_count,
        embedding_provider=result.embedding_provider,
        embedding_model=result.embedding_model,
    )


@router.post("/search", response_model=RagSearchResponse)
def search_chunks(
    body: RagSearchRequest,
    user: CurrentUser,
    service: RagService = Depends(get_rag_service),
) -> RagSearchResponse:
    citations = service.retrieve(
        actor=user,
        query=body.query,
        document_ids=body.document_ids,
        top_k=body.top_k,
    )
    return RagSearchResponse(
        query=body.query,
        citations=[
            RagCitationOut(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                ocr_job_id=c.ocr_job_id,
                page=c.page,
                chunk_index=c.chunk_index,
                score=c.score,
                snippet=c.snippet,
            )
            for c in citations
        ],
    )
