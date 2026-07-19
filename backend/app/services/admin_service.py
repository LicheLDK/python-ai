"""Admin facade (T-2.03 / T-10.01 / SDS §7.4, §9.9)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions.domain import NotFoundError, ValidationAppError
from app.models.ai import AiProvider, AiRequest, AiRequestStatus, AiUsage
from app.models.ocr import OcrJob, OcrJobStatus
from app.models.user import User, UserRole, UserStatus
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.repositories.ocr_result_repository import OcrResultRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminDashboardResponse,
    AiUsageRead,
    DashboardProviderBreakdown,
    DashboardTopUser,
    OcrJobAdminDetail,
    to_ocr_job_admin_read,
)
from app.schemas.ocr import to_ocr_results_read
from app.services.audit_service import AuditService
from app.utils.pagination import PageParams, normalize_page


class AdminService:
    def __init__(
        self,
        session: Session,
        *,
        users: UserRepository | None = None,
        audit: AuditService | None = None,
        audit_logs: AuditLogRepository | None = None,
        usages: AiUsageRepository | None = None,
        ocr_jobs: OcrJobRepository | None = None,
        ocr_results: OcrResultRepository | None = None,
    ) -> None:
        self._session = session
        self._users = users or UserRepository(session)
        self._audit = audit or AuditService(session)
        self._audit_logs = audit_logs or AuditLogRepository(session)
        self._usages = usages or AiUsageRepository(session)
        self._ocr_jobs = ocr_jobs or OcrJobRepository(session)
        self._ocr_results = ocr_results or OcrResultRepository(session)

    # ------------------------------------------------------------------ users
    def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> tuple[list[User], PageParams, int]:
        params = normalize_page(page, page_size)
        role_enum = self._parse_role(role) if role else None
        status_enum = self._parse_status(status) if status else None
        rows, total = self._users.list_filtered(
            page=params,
            q=q,
            role=role_enum,
            status=status_enum,
        )
        return rows, params, total

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def patch_user(
        self,
        *,
        actor: User,
        user_id: uuid.UUID,
        name: str | None = None,
        role: str | None = None,
        status: str | None = None,
        org_id: uuid.UUID | None = None,
        ip: str | None = None,
    ) -> User:
        target = self.get_user(user_id)

        cleaned_name = name.strip() if name is not None else None
        if name is not None and not cleaned_name:
            raise ValidationAppError("Name must not be empty")

        role_enum = self._parse_role(role) if role is not None else None
        status_enum = self._parse_status(status) if status is not None else None

        if org_id is not None:
            from app.repositories.organization_repository import OrganizationRepository

            org = OrganizationRepository(self._session).get_by_id(org_id)
            if org is None:
                raise NotFoundError("Organization not found")

        if (
            cleaned_name is None
            and role_enum is None
            and status_enum is None
            and org_id is None
        ):
            return target

        before = {
            "name": target.name,
            "role": target.role.value if isinstance(target.role, UserRole) else str(target.role),
            "status": (
                target.status.value
                if isinstance(target.status, UserStatus)
                else str(target.status)
            ),
            "org_id": str(target.org_id),
        }

        updated = self._users.apply_admin_update(
            target,
            name=cleaned_name,
            role=role_enum,
            status=status_enum,
            org_id=org_id,
        )

        after = {
            "name": updated.name,
            "role": updated.role.value if isinstance(updated.role, UserRole) else str(updated.role),
            "status": (
                updated.status.value
                if isinstance(updated.status, UserStatus)
                else str(updated.status)
            ),
            "org_id": str(updated.org_id),
        }
        changes = {k: {"from": before[k], "to": after[k]} for k in before if before[k] != after[k]}

        self._audit.write(
            action="admin.user.update",
            resource_type="user",
            actor_id=actor.id,
            resource_id=str(updated.id),
            payload={"changes": changes},
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(updated)
        return updated

    # ------------------------------------------------------------------ usage
    def list_usage(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        provider: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[AiUsageRead], PageParams, int]:
        params = normalize_page(page, page_size)
        provider_enum = None
        if provider:
            try:
                provider_enum = AiProvider(provider)
            except ValueError as exc:
                raise ValidationAppError(
                    "Invalid provider",
                    details={"allowed": [p.value for p in AiProvider]},
                ) from exc
        rows, total = self._usages.list_joined(
            page=params,
            date_from=date_from,
            date_to=date_to,
            provider=provider_enum,
            user_id=user_id,
        )
        items = [AiUsageRead(**row) for row in rows]
        return items, params, total

    # ------------------------------------------------------------- ocr-history
    def list_ocr_history(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        user_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[OcrJob], PageParams, int]:
        params = normalize_page(page, page_size)
        status_enum = None
        if status:
            try:
                status_enum = OcrJobStatus(status)
            except ValueError as exc:
                raise ValidationAppError("Invalid OCR status") from exc
        rows, total = self._ocr_jobs.list_all(
            page=params,
            status=status_enum,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        return rows, params, total

    def get_ocr_history_detail(self, job_id: uuid.UUID) -> OcrJobAdminDetail:
        job = self._ocr_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("OCR job not found")
        pages_rows = self._ocr_results.list_for_job(job_id)
        results = to_ocr_results_read(job_id, pages_rows)
        return OcrJobAdminDetail(
            job=to_ocr_job_admin_read(job),
            pages=results.pages,
        )

    # --------------------------------------------------------------- audit-logs
    def list_audit_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, PageParams, int]:
        params = normalize_page(page, page_size)
        rows, total = self._audit_logs.list_filtered(
            page=params,
            actor_id=actor_id,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        return rows, params, total

    # ---------------------------------------------------------------- dashboard
    def dashboard(self) -> AdminDashboardResponse:
        now = datetime.now(UTC)
        since = now - timedelta(hours=24)

        users_total = int(
            self._session.scalar(select(func.count()).select_from(User)) or 0
        )

        ocr_total, ocr_failed = self._session.execute(
            select(
                func.count(),
                func.count().filter(OcrJob.status == OcrJobStatus.failed),
            ).where(OcrJob.created_at >= since)
        ).one()

        ai_total, ai_failed = self._session.execute(
            select(
                func.count(),
                func.count().filter(AiRequest.status == AiRequestStatus.failed),
            ).where(AiRequest.created_at >= since)
        ).one()

        total_ops = int(ocr_total) + int(ai_total)
        failures = int(ocr_failed) + int(ai_failed)
        error_rate = (failures / total_ops) if total_ops else 0.0

        # Top users by combined OCR + AI volume in 24h.
        ocr_by_user = {
            uid: int(cnt)
            for uid, cnt in self._session.execute(
                select(OcrJob.user_id, func.count())
                .where(OcrJob.created_at >= since)
                .group_by(OcrJob.user_id)
            ).all()
        }
        ai_by_user = {
            uid: int(cnt)
            for uid, cnt in self._session.execute(
                select(AiRequest.user_id, func.count())
                .where(AiRequest.created_at >= since)
                .group_by(AiRequest.user_id)
            ).all()
        }
        combined: dict[uuid.UUID, tuple[int, int]] = {}
        for uid, cnt in ocr_by_user.items():
            combined[uid] = (cnt, ai_by_user.get(uid, 0))
        for uid, cnt in ai_by_user.items():
            if uid not in combined:
                combined[uid] = (0, cnt)

        ranked = sorted(
            combined.items(),
            key=lambda item: item[1][0] + item[1][1],
            reverse=True,
        )[:5]
        top_users: list[DashboardTopUser] = []
        for uid, (ocr_cnt, ai_cnt) in ranked:
            user = self._users.get_by_id(uid)
            top_users.append(
                DashboardTopUser(
                    user_id=uid,
                    email=user.email if user else None,
                    ocr_jobs=ocr_cnt,
                    ai_requests=ai_cnt,
                )
            )

        provider_rows = self._session.execute(
            select(
                AiRequest.provider,
                func.count(),
                func.coalesce(func.sum(AiUsage.tokens_in), 0),
                func.coalesce(func.sum(AiUsage.tokens_out), 0),
                func.coalesce(func.sum(AiUsage.cost_estimate), 0),
            )
            .outerjoin(AiUsage, AiUsage.request_id == AiRequest.id)
            .where(AiRequest.created_at >= since)
            .group_by(AiRequest.provider)
            .order_by(func.count().desc())
        ).all()
        provider_breakdown = [
            DashboardProviderBreakdown(
                provider=p.value if hasattr(p, "value") else str(p),
                requests=int(cnt),
                tokens_in=int(tin or 0),
                tokens_out=int(tout or 0),
                cost_estimate=float(cost or 0),
            )
            for p, cnt, tin, tout, cost in provider_rows
        ]

        return AdminDashboardResponse(
            users_total=users_total,
            ocr_jobs_24h=int(ocr_total),
            ai_requests_24h=int(ai_total),
            error_rate_24h=error_rate,
            top_users=top_users,
            provider_breakdown=provider_breakdown,
        )

    @staticmethod
    def _parse_role(value: str) -> UserRole:
        try:
            return UserRole(value)
        except ValueError as exc:
            raise ValidationAppError("Invalid role") from exc

    @staticmethod
    def _parse_status(value: str) -> UserStatus:
        try:
            return UserStatus(value)
        except ValueError as exc:
            raise ValidationAppError("Invalid status") from exc
