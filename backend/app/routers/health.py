"""Health and readiness probes (T-0.07, SDS ADR-028).

Controller layer only — dependency checks live in core helpers.
Normative paths: GET /health, GET /ready (no /api/v1 prefix).
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import ping_postgres
from app.core.redis import ping_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: process is up (does not check dependencies)."""
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready() -> JSONResponse:
    """Readiness: PostgreSQL and Redis must both respond."""
    postgres_ok = ping_postgres()
    redis_ok = ping_redis()
    body = {
        "status": "ok" if postgres_ok and redis_ok else "unavailable",
        "postgres": postgres_ok,
        "redis": redis_ok,
    }
    status_code = 200 if postgres_ok and redis_ok else 503
    return JSONResponse(status_code=status_code, content=body)
