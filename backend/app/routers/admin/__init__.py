"""Admin router package (T-2.03 / T-10.01)."""

from fastapi import APIRouter

from app.routers.admin import audit as admin_audit
from app.routers.admin import dashboard as admin_dashboard
from app.routers.admin import ocr_history as admin_ocr_history
from app.routers.admin import usage as admin_usage
from app.routers.admin import users as admin_users

router = APIRouter(prefix="/admin")
router.include_router(admin_users.router)
router.include_router(admin_usage.router)
router.include_router(admin_ocr_history.router)
router.include_router(admin_audit.router)
router.include_router(admin_dashboard.router)
