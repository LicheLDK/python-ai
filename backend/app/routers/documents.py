"""Document routes (T-3.03 / SDS §9.4). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import get_local_storage
from app.core.deps import CurrentUser, get_db
from app.schemas.document import DocumentPage, DocumentRead, to_document_read
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(db, storage=get_local_storage())


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
    file: UploadFile = File(...),
) -> DocumentRead:
    data = await file.read()
    doc = service.upload(
        owner=user,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        data=data,
    )
    return to_document_read(doc)


@router.get("", response_model=DocumentPage)
def list_documents(
    user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DocumentPage:
    rows, params, total = service.list_mine(
        owner=user,
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return DocumentPage(
        items=[to_document_read(d) for d in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    return to_document_read(service.get_for_actor(actor=user, document_id=document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    service: DocumentService = Depends(get_document_service),
) -> None:
    service.soft_delete(actor=user, document_id=document_id)
