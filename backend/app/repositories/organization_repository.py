"""OrganizationRepository — DB access only (T-16.03)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.organization import Organization, OrganizationStatus
from app.utils.pagination import PageParams

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_ORG_SLUG = "default"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return (slug or "org")[:64]


class OrganizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        return self._session.get(Organization, org_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug.strip().lower())
        return self._session.scalars(stmt).first()

    def get_or_create_default(
        self,
        *,
        name: str = "Default Organization",
    ) -> Organization:
        existing = self.get_by_id(DEFAULT_ORG_ID)
        if existing is not None:
            return existing
        by_slug = self.get_by_slug(DEFAULT_ORG_SLUG)
        if by_slug is not None:
            return by_slug
        org = Organization(
            id=DEFAULT_ORG_ID,
            name=name,
            slug=DEFAULT_ORG_SLUG,
            status=OrganizationStatus.active,
            branding={},
        )
        self._session.add(org)
        self._session.flush()
        return org

    def create(
        self,
        *,
        name: str,
        slug: str | None = None,
        status: OrganizationStatus = OrganizationStatus.active,
        ai_rate_limit_max: int | None = None,
        ai_rate_limit_window_seconds: int | None = None,
        branding: dict[str, Any] | None = None,
        org_id: uuid.UUID | None = None,
    ) -> Organization:
        resolved_slug = slugify(slug or name)
        org = Organization(
            id=org_id or uuid.uuid4(),
            name=name.strip(),
            slug=resolved_slug,
            status=status,
            ai_rate_limit_max=ai_rate_limit_max,
            ai_rate_limit_window_seconds=ai_rate_limit_window_seconds,
            branding=branding or {},
        )
        self._session.add(org)
        self._session.flush()
        return org

    def list_filtered(
        self,
        *,
        page: PageParams,
        q: str | None = None,
        status: OrganizationStatus | None = None,
    ) -> tuple[list[Organization], int]:
        filters = []
        if q:
            like = f"%{q.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Organization.name).like(like),
                    func.lower(Organization.slug).like(like),
                )
            )
        if status is not None:
            filters.append(Organization.status == status)

        count_stmt = select(func.count()).select_from(Organization)
        list_stmt = select(Organization).order_by(Organization.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(
            self._session.scalars(list_stmt.offset(page.offset).limit(page.limit)).all()
        )
        return rows, total

    def apply_update(
        self,
        org: Organization,
        *,
        name: str | None = None,
        status: OrganizationStatus | None = None,
        ai_rate_limit_max: int | None = None,
        ai_rate_limit_window_seconds: int | None = None,
        clear_ai_rate_limit_max: bool = False,
        clear_ai_rate_limit_window: bool = False,
        branding: dict[str, Any] | None = None,
    ) -> Organization:
        if name is not None:
            org.name = name
        if status is not None:
            org.status = status
        if clear_ai_rate_limit_max:
            org.ai_rate_limit_max = None
        elif ai_rate_limit_max is not None:
            org.ai_rate_limit_max = ai_rate_limit_max
        if clear_ai_rate_limit_window:
            org.ai_rate_limit_window_seconds = None
        elif ai_rate_limit_window_seconds is not None:
            org.ai_rate_limit_window_seconds = ai_rate_limit_window_seconds
        if branding is not None:
            org.branding = branding
        self._session.flush()
        return org
