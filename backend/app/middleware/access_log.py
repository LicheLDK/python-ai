"""Structured access log middleware (T-0.05)."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.request_context import get_request_id

logger = logging.getLogger("app.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, latency, and request_id as JSON via root logger."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        client_ip = request.client.host if request.client else None
        logger.info(
            "request completed",
            extra={
                "request_id": get_request_id() or getattr(request.state, "request_id", ""),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
            },
        )
        return response
