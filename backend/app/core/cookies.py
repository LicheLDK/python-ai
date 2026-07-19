"""Auth cookie and CSRF helpers (T-1.04 / SDS ADR-008, §9.2).

Double-submit: csrf cookie (readable) must match X-CSRF-Token header.
"""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import Request, Response

from app.core.config import settings
from app.core.constants import (
    AUTH_COOKIE_PATH,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    REFRESH_COOKIE_NAME,
)
from app.exceptions.auth import ForbiddenError, UnauthorizedError


def _cookie_secure() -> bool:
    return settings.app_env.lower() not in {"local", "test", "development", "dev"}


def _samesite() -> Literal["lax", "strict", "none"]:
    return "lax"


def set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_samesite(),
        path=AUTH_COOKIE_PATH,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_samesite(),
    )


def set_csrf_cookie(response: Response, csrf_token: str) -> None:
    # Not HttpOnly — client must read cookie and send X-CSRF-Token (double-submit).
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=_cookie_secure(),
        samesite=_samesite(),
        path=AUTH_COOKIE_PATH,
        max_age=60 * 60,
    )


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        httponly=False,
        secure=_cookie_secure(),
        samesite=_samesite(),
    )


def issue_csrf_token(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    set_csrf_cookie(response, token)
    return token


def get_refresh_token_from_request(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE_NAME)


def require_csrf(request: Request) -> None:
    """Validate double-submit CSRF for cookie-authenticated auth routes."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise ForbiddenError("CSRF validation failed")


def require_refresh_cookie(request: Request) -> str:
    raw = get_refresh_token_from_request(request)
    if not raw:
        raise UnauthorizedError("Refresh token cookie missing")
    return raw


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None
