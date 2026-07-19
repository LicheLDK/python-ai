"""Pipeline async job handler (T-6.02 / T-6.03 / SDS §8.5).

Stages: preprocess → ocr → ai_analyze → persist.
On failure, prior stages keep succeeded + output_ref (partial reporting).
"""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.adapters.llm_factory import LlmFactory, get_llm_factory
from app.adapters.local_storage_adapter import get_local_storage
from app.adapters.ports import (
    ChatMessage,
    LlmChatParams,
    LlmProviderPort,
    StoragePort,
)
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ai import AiProvider, AiRequestStatus, AiRequestType
from app.models.document import DocumentStatus
from app.models.ocr import OcrJobStatus
from app.models.pipeline import PipelineRun, PipelineRunStatus, STAGE_NAMES
from app.repositories.ai_request_repository import AiRequestRepository
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.repositories.pipeline_run_repository import PipelineRunRepository
from app.services.prompt_service import PromptService
from app.utils.pdf_pages import resolve_page_images
from app.workers.ocr_jobs import OcrJobRunner

logger = logging.getLogger(__name__)

_PIPELINE_JOB_NAME = "run_pipeline"


class PipelineStageError(Exception):
    """Raised when a stage fails; carries stage name for partial reporting."""

    def __init__(
        self,
        stage: str,
        message: str,
        *,
        output_ref: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.output_ref = output_ref


def _clone_stages(stages: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return copy.deepcopy(list(stages or []))


def _set_stage(
    stages: list[dict[str, Any]],
    name: str,
    *,
    status: str,
    error: str | None = None,
    output_ref: dict[str, Any] | None = None,
    clear_input: bool = False,
) -> list[dict[str, Any]]:
    found = False
    for item in stages:
        if item.get("name") != name:
            continue
        found = True
        item["status"] = status
        if error is not None:
            item["error"] = error
        elif "error" in item and status == "succeeded":
            item.pop("error", None)
        if output_ref is not None:
            item["output_ref"] = output_ref
        if clear_input:
            item.pop("input", None)
        break
    if not found:
        entry: dict[str, Any] = {"name": name, "status": status}
        if error is not None:
            entry["error"] = error
        if output_ref is not None:
            entry["output_ref"] = output_ref
        stages.append(entry)
    return stages


def _extract_options(stages: list[dict[str, Any]]) -> dict[str, Any]:
    for item in stages:
        if item.get("name") == "preprocess" and isinstance(item.get("input"), dict):
            return dict(item["input"])
    return {"ocr_options": {}, "ai": {}}


class PipelineRunner:
    """Synchronous pipeline execution (ARQ worker + tests)."""

    def __init__(
        self,
        session: Session,
        *,
        storage: StoragePort | None = None,
        llm_factory: LlmFactory | None = None,
        ocr_runner: OcrJobRunner | None = None,
        max_pages: int | None = None,
    ) -> None:
        self._session = session
        self._runs = PipelineRunRepository(session)
        self._documents = DocumentRepository(session)
        self._ocr_jobs = OcrJobRepository(session)
        self._ocr_results = OcrResultRepository(session)
        self._ai_requests = AiRequestRepository(session)
        self._ai_usages = AiUsageRepository(session)
        self._prompts = PromptService(session)
        self._storage = storage or get_local_storage()
        self._llm_factory = llm_factory or get_llm_factory()
        self._ocr_runner = ocr_runner
        self._max_pages = max_pages if max_pages is not None else settings.ocr_max_pages

    def run(self, run_id: uuid.UUID) -> dict[str, Any]:
        run = self._runs.get_by_id(run_id)
        if run is None:
            logger.warning("pipeline run missing: %s", run_id)
            return {"status": "missing", "run_id": str(run_id)}

        if run.status in (
            PipelineRunStatus.succeeded,
            PipelineRunStatus.cancelled,
        ):
            return {"status": run.status.value, "run_id": str(run_id)}

        stages = _clone_stages(run.stages)
        options = _extract_options(stages)
        self._runs.mark_running(run)
        self._session.commit()

        try:
            stages = self._stage_preprocess(run, stages)
            self._persist_progress(run, stages)

            ocr_job_id, stages = self._stage_ocr(run, stages, options)
            self._persist_progress(run, stages, ocr_job_id=ocr_job_id)

            ai_request_id, stages = self._stage_ai(run, stages, options, ocr_job_id)
            self._persist_progress(run, stages, ai_request_id=ai_request_id)

            stages = self._stage_persist(run, stages, ocr_job_id, ai_request_id)
            self._assign_stages(run, stages)
            self._runs.mark_succeeded(
                run,
                finished_at=datetime.now(UTC),
                stages=run.stages,
            )
            self._session.commit()
            return {
                "status": PipelineRunStatus.succeeded.value,
                "run_id": str(run_id),
                "ocr_job_id": str(ocr_job_id) if ocr_job_id else None,
                "ai_request_id": str(ai_request_id) if ai_request_id else None,
            }
        except PipelineStageError as exc:
            logger.warning(
                "pipeline stage failed run=%s stage=%s: %s",
                run_id,
                exc.stage,
                exc.message,
            )
            self._session.rollback()
            run = self._runs.get_by_id(run_id)
            if run is None:
                return {"status": "missing", "run_id": str(run_id)}
            # Rebuild from last committed stages so prior succeeded output_ref survives.
            stages = _clone_stages(run.stages)
            stages = _set_stage(
                stages,
                exc.stage,
                status="failed",
                error=exc.message,
                output_ref=exc.output_ref,
                clear_input=True,
            )
            self._assign_stages(run, stages)
            self._runs.mark_failed(
                run,
                finished_at=datetime.now(UTC),
                stages=run.stages,
                error=f"{exc.stage}: {exc.message}",
            )
            self._session.commit()
            return {
                "status": PipelineRunStatus.failed.value,
                "run_id": str(run_id),
                "failed_stage": exc.stage,
                "error": exc.message,
            }
        except Exception as exc:  # noqa: BLE001
            err = str(exc) or exc.__class__.__name__
            logger.exception("pipeline unexpected failure run=%s", run_id)
            self._session.rollback()
            run = self._runs.get_by_id(run_id)
            if run is None:
                return {"status": "missing", "run_id": str(run_id), "error": err}
            stages = _clone_stages(run.stages)
            stages = _set_stage(stages, "persist", status="failed", error=err)
            self._assign_stages(run, stages)
            self._runs.mark_failed(
                run,
                finished_at=datetime.now(UTC),
                stages=run.stages,
                error=err,
            )
            self._session.commit()
            return {
                "status": PipelineRunStatus.failed.value,
                "run_id": str(run_id),
                "error": err,
            }

    def _assign_stages(self, run: PipelineRun, stages: list[dict[str, Any]]) -> None:
        run.stages = copy.deepcopy(stages)
        flag_modified(run, "stages")

    def _persist_progress(
        self,
        run: PipelineRun,
        stages: list[dict[str, Any]],
        *,
        ocr_job_id: uuid.UUID | None = None,
        ai_request_id: uuid.UUID | None = None,
    ) -> None:
        self._assign_stages(run, stages)
        self._runs.update_stages(
            run,
            run.stages,
            ocr_job_id=ocr_job_id,
            ai_request_id=ai_request_id,
        )
        self._session.commit()

    def _stage_preprocess(
        self,
        run: PipelineRun,
        stages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        stages = _set_stage(stages, "preprocess", status="running", clear_input=False)
        doc = self._documents.get_by_id(run.document_id)
        if doc is None or doc.status == DocumentStatus.deleted:
            raise PipelineStageError("preprocess", "Document not found")
        try:
            raw = self._storage.get(doc.storage_key)
        except FileNotFoundError as exc:
            raise PipelineStageError("preprocess", "Document storage object missing") from exc

        total_pages, page_images = resolve_page_images(
            raw,
            mime_type=doc.mime_type,
            max_pages=self._max_pages,
        )
        if total_pages > self._max_pages:
            raise PipelineStageError(
                "preprocess",
                f"Document exceeds page limit "
                f"(page_count={total_pages}, max_pages={self._max_pages})",
            )
        return _set_stage(
            stages,
            "preprocess",
            status="succeeded",
            output_ref={
                "document_id": str(doc.id),
                "mime_type": doc.mime_type,
                "page_count": total_pages,
                "pages_loaded": len(page_images),
            },
            clear_input=True,
        )

    def _stage_ocr(
        self,
        run: PipelineRun,
        stages: list[dict[str, Any]],
        options: dict[str, Any],
    ) -> tuple[uuid.UUID, list[dict[str, Any]]]:
        stages = _set_stage(stages, "ocr", status="running")
        ocr_opts = dict(options.get("ocr_options") or {})
        job = self._ocr_jobs.create(
            document_id=run.document_id,
            user_id=run.user_id,
            options=ocr_opts,
            status=OcrJobStatus.queued,
        )
        run.ocr_job_id = job.id
        self._session.commit()

        runner = self._ocr_runner or OcrJobRunner(
            self._session,
            storage=self._storage,
            max_attempts=1,  # pipeline fails the stage instead of ARQ retry loop
        )
        outcome = runner.run(job.id)
        if outcome.status != OcrJobStatus.succeeded.value:
            raise PipelineStageError(
                "ocr",
                outcome.error or f"OCR ended with status={outcome.status}",
                output_ref={"ocr_job_id": str(job.id)},
            )
        stages = _set_stage(
            stages,
            "ocr",
            status="succeeded",
            output_ref={"ocr_job_id": str(job.id)},
        )
        return job.id, stages

    def _stage_ai(
        self,
        run: PipelineRun,
        stages: list[dict[str, Any]],
        options: dict[str, Any],
        ocr_job_id: uuid.UUID,
    ) -> tuple[uuid.UUID, list[dict[str, Any]]]:
        stages = _set_stage(stages, "ai_analyze", status="running")
        ai_opts = dict(options.get("ai") or {})
        prompt_name = (ai_opts.get("prompt_name") or "ocr.analyze.summary").strip()
        pages = self._ocr_results.list_for_job(ocr_job_id)
        ocr_text = "\n\n".join(
            (p.text or "").strip() for p in pages if (p.text or "").strip()
        )
        if not ocr_text:
            ocr_text = "(empty OCR text)"

        try:
            prompt = self._prompts.resolve(name=prompt_name, version=None)
            rendered = self._prompts.render(prompt, {"ocr_text": ocr_text})
        except Exception as exc:  # noqa: BLE001 — map to stage failure
            raise PipelineStageError("ai_analyze", str(exc)) from exc

        llm: LlmProviderPort = self._llm_factory.resolve(ai_opts.get("provider"))
        params = LlmChatParams(model=ai_opts.get("model"))
        try:
            result = llm.chat(
                [ChatMessage(role="user", content=rendered)],
                params,
            )
        except Exception as exc:  # noqa: BLE001
            raise PipelineStageError("ai_analyze", str(exc)) from exc

        try:
            provider = AiProvider(result.provider)
        except ValueError:
            provider = AiProvider.openai

        req = self._ai_requests.create(
            user_id=run.user_id,
            provider=provider,
            model=result.model,
            request_type=AiRequestType.pipeline,
            status=AiRequestStatus.succeeded,
            prompt_id=prompt.id if prompt else None,
            input_ref={
                "pipeline_run_id": str(run.id),
                "ocr_job_id": str(ocr_job_id),
                "prompt_name": prompt_name,
            },
            output_ref={
                "role": result.message.role,
                "content": result.message.content,
            },
        )
        self._ai_usages.create(
            request_id=req.id,
            tokens_in=int(result.usage.tokens_in or 0),
            tokens_out=int(result.usage.tokens_out or 0),
            latency_ms=int(result.usage.latency_ms or 0),
            cost_estimate=float(result.usage.cost_estimate or 0.0),
        )
        self._session.commit()

        stages = _set_stage(
            stages,
            "ai_analyze",
            status="succeeded",
            output_ref={
                "ai_request_id": str(req.id),
                "provider": result.provider,
                "model": result.model,
            },
        )
        return req.id, stages

    def _stage_persist(
        self,
        run: PipelineRun,
        stages: list[dict[str, Any]],
        ocr_job_id: uuid.UUID,
        ai_request_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        stages = _set_stage(stages, "persist", status="running")
        return _set_stage(
            stages,
            "persist",
            status="succeeded",
            output_ref={
                "pipeline_run_id": str(run.id),
                "ocr_job_id": str(ocr_job_id),
                "ai_request_id": str(ai_request_id),
                "stages": list(STAGE_NAMES),
            },
        )


async def run_pipeline(ctx: dict[str, Any], run_id: str) -> dict[str, Any]:
    """ARQ entrypoint: ``enqueue('run_pipeline', run_id)``."""
    runner_factory = ctx.get("pipeline_runner_factory")
    with SessionLocal() as session:
        if callable(runner_factory):
            runner = runner_factory(session)
        else:
            runner = PipelineRunner(session)
        return runner.run(uuid.UUID(run_id))
