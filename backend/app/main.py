"""FastAPI application factory.

T-0.04: app shell + empty router + temporary GET /
T-0.05: settings, JSON logging, request-id, error envelope
T-0.07: /health and /ready probes
T-1.04: CORS (credentials) for refresh cookie + /api/v1/auth
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.exceptions.handlers import register_exception_handlers
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.routers import api_router
from app.routers.health import router as health_router


def create_app() -> FastAPI:
    """Application factory — preferred entry for tests and uvicorn."""
    configure_logging()

    application = FastAPI(
        title="AI SaaS Framework",
        version="0.0.0",
        description="API shell. See docs/PRD.md and docs/SDS.md.",
    )

    # Middleware order: last added runs first on the request path.
    application.add_middleware(AccessLogMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    application.include_router(health_router)
    application.include_router(api_router)

    @application.get("/", tags=["root"])
    def root() -> dict[str, str]:
        """Temporary probe endpoint from T-0.04."""
        return {
            "message": "AI SaaS Framework API is running",
            "app_env": settings.app_env,
        }

    return application


app = create_app()
