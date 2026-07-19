"""Global exception handlers → SDS error envelope (T-0.05)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import get_request_id
from app.exceptions.base import AppError
from app.schemas.common import ErrorEnvelope

logger = logging.getLogger(__name__)

_HTTP_CODE_MAP: dict[int, str] = {
    400: "app_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    502: "provider_error",
}


def _resolve_request_id(request: Request) -> str:
    return (
        get_request_id()
        or getattr(request.state, "request_id", None)
        or request.headers.get("X-Request-ID")
        or ""
    )


def _envelope(
    *,
    code: str,
    message: str,
    request_id: str,
    details: Any | None = None,
) -> dict[str, Any]:
    return ErrorEnvelope(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global handlers that always return the standard error body."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = _resolve_request_id(request)
        headers = {"X-Request-ID": request_id} if request_id else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _resolve_request_id(request)
        headers = {"X-Request-ID": request_id} if request_id else None
        return JSONResponse(
            status_code=422,
            content=_envelope(
                code="validation_error",
                message="Request validation failed",
                details=exc.errors(),
                request_id=request_id,
            ),
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        request_id = _resolve_request_id(request)
        headers = {"X-Request-ID": request_id} if request_id else None
        code = _HTTP_CODE_MAP.get(exc.status_code, "app_error")
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        details = None if isinstance(exc.detail, str) else exc.detail
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                code=code,
                message=message,
                details=details,
                request_id=request_id,
            ),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _resolve_request_id(request)
        headers = {"X-Request-ID": request_id} if request_id else None
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content=_envelope(
                code="app_error",
                message="Internal server error",
                details=None,
                request_id=request_id,
            ),
            headers=headers,
        )
