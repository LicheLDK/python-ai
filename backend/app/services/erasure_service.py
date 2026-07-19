"""ErasureService — request account/document erasure jobs (T-17.03)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.adapters.queue_publisher import QueuePublisher
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import ConflictError, NotFoundError, ValidationAppError
from app.models.erasure import ErasureJob
from app.models.user import User, UserRole
from app.repositories.erasure_job_repository import ErasureJobRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

ALLOWED_SCOPES = frozenset({"account", "documents"})


class ErasureService:
    def __init__(
        self,
        session: Session,
        *,
        jobs: ErasureJobRepository | None = None,
        users: UserRepository | None = None,
        queue: QueuePublisher | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._session = session
        self._jobs = jobs or ErasureJobRepository(session)
        self._users = users or UserRepository(session)
        self._queue = queue or QueuePublisher()
        self._audit = audit or AuditService(session)

    def request_self_erasure(self, *, actor: User) -> ErasureJob:
        return self._create_job(
            actor=actor,
            target_user_id=actor.id,
            scopes=["account"],
            ip=None,
        )

    def request_admin_erasure(
        self,
        *,
        actor: User,
        target_user_id: uuid.UUID,
        scopes: Sequence[str],
        ip: str | None = None,
    ) -> ErasureJob:
        if not self._is_admin(actor):
            raise ForbiddenError("Admin only")
        return self._create_job(
            actor=actor,
            target_user_id=target_user_id,
            scopes=scopes,
            ip=ip,
        )

    def get_for_actor(self, *, actor: User, job_id: uuid.UUID) -> ErasureJob:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Erasure job not found")
        if self._is_admin(actor):
            return job
        if job.target_user_id != actor.id and job.requested_by_id != actor.id:
            raise ForbiddenError("Not allowed to view this erasure job")
        return job

    async def enqueue_job(self, job_id: uuid.UUID) -> None:
        await self._queue.enqueue_erasure_job(str(job_id))

    def _create_job(
        self,
        *,
        actor: User,
        target_user_id: uuid.UUID,
        scopes: Sequence[str],
        ip: str | None,
    ) -> ErasureJob:
        normalized = self._normalize_scopes(scopes)
        target = self._users.get_by_id(target_user_id)
        if target is None:
            raise NotFoundError("User not found")

        if self._jobs.has_active_for_user(target_user_id):
            raise ConflictError(
                "An erasure job is already queued or running for this user"
            )

        job = self._jobs.create(
            target_user_id=target_user_id,
            requested_by_id=actor.id,
            scopes=normalized,
        )
        self._audit.write(
            action="erasure.requested",
            resource_type="erasure_job",
            actor_id=actor.id,
            resource_id=str(job.id),
            payload={
                "target_user_id": str(target_user_id),
                "scopes": normalized,
            },
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(job)
        return job

    @staticmethod
    def _normalize_scopes(scopes: Sequence[str]) -> list[str]:
        cleaned: list[str] = []
        for raw in scopes:
            key = (raw or "").strip().lower()
            if key not in ALLOWED_SCOPES:
                raise ValidationAppError(
                    "Invalid erasure scope",
                    details={"allowed": sorted(ALLOWED_SCOPES), "got": raw},
                )
            if key not in cleaned:
                cleaned.append(key)
        if not cleaned:
            raise ValidationAppError("scopes must not be empty")
        # account implies documents hard-delete as well
        if "account" in cleaned and "documents" not in cleaned:
            cleaned.append("documents")
        return cleaned

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value
