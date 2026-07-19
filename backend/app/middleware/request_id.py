"""X-Request-ID middleware (T-0.05, SDS ADR-019)."""

from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.request_context import get_request_id, reset_request_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"

# Re-export for callers that historically imported from this module.
__all__ = [
    "REQUEST_ID_HEADER",
    "RequestIdMiddleware",
    "get_request_id",
]


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Propagate or generate X-Request-ID on every request/response."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming.strip() if incoming and incoming.strip() else str(uuid4())
        token = set_request_id(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            reset_request_id(token)
