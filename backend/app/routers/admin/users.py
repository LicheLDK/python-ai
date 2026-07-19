"""Admin user management routes (T-2.03 / SDS §9.9). Controller only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.cookies import client_ip
from app.core.deps import AdminUser, get_db
from app.schemas.admin import AdminUserUpdateRequest, UserAdminPage, UserAdminRead
from app.schemas.user import to_user_read
from app.services.admin_service import AdminService

router = APIRouter(prefix="/users", tags=["admin-users"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)


@router.get("", response_model=UserAdminPage)
def list_users(
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
    q: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> UserAdminPage:
    rows, params, total = service.list_users(
        page=page,
        page_size=page_size,
        q=q,
        role=role,
        status=status,
    )
    return UserAdminPage(
        items=[to_user_read(u) for u in rows],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/{user_id}", response_model=UserAdminRead)
def get_user(
    user_id: uuid.UUID,
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
) -> UserAdminRead:
    return to_user_read(service.get_user(user_id))


@router.patch("/{user_id}", response_model=UserAdminRead)
def patch_user(
    user_id: uuid.UUID,
    body: AdminUserUpdateRequest,
    request: Request,
    admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
) -> UserAdminRead:
    updated = service.patch_user(
        actor=admin,
        user_id=user_id,
        name=body.name,
        role=body.role.value if body.role is not None else None,
        status=body.status.value if body.status is not None else None,
        ip=client_ip(request),
    )
    return to_user_read(updated)
