"""Admin dashboard KPI route (T-10.01 / SDS §9.9). Controller only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AdminUser, get_db
from app.schemas.admin import AdminDashboardResponse
from app.services.admin_service import AdminService

router = APIRouter(tags=["admin-dashboard"])


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    return AdminService(db)


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _admin: AdminUser,
    service: AdminService = Depends(get_admin_service),
) -> AdminDashboardResponse:
    return service.dashboard()
