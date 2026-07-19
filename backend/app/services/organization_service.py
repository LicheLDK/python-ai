"""OrganizationService — soft tenant CRUD + quota helpers (T-16.03–T-16.05)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import ConflictError, NotFoundError, ValidationAppError
from app.models.organization import Organization, OrganizationStatus
from app.models.user import User, UserRole
from app.repositories.organization_repository import OrganizationRepository
from app.services.audit_service import AuditService
from app.utils.pagination import PageParams, normalize_page


class OrganizationService:
    def __init__(
        self,
        session: Session,
        *,
        orgs: OrganizationRepository | None = None,
        audit: AuditService | None = None,
        cfg: Settings | None = None,
    ) -> None:
        self._session = session
        self._orgs = orgs or OrganizationRepository(session)
        self._audit = audit or AuditService(session)
        self._settings = cfg or settings

    def get_for_user(self, actor: User) -> Organization:
        org = self._orgs.get_by_id(actor.org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return org

    def update_my_org(
        self,
        *,
        actor: User,
        name: str | None = None,
    ) -> Organization:
        org = self.get_for_user(actor)
        cleaned = name.strip() if name is not None else None
        if name is not None and not cleaned:
            raise ValidationAppError("Name must not be empty")
        if cleaned is None:
            return org
        updated = self._orgs.apply_update(org, name=cleaned)
        self._session.commit()
        self._session.refresh(updated)
        return updated

    def list_orgs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Organization], PageParams, int]:
        params = normalize_page(page, page_size)
        status_enum = None
        if status is not None:
            try:
                status_enum = OrganizationStatus(status)
            except ValueError as exc:
                raise ValidationAppError(
                    "Invalid status",
                    details={"allowed": [s.value for s in OrganizationStatus]},
                ) from exc
        rows, total = self._orgs.list_filtered(page=params, q=q, status=status_enum)
        return rows, params, total

    def get_org(self, org_id: uuid.UUID) -> Organization:
        org = self._orgs.get_by_id(org_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return org

    def create_org(
        self,
        *,
        actor: User,
        name: str,
        slug: str | None = None,
        ai_rate_limit_max: int | None = None,
        ai_rate_limit_window_seconds: int | None = None,
        branding: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> Organization:
        if slug:
            existing = self._orgs.get_by_slug(slug)
            if existing is not None:
                raise ConflictError("Organization slug already exists")
        org = self._orgs.create(
            name=name,
            slug=slug,
            ai_rate_limit_max=ai_rate_limit_max,
            ai_rate_limit_window_seconds=ai_rate_limit_window_seconds,
            branding=branding,
        )
        self._audit.write(
            action="admin.org.create",
            resource_type="organization",
            actor_id=actor.id,
            resource_id=str(org.id),
            payload={"name": org.name, "slug": org.slug},
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(org)
        return org

    def patch_org(
        self,
        *,
        actor: User,
        org_id: uuid.UUID,
        name: str | None = None,
        status: str | None = None,
        ai_rate_limit_max: int | None = None,
        ai_rate_limit_window_seconds: int | None = None,
        clear_ai_rate_limits: bool = False,
        branding: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> Organization:
        org = self.get_org(org_id)
        cleaned_name = name.strip() if name is not None else None
        if name is not None and not cleaned_name:
            raise ValidationAppError("Name must not be empty")

        status_enum = None
        if status is not None:
            try:
                status_enum = OrganizationStatus(status)
            except ValueError as exc:
                raise ValidationAppError("Invalid status") from exc

        if (
            cleaned_name is None
            and status_enum is None
            and ai_rate_limit_max is None
            and ai_rate_limit_window_seconds is None
            and not clear_ai_rate_limits
            and branding is None
        ):
            return org

        before = {
            "name": org.name,
            "status": org.status.value if isinstance(org.status, OrganizationStatus) else str(org.status),
            "ai_rate_limit_max": org.ai_rate_limit_max,
            "ai_rate_limit_window_seconds": org.ai_rate_limit_window_seconds,
        }
        updated = self._orgs.apply_update(
            org,
            name=cleaned_name,
            status=status_enum,
            ai_rate_limit_max=ai_rate_limit_max,
            ai_rate_limit_window_seconds=ai_rate_limit_window_seconds,
            clear_ai_rate_limit_max=clear_ai_rate_limits,
            clear_ai_rate_limit_window=clear_ai_rate_limits,
            branding=branding,
        )
        after = {
            "name": updated.name,
            "status": (
                updated.status.value
                if isinstance(updated.status, OrganizationStatus)
                else str(updated.status)
            ),
            "ai_rate_limit_max": updated.ai_rate_limit_max,
            "ai_rate_limit_window_seconds": updated.ai_rate_limit_window_seconds,
        }
        changes = {
            k: {"from": before[k], "to": after[k]} for k in before if before[k] != after[k]
        }
        self._audit.write(
            action="admin.org.update",
            resource_type="organization",
            actor_id=actor.id,
            resource_id=str(updated.id),
            payload={"changes": changes},
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(updated)
        return updated

    def effective_ai_quota(self, org: Organization | None) -> tuple[int, int]:
        default_max = int(self._settings.ai_rate_limit_max)
        default_window = int(self._settings.ai_rate_limit_window_seconds)
        if org is None:
            return default_max, default_window
        max_req = (
            int(org.ai_rate_limit_max)
            if org.ai_rate_limit_max is not None
            else default_max
        )
        window = (
            int(org.ai_rate_limit_window_seconds)
            if org.ai_rate_limit_window_seconds is not None
            else default_window
        )
        return max_req, window

    @staticmethod
    def assert_same_org(actor: User, org_id: uuid.UUID) -> None:
        role = actor.role.value if isinstance(actor.role, UserRole) else str(actor.role)
        if role == UserRole.admin.value:
            return
        if actor.org_id != org_id:
            raise ForbiddenError("Not allowed to access this organization")
