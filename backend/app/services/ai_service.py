"""AiService — chat/vision orchestration + usage metering (T-5.06–T-5.08)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import redis
from sqlalchemy.orm import Session

from app.adapters.llm_factory import LlmFactory, get_llm_factory
from app.adapters.local_storage_adapter import get_local_storage
from app.adapters.ports import (
    ChatMessage,
    ChatResult,
    LlmChatParams,
    LlmProviderPort,
    LlmUsageStats,
    LlmVisionParams,
    StoragePort,
    VisionResult,
)
from app.core.config import Settings, settings
from app.core.constants import (
    REDIS_KEY_AI_RATE_ORG,
    REDIS_KEY_AI_RATE_USER,
)
from app.core.redis import get_redis
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import (
    ConflictError,
    NotFoundError,
    ProviderError,
    RateLimitError,
    ValidationAppError,
)
from app.models.ai import (
    AiProvider,
    AiRequest,
    AiRequestStatus,
    AiRequestType,
    AiUsage,
)
from app.models.document import Document, DocumentStatus
from app.models.ocr import OcrJobStatus
from app.models.user import User, UserRole
from app.repositories.ai_request_repository import AiRequestRepository
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.repositories.organization_repository import OrganizationRepository
from app.services.prompt_service import PromptService
from app.services.rag_service import RagCitation, RagService

_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/webp"})


class AiService:
    def __init__(
        self,
        session: Session,
        *,
        prompts: PromptService | None = None,
        requests: AiRequestRepository | None = None,
        usages: AiUsageRepository | None = None,
        documents: DocumentRepository | None = None,
        ocr_jobs: OcrJobRepository | None = None,
        ocr_results: OcrResultRepository | None = None,
        storage: StoragePort | None = None,
        llm_factory: LlmFactory | None = None,
        redis_client: redis.Redis | None = None,
        rag: RagService | None = None,
        cfg: Settings | None = None,
    ) -> None:
        self._session = session
        self._prompts = prompts or PromptService(session)
        self._requests = requests or AiRequestRepository(session)
        self._usages = usages or AiUsageRepository(session)
        self._documents = documents or DocumentRepository(session)
        self._ocr_jobs = ocr_jobs or OcrJobRepository(session)
        self._ocr_results = ocr_results or OcrResultRepository(session)
        self._storage = storage or get_local_storage()
        self._llm_factory = llm_factory or get_llm_factory()
        self._redis = redis_client if redis_client is not None else get_redis()
        self._settings = cfg or settings
        self._rag = rag or RagService(session, cfg=self._settings)

    def chat(
        self,
        *,
        actor: User,
        messages: list[dict[str, str]],
        prompt_name: str | None = None,
        prompt_version: int | None = None,
        variables: dict[str, Any] | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int | None = None,
    ) -> tuple[AiRequest, AiUsage, ChatResult, list[RagCitation]]:
        self._assert_ai_rate_limit(actor)
        prompt = self._prompts.resolve(name=prompt_name, version=prompt_version)
        chat_messages = self._build_chat_messages(
            messages=messages,
            prompt=prompt,
            variables=variables,
        )

        citations: list[RagCitation] = []
        if document_ids:
            query = self._last_user_content(messages)
            citations = self._rag.retrieve(
                actor=actor,
                query=query,
                document_ids=document_ids,
                top_k=top_k,
            )
            context = self._rag.build_context(citations)
            if context:
                chat_messages = [
                    ChatMessage(role="system", content=context),
                    *chat_messages,
                ]

        llm = self._resolve_llm(provider)
        params = LlmChatParams(model=model, temperature=temperature, max_tokens=max_tokens)
        input_ref: dict[str, Any] = {
            "messages": messages,
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
        }
        if document_ids:
            input_ref["document_ids"] = [str(d) for d in document_ids]
            input_ref["top_k"] = top_k
            input_ref["rag"] = True

        try:
            result = llm.chat(chat_messages, params)
        except (ProviderError, RateLimitError, ValidationAppError):
            self._persist_failed(
                actor=actor,
                provider_name=getattr(llm, "name", provider or self._settings.ai_primary_provider),
                model=model or "unknown",
                request_type=AiRequestType.chat,
                prompt_id=prompt.id if prompt else None,
                input_ref=input_ref,
                error="provider_or_validation_error",
            )
            raise

        self._bump_ai_rate_limit(actor)
        output_ref: dict[str, Any] = {
            "role": result.message.role,
            "content": result.message.content,
        }
        if citations:
            output_ref["citations"] = self._rag.citations_as_dicts(citations)

        req, usage = self._persist_success(
            actor=actor,
            provider_name=result.provider,
            model=result.model,
            request_type=AiRequestType.chat,
            prompt_id=prompt.id if prompt else None,
            input_ref=input_ref,
            output_ref=output_ref,
            stats=result.usage,
        )
        return req, usage, result, citations

    def chat_stream(
        self,
        *,
        actor: User,
        messages: list[dict[str, str]],
        prompt_name: str | None = None,
        prompt_version: int | None = None,
        variables: dict[str, Any] | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int | None = None,
        chunk_size: int = 24,
    ) -> Iterator[str]:
        """SSE event lines after a full provider chat (pseudo-stream; T-5.08)."""
        req, usage, result, citations = self.chat(
            actor=actor,
            messages=messages,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            variables=variables,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            document_ids=document_ids,
            top_k=top_k,
        )
        yield self._sse(
            "meta",
            {
                "request_id": str(req.id),
                "provider": result.provider,
                "model": result.model,
                "citations": self._rag.citations_as_dicts(citations),
            },
        )
        content = result.message.content or ""
        size = max(1, chunk_size)
        for i in range(0, len(content), size):
            yield self._sse("delta", {"content": content[i : i + size]})
        yield self._sse(
            "done",
            {
                "usage": {
                    "tokens_in": usage.tokens_in,
                    "tokens_out": usage.tokens_out,
                    "latency_ms": usage.latency_ms,
                    "cost_estimate": float(usage.cost_estimate),
                }
            },
        )

    def vision(
        self,
        *,
        actor: User,
        document_id: uuid.UUID | None = None,
        ocr_job_id: uuid.UUID | None = None,
        image_document_id: uuid.UUID | None = None,
        prompt_name: str | None = None,
        prompt_version: int | None = None,
        variables: dict[str, Any] | None = None,
        instruction: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[AiRequest, AiUsage, VisionResult]:
        self._assert_ai_rate_limit(actor)
        if not any((document_id, ocr_job_id, image_document_id)):
            raise ValidationAppError(
                "At least one of document_id, ocr_job_id, image_document_id is required"
            )

        prompt = self._prompts.resolve(name=prompt_name, version=prompt_version)
        prompt_text = self._build_vision_prompt(
            prompt=prompt,
            variables=variables,
            instruction=instruction,
        )
        images, ocr_text, input_ref = self._resolve_vision_inputs(
            actor=actor,
            document_id=document_id,
            ocr_job_id=ocr_job_id,
            image_document_id=image_document_id,
        )
        if ocr_text:
            prompt_text = f"{prompt_text}\n\nOCR text:\n{ocr_text}".strip()
        if not images:
            raise ValidationAppError(
                "No image bytes available for vision",
                details=input_ref,
            )

        llm = self._resolve_llm(provider)
        params = LlmVisionParams(model=model, temperature=temperature, max_tokens=max_tokens)
        try:
            result = llm.vision(images=images, prompt=prompt_text, params=params)
        except (ProviderError, RateLimitError, ValidationAppError):
            self._persist_failed(
                actor=actor,
                provider_name=getattr(llm, "name", provider or self._settings.ai_primary_provider),
                model=model or "unknown",
                request_type=AiRequestType.vision,
                prompt_id=prompt.id if prompt else None,
                input_ref=input_ref,
                error="provider_or_validation_error",
            )
            raise

        self._bump_ai_rate_limit(actor)
        req, usage = self._persist_success(
            actor=actor,
            provider_name=result.provider,
            model=result.model,
            request_type=AiRequestType.vision,
            prompt_id=prompt.id if prompt else None,
            input_ref=input_ref,
            output_ref={"result": result.result},
            stats=result.usage,
        )
        return req, usage, result

    def _build_chat_messages(
        self,
        *,
        messages: list[dict[str, str]],
        prompt,
        variables: dict[str, Any] | None,
    ) -> list[ChatMessage]:
        out: list[ChatMessage] = []
        if prompt is not None:
            rendered = self._prompts.render(prompt, variables)
            out.append(ChatMessage(role="system", content=rendered))
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role not in {"system", "user", "assistant"}:
                raise ValidationAppError("Invalid message role", details={"role": role})
            out.append(ChatMessage(role=role, content=content))
        return out

    def _build_vision_prompt(
        self,
        *,
        prompt,
        variables: dict[str, Any] | None,
        instruction: str | None,
    ) -> str:
        parts: list[str] = []
        if prompt is not None:
            parts.append(self._prompts.render(prompt, variables))
        if instruction:
            parts.append(instruction.strip())
        text = "\n\n".join(p for p in parts if p)
        if not text:
            raise ValidationAppError(
                "Vision requires prompt_name and/or instruction",
            )
        return text

    def _resolve_vision_inputs(
        self,
        *,
        actor: User,
        document_id: uuid.UUID | None,
        ocr_job_id: uuid.UUID | None,
        image_document_id: uuid.UUID | None,
    ) -> tuple[list[bytes], str | None, dict[str, Any]]:
        images: list[bytes] = []
        ocr_text: str | None = None
        input_ref: dict[str, Any] = {}

        if document_id is not None:
            doc = self._get_document_for_actor(actor, document_id)
            images.append(self._load_image_bytes(doc))
            input_ref["document_id"] = str(document_id)

        if image_document_id is not None:
            doc = self._get_document_for_actor(actor, image_document_id)
            images.append(self._load_image_bytes(doc))
            input_ref["image_document_id"] = str(image_document_id)

        if ocr_job_id is not None:
            job = self._ocr_jobs.get_by_id(ocr_job_id)
            if job is None:
                raise NotFoundError("OCR job not found")
            if job.user_id != actor.id and not self._is_admin(actor):
                raise ForbiddenError("Not allowed to access this OCR job")
            if job.status != OcrJobStatus.succeeded:
                raise ConflictError(
                    "OCR results not ready",
                    details={"status": job.status.value},
                )
            pages = self._ocr_results.list_for_job(job.id)
            ocr_text = "\n\n".join(
                (p.text or "").strip() for p in pages if (p.text or "").strip()
            )
            input_ref["ocr_job_id"] = str(ocr_job_id)
            # Prefer document image from the OCR job when no other image was given.
            if not images:
                doc = self._get_document_for_actor(actor, job.document_id)
                try:
                    images.append(self._load_image_bytes(doc))
                    input_ref["document_id"] = str(job.document_id)
                except ValidationAppError:
                    # PDF-only OCR: fall back is not possible for vision bytes.
                    raise ValidationAppError(
                        "Vision with ocr_job_id requires an image document "
                        "(or pass image_document_id / document_id)",
                        details={"ocr_job_id": str(ocr_job_id), "mime": doc.mime_type},
                    ) from None

        return images, ocr_text, input_ref

    def _get_document_for_actor(self, actor: User, document_id: uuid.UUID) -> Document:
        doc = self._documents.get_by_id(document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise NotFoundError("Document not found")
        if doc.owner_id != actor.id and not self._is_admin(actor):
            raise ForbiddenError("Not allowed to access this document")
        return doc

    def _load_image_bytes(self, doc: Document) -> bytes:
        mime = (doc.mime_type or "").split(";")[0].strip().lower()
        if mime not in _IMAGE_MIMES:
            raise ValidationAppError(
                "Vision requires an image document (jpeg/png/webp)",
                details={"mime": mime, "document_id": str(doc.id)},
            )
        try:
            return self._storage.get(doc.storage_key)
        except FileNotFoundError as exc:
            raise NotFoundError("Document storage object missing") from exc

    def _resolve_llm(self, provider: str | None) -> LlmProviderPort:
        return self._llm_factory.resolve(provider)

    def _persist_success(
        self,
        *,
        actor: User,
        provider_name: str,
        model: str,
        request_type: AiRequestType,
        prompt_id: uuid.UUID | None,
        input_ref: dict[str, Any],
        output_ref: dict[str, Any],
        stats: LlmUsageStats,
    ) -> tuple[AiRequest, AiUsage]:
        provider = self._to_provider(provider_name)
        req = self._requests.create(
            user_id=actor.id,
            provider=provider,
            model=model,
            request_type=request_type,
            status=AiRequestStatus.succeeded,
            prompt_id=prompt_id,
            input_ref=input_ref,
            output_ref=output_ref,
        )
        usage = self._usages.create(
            request_id=req.id,
            tokens_in=int(stats.tokens_in or 0),
            tokens_out=int(stats.tokens_out or 0),
            latency_ms=int(stats.latency_ms or 0),
            cost_estimate=float(stats.cost_estimate or 0.0),
        )
        self._session.commit()
        self._session.refresh(req)
        self._session.refresh(usage)
        return req, usage

    def _persist_failed(
        self,
        *,
        actor: User,
        provider_name: str,
        model: str,
        request_type: AiRequestType,
        prompt_id: uuid.UUID | None,
        input_ref: dict[str, Any],
        error: str,
    ) -> None:
        try:
            provider = self._to_provider(provider_name)
            self._requests.create(
                user_id=actor.id,
                provider=provider,
                model=model,
                request_type=request_type,
                status=AiRequestStatus.failed,
                prompt_id=prompt_id,
                input_ref=input_ref,
                error=error,
            )
            self._session.commit()
        except Exception:  # noqa: BLE001 — never mask original provider error
            self._session.rollback()

    def _assert_ai_rate_limit(self, actor: User) -> None:
        user_max = int(self._settings.ai_rate_limit_max)
        user_key = REDIS_KEY_AI_RATE_USER.format(user_id=str(actor.id))
        user_raw = self._redis.get(user_key)
        if user_raw is not None and int(user_raw) >= user_max:
            raise RateLimitError(
                "AI rate limit exceeded. Try again later.",
                details={
                    "scope": "user",
                    "limit": user_max,
                    "window_seconds": int(self._settings.ai_rate_limit_window_seconds),
                },
            )

        org = OrganizationRepository(self._session).get_by_id(actor.org_id)
        org_max = (
            int(org.ai_rate_limit_max)
            if org is not None and org.ai_rate_limit_max is not None
            else user_max
        )
        org_window = (
            int(org.ai_rate_limit_window_seconds)
            if org is not None and org.ai_rate_limit_window_seconds is not None
            else int(self._settings.ai_rate_limit_window_seconds)
        )
        org_key = REDIS_KEY_AI_RATE_ORG.format(org_id=str(actor.org_id))
        org_raw = self._redis.get(org_key)
        if org_raw is not None and int(org_raw) >= org_max:
            raise RateLimitError(
                "Organization AI rate limit exceeded. Try again later.",
                details={
                    "scope": "organization",
                    "org_id": str(actor.org_id),
                    "limit": org_max,
                    "window_seconds": org_window,
                },
            )

    def _bump_ai_rate_limit(self, actor: User) -> None:
        user_window = int(self._settings.ai_rate_limit_window_seconds)
        user_key = REDIS_KEY_AI_RATE_USER.format(user_id=str(actor.id))
        user_count = self._redis.incr(user_key)
        if user_count == 1:
            self._redis.expire(user_key, user_window)

        org = OrganizationRepository(self._session).get_by_id(actor.org_id)
        org_window = (
            int(org.ai_rate_limit_window_seconds)
            if org is not None and org.ai_rate_limit_window_seconds is not None
            else user_window
        )
        org_key = REDIS_KEY_AI_RATE_ORG.format(org_id=str(actor.org_id))
        org_count = self._redis.incr(org_key)
        if org_count == 1:
            self._redis.expire(org_key, org_window)

    @staticmethod
    def _to_provider(name: str) -> AiProvider:
        key = (name or "").strip().lower()
        try:
            return AiProvider(key)
        except ValueError:
            # FallbackLlmProvider reports primary name; unknown → openai enum default path
            return AiProvider.openai

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value

    @staticmethod
    def _last_user_content(messages: list[dict[str, str]]) -> str:
        for msg in reversed(messages):
            if (msg.get("role") or "").lower() == "user":
                return (msg.get("content") or "").strip()
        return (messages[-1].get("content") if messages else "") or ""

    @staticmethod
    def _sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
