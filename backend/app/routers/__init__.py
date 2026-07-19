"""Controller package (SDS routers).

Registers versioned API routers under /api/v1.
"""

from fastapi import APIRouter

from app.routers.admin import router as admin_router
from app.routers.ai import router as ai_router
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.ocr import router as ocr_router
from app.routers.pipelines import router as pipelines_router
from app.routers.probe import router as probe_router
from app.routers.stats import router as stats_router
from app.routers.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(documents_router)
api_router.include_router(ocr_router)
api_router.include_router(ai_router)
api_router.include_router(pipelines_router)
api_router.include_router(stats_router)
api_router.include_router(admin_router)
api_router.include_router(probe_router)
