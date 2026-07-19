"""Erasure async job handler (T-17.04 / B-P1-ERASURE).

Hard-deletes storage objects + document rows (CASCADE OCR/RAG/pipeline),
optionally anonymizes and deactivates the target user.
Audit log rows are retained (actor_id SET NULL on user delete — we anonymize instead).
LLM provider logs are out-of-band (local SoR only).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.local_storage_adapter import get_local_storage
from app.adapters.ports import StoragePort
from app.core.database import SessionLocal
from app.models.erasure import ErasureJobStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.erasure_job_repository import ErasureJobRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

_ERASURE_JOB_NAME = "run_erasure_job"


class ErasureJobRunner:
    """Synchronous erasure used by the ARQ worker (and unit tests)."""

    def __init__(
        self,
        session: Session,
        *,
        storage: StoragePort | None = None,
        jobs: ErasureJobRepository | None = None,
        documents: DocumentRepository | None = None,
        users: UserRepository | None = None,
        refresh_tokens: RefreshTokenRepository | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._session = session
        self._storage = storage or get_local_storage()
        self._jobs = jobs or ErasureJobRepository(session)
        self._documents = documents or DocumentRepository(session)
        self._users = users or UserRepository(session)
        self._refresh = refresh_tokens or RefreshTokenRepository(session)
        self._audit = audit or AuditService(session)

    def run(self, job_id: uuid.UUID) -> dict[str, Any]:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            raise ValueError(f"Erasure job not found: {job_id}")
        if job.status in {ErasureJobStatus.succeeded, ErasureJobStatus.failed}:
            return {
                "status": job.status.value,
                "stats": dict(job.stats or {}),
            }

        now = datetime.now(UTC)
        self._jobs.mark_running(job, started_at=now)
        self._session.commit()

        scopes = {str(s).lower() for s in (job.scopes or [])}
        stats: dict[str, Any] = {
            "documents_deleted": 0,
            "storage_deleted": 0,
            "storage_errors": 0,
            "account_anonymized": False,
            "tokens_revoked": 0,
            "scopes": sorted(scopes),
        }

        try:
            if "documents" in scopes or "account" in scopes:
                docs = self._documents.list_all_for_owner(job.target_user_id)
                for doc in docs:
                    try:
                        self._storage.delete(doc.storage_key)
                        stats["storage_deleted"] += 1
                    except Exception:  # noqa: BLE001 — best-effort storage
                        stats["storage_errors"] += 1
                        logger.exception(
                            "erasure storage delete failed key=%s",
                            doc.storage_key,
                        )
                    self._documents.hard_delete(doc)
                    stats["documents_deleted"] += 1
                self._session.flush()

            if "account" in scopes:
                target = self._users.get_by_id(job.target_user_id)
                if target is not None:
                    revoked = self._refresh.revoke_all_for_user(target.id)
                    stats["tokens_revoked"] = int(revoked or 0)
                    self._users.anonymize_and_deactivate(target)
                    stats["account_anonymized"] = True

            self._audit.write(
                action="erasure.completed",
                resource_type="erasure_job",
                actor_id=job.requested_by_id,
                resource_id=str(job.id),
                payload={"stats": stats, "target_user_id": str(job.target_user_id)},
                commit=False,
            )
            finished = datetime.now(UTC)
            self._jobs.mark_succeeded(job, finished_at=finished, stats=stats)
            self._session.commit()
            return {"status": ErasureJobStatus.succeeded.value, "stats": stats}
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            job = self._jobs.get_by_id(job_id)
            if job is not None:
                self._jobs.mark_failed(
                    job,
                    finished_at=datetime.now(UTC),
                    error=str(exc)[:2000],
                    stats=stats,
                )
                self._session.commit()
            logger.exception("erasure job failed id=%s", job_id)
            return {
                "status": ErasureJobStatus.failed.value,
                "error": str(exc),
                "stats": stats,
            }


async def run_erasure_job(ctx: dict, job_id: str) -> dict[str, Any]:
    """ARQ entrypoint."""
    _ = ctx
    session = SessionLocal()
    try:
        runner = ErasureJobRunner(session)
        return runner.run(uuid.UUID(job_id))
    finally:
        session.close()
