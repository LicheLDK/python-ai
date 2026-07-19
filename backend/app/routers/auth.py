"""Auth routes (T-1.04 / SDS §9.2). Controller only — logic in AuthService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.cookies import (
    clear_csrf_cookie,
    clear_refresh_cookie,
    client_ip,
    get_refresh_token_from_request,
    issue_csrf_token,
    require_csrf,
    require_refresh_cookie,
    set_refresh_cookie,
)
from app.core.deps import get_db
from app.core.redis import get_redis
from app.schemas.auth import (
    CsrfResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import RegisterResponse, UserRead, to_user_read
from app.services.auth_service import AuthService, AuthSession

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    db: Session = Depends(get_db),
) -> AuthService:
    return AuthService(db, get_redis())


def _user_read(user) -> UserRead:
    return to_user_read(user)


def _token_response(session: AuthSession) -> TokenResponse:
    return TokenResponse(
        access_token=session.access_token,
        token_type=session.token_type,
        expires_in=session.expires_in,
        user=_user_read(session.user),
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    body: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    user = auth.register(email=body.email, password=body.password, name=body.name)
    return RegisterResponse(user=_user_read(user))


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    session = auth.login(
        email=body.email,
        password=body.password,
        ip=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    set_refresh_cookie(response, session.refresh_token)
    issue_csrf_token(response)
    return _token_response(session)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    require_csrf(request)
    raw_refresh = require_refresh_cookie(request)
    session = auth.refresh(
        raw_refresh_token=raw_refresh,
        ip=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    set_refresh_cookie(response, session.refresh_token)
    issue_csrf_token(response)
    return _token_response(session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> None:
    # Cookie-based logout requires CSRF (SDS). Idempotent if already logged out.
    raw_refresh = get_refresh_token_from_request(request)
    if raw_refresh:
        require_csrf(request)
        auth.logout(raw_refresh_token=raw_refresh)
    clear_refresh_cookie(response)
    clear_csrf_cookie(response)
    return None


@router.get("/csrf", response_model=CsrfResponse)
def csrf(response: Response) -> CsrfResponse:
    token = issue_csrf_token(response)
    return CsrfResponse(csrf_token=token)
