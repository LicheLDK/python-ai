"""AI chat, vision, prompt routes (T-5.05–T-5.08 / SDS §9.6). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.adapters.llm_factory import get_llm_factory
from app.adapters.local_storage_adapter import get_local_storage
from app.core.cookies import client_ip
from app.core.deps import AdminUser, CurrentUser, get_db
from app.core.redis import get_redis
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ChatMessageOut,
    PromptCreate,
    PromptPage,
    PromptRead,
    PromptUpdate,
    RagCitationBlock,
    UsageBlock,
    VisionRequest,
    VisionResponse,
    to_prompt_read,
)
from app.services.ai_service import AiService
from app.services.prompt_service import PromptService

router = APIRouter(prefix="/ai", tags=["ai"])


def get_prompt_service(db: Session = Depends(get_db)) -> PromptService:
    return PromptService(db)


def get_ai_service(db: Session = Depends(get_db)) -> AiService:
    return AiService(
        db,
        storage=get_local_storage(),
        llm_factory=get_llm_factory(),
        redis_client=get_redis(),
    )


@router.get("/prompts", response_model=PromptPage)
def list_prompts(
    _user: CurrentUser,
    service: PromptService = Depends(get_prompt_service),
    name: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PromptPage:
    rows, params, total = service.list_prompts(
        page=page,
        page_size=page_size,
        name=name,
        active=active,
    )
    return PromptPage(
        items=[to_prompt_read(r) for r in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/prompts/{prompt_id}", response_model=PromptRead)
def get_prompt(
    prompt_id: uuid.UUID,
    _user: CurrentUser,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    return to_prompt_read(service.get(prompt_id))


@router.post("/prompts", response_model=PromptRead, status_code=201)
def create_prompt(
    body: PromptCreate,
    request: Request,
    admin: AdminUser,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    row = service.create(
        actor=admin,
        name=body.name,
        template=body.template,
        variables_schema=body.variables_schema,
        activate=body.activate,
        ip=client_ip(request),
    )
    return to_prompt_read(row)


@router.patch("/prompts/{prompt_id}", response_model=PromptRead)
def patch_prompt(
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    request: Request,
    admin: AdminUser,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    row = service.update(
        actor=admin,
        prompt_id=prompt_id,
        template=body.template,
        variables_schema=body.variables_schema,
        create_new_version=body.create_new_version,
        ip=client_ip(request),
    )
    return to_prompt_read(row)


@router.post("/prompts/{prompt_id}/activate", response_model=PromptRead)
def activate_prompt(
    prompt_id: uuid.UUID,
    request: Request,
    admin: AdminUser,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    row = service.activate(
        actor=admin,
        prompt_id=prompt_id,
        ip=client_ip(request),
    )
    return to_prompt_read(row)


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    user: CurrentUser,
    service: AiService = Depends(get_ai_service),
) -> ChatResponse:
    req, usage, result, citations = service.chat(
        actor=user,
        messages=[m.model_dump() for m in body.messages],
        prompt_name=body.prompt_name,
        prompt_version=body.prompt_version,
        variables=body.variables,
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        document_ids=body.document_ids,
        top_k=body.top_k,
    )
    return ChatResponse(
        request_id=req.id,
        provider=result.provider,
        model=result.model,
        message=ChatMessageOut(content=result.message.content),
        usage=UsageBlock(
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            latency_ms=usage.latency_ms,
            cost_estimate=float(usage.cost_estimate),
        ),
        citations=[
            RagCitationBlock(
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


@router.post("/chat/stream")
def chat_stream(
    body: ChatRequest,
    user: CurrentUser,
    service: AiService = Depends(get_ai_service),
) -> StreamingResponse:
    """SSE chat stream (T-5.08). Events: ``meta``, ``delta``, ``done``."""

    def _gen():
        yield from service.chat_stream(
            actor=user,
            messages=[m.model_dump() for m in body.messages],
            prompt_name=body.prompt_name,
            prompt_version=body.prompt_version,
            variables=body.variables,
            provider=body.provider,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            document_ids=body.document_ids,
            top_k=body.top_k,
        )

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.post("/vision", response_model=VisionResponse)
def vision(
    body: VisionRequest,
    user: CurrentUser,
    service: AiService = Depends(get_ai_service),
) -> VisionResponse:
    req, usage, result = service.vision(
        actor=user,
        document_id=body.document_id,
        ocr_job_id=body.ocr_job_id,
        image_document_id=body.image_document_id,
        prompt_name=body.prompt_name,
        prompt_version=body.prompt_version,
        variables=body.variables,
        instruction=body.instruction,
        provider=body.provider,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return VisionResponse(
        request_id=req.id,
        provider=result.provider,
        model=result.model,
        result=result.result,
        usage=UsageBlock(
            tokens_in=usage.tokens_in,
            tokens_out=usage.tokens_out,
            latency_ms=usage.latency_ms,
            cost_estimate=float(usage.cost_estimate),
        ),
    )
