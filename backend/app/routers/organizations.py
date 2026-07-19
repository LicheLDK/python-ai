"""Org me + admin org routes (T-16.04). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cookies import client_ip
from app.core.deps import AdminUser, CurrentUser, get_db
from app.schemas.organization import (
    OrganizationAdminUpdate,
    OrganizationCreate,
    OrganizationMeUpdate,
    OrganizationPage,
    OrganizationRead,
    to_organization_read,
)
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["organizations"])


def get_organization_service(db: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(db)


def _read(org) -> OrganizationRead:
    return to_organization_read(
        org,
        default_ai_max=settings.ai_rate_limit_max,
        default_ai_window=settings.ai_rate_limit_window_seconds,
    )


# ---- user-facing ----

me_router = APIRouter(prefix="/orgs", tags=["organizations"])


@me_router.get("/me", response_model=OrganizationRead)
def get_my_org(
    user: CurrentUser,
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    return _read(service.get_for_user(user))


@me_router.patch("/me", response_model=OrganizationRead)
def patch_my_org(
    body: OrganizationMeUpdate,
    user: CurrentUser,
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    return _read(service.update_my_org(actor=user, name=body.name))


# ---- admin ----

admin_router = APIRouter(prefix="/orgs", tags=["admin-organizations"])


@admin_router.get("", response_model=OrganizationPage)
def list_orgs(
    _admin: AdminUser,
    service: OrganizationService = Depends(get_organization_service),
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> OrganizationPage:
    rows, params, total = service.list_orgs(
        page=page,
        page_size=page_size,
        q=q,
        status=status,
    )
    return OrganizationPage(
        items=[_read(o) for o in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@admin_router.post("", response_model=OrganizationRead, status_code=201)
def create_org(
    body: OrganizationCreate,
    request: Request,
    admin: AdminUser,
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    org = service.create_org(
        actor=admin,
        name=body.name,
        slug=body.slug,
        ai_rate_limit_max=body.ai_rate_limit_max,
        ai_rate_limit_window_seconds=body.ai_rate_limit_window_seconds,
        branding=body.branding,
        ip=client_ip(request),
    )
    return _read(org)


@admin_router.get("/{org_id}", response_model=OrganizationRead)
def get_org(
    org_id: uuid.UUID,
    _admin: AdminUser,
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    return _read(service.get_org(org_id))


@admin_router.patch("/{org_id}", response_model=OrganizationRead)
def patch_org(
    org_id: uuid.UUID,
    body: OrganizationAdminUpdate,
    request: Request,
    admin: AdminUser,
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationRead:
    org = service.patch_org(
        actor=admin,
        org_id=org_id,
        name=body.name,
        status=body.status,
        ai_rate_limit_max=body.ai_rate_limit_max,
        ai_rate_limit_window_seconds=body.ai_rate_limit_window_seconds,
        clear_ai_rate_limits=body.clear_ai_rate_limits,
        branding=body.branding,
        ip=client_ip(request),
    )
    return _read(org)
