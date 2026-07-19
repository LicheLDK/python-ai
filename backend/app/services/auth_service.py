"""Authentication use cases (T-1.03 / SDS §7.2, §8.1–8.2).

Owns register/login/refresh rotation/logout/reuse detection and Redis rate-limit
/ denylist coordination. HTTP cookies and CSRF belong to routers (T-1.04).
Access-token jti denylist on logout is T-1.08 (optional hardening).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import (
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    REDIS_KEY_AUTH_DENY_JTI,
    REDIS_KEY_LOGIN_RATE_EMAIL,
    REDIS_KEY_LOGIN_RATE_IP,
)
from app.core.security import (
    access_token_expires_in_seconds,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.exceptions.auth import ForbiddenError, TokenError, UnauthorizedError
from app.exceptions.domain import ConflictError, RateLimitError
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole, UserStatus
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class AuthSession:
    """Result of login / refresh — router sets the refresh cookie."""

    access_token: str
    refresh_token: str
    expires_in: int
    user: User
    token_type: str = "bearer"


class AuthService:
    def __init__(
        self,
        session: Session,
        redis_client: redis.Redis,
        *,
        users: UserRepository | None = None,
        refresh_tokens: RefreshTokenRepository | None = None,
        audit: "AuditService | None" = None,
    ) -> None:
        from app.services.audit_service import AuditService

        self._session = session
        self._redis = redis_client
        self._users = users or UserRepository(session)
        self._refresh_tokens = refresh_tokens or RefreshTokenRepository(session)
        self._orgs = OrganizationRepository(session)
        self._audit = audit or AuditService(session)

    def register(self, *, email: str, password: str, name: str) -> User:
        normalized = email.strip().lower()
        if self._users.get_by_email(normalized) is not None:
            raise ConflictError("Email already registered")

        org = self._orgs.get_or_create_default(
            name=getattr(settings, "default_org_name", None) or "Default Organization",
        )
        user = self._users.create(
            email=normalized,
            password_hash=hash_password(password),
            name=name.strip(),
            org_id=org.id,
            role=UserRole.user,
            status=UserStatus.active,
        )
        self._session.commit()
        self._session.refresh(user)
        return user

    def login(
        self,
        *,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSession:
        normalized = email.strip().lower()
        self._assert_login_rate_limit(email=normalized, ip=ip)

        user = self._users.get_by_email(normalized)
        if user is None or not verify_password(password, user.password_hash):
            self._bump_login_rate_limit(email=normalized, ip=ip)
            # Feed stats metric auth.login.failed (T-7.02 / SDS §9.8).
            try:
                self._audit.write(
                    action="auth.login.failed",
                    resource_type="auth",
                    payload={"email": normalized},
                    ip=ip,
                    commit=True,
                )
            except Exception:  # noqa: BLE001 — audit must not mask auth error
                self._session.rollback()
            raise UnauthorizedError("Invalid email or password")

        if user.status != UserStatus.active:
            raise ForbiddenError("User account is inactive")

        self._clear_login_rate_limit(email=normalized, ip=ip)
        return self._issue_session(user, ip=ip, user_agent=user_agent)

    def refresh(
        self,
        *,
        raw_refresh_token: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSession:
        token_hash = hash_token(raw_refresh_token)
        existing = self._refresh_tokens.get_by_token_hash(token_hash)

        if existing is None:
            raise TokenError("Invalid refresh token")

        if existing.revoked_at is not None:
            # Rotated token replay (has replacement) ⇒ reuse / theft → wipe family.
            # Logout-only revoke (no replaced_by) ⇒ invalid, no family wipe.
            if existing.replaced_by_id is not None:
                self._deny_jti(existing.jti, existing.expires_at)
                self._handle_reuse(existing.user_id)
                raise TokenError("Refresh token reuse detected")
            raise TokenError("Invalid refresh token")

        if self._is_jti_denied(existing.jti):
            self._handle_reuse(existing.user_id)
            raise TokenError("Refresh token reuse detected")

        now = datetime.now(UTC)
        expires_at = self._as_utc(existing.expires_at)
        if expires_at <= now:
            self._refresh_tokens.revoke(existing, at=now)
            self._session.commit()
            raise TokenError("Refresh token expired")

        user = existing.user
        if user.status != UserStatus.active:
            self._refresh_tokens.revoke(existing, at=now)
            self._deny_jti(existing.jti, expires_at)
            self._session.commit()
            raise ForbiddenError("User account is inactive")

        # Rotate in one transaction: revoke old → create new → link chain.
        self._refresh_tokens.revoke(existing, at=now)
        self._deny_jti(existing.jti, expires_at)

        raw_refresh, new_row = self._create_refresh_row(
            user,
            ip=ip,
            user_agent=user_agent,
        )
        self._refresh_tokens.set_replaced_by(existing, replaced_by_id=new_row.id)
        self._session.commit()
        self._session.refresh(user)

        return self._build_session(user, raw_refresh=raw_refresh)

    def logout(self, *, raw_refresh_token: str | None) -> None:
        if not raw_refresh_token:
            return

        token_hash = hash_token(raw_refresh_token)
        existing = self._refresh_tokens.get_by_token_hash(token_hash)
        if existing is None:
            return

        now = datetime.now(UTC)
        if existing.revoked_at is None:
            self._refresh_tokens.revoke(existing, at=now)
        self._deny_jti(existing.jti, existing.expires_at)
        self._session.commit()

    def _issue_session(
        self,
        user: User,
        *,
        ip: str | None,
        user_agent: str | None,
    ) -> AuthSession:
        raw_refresh, _row = self._create_refresh_row(
            user,
            ip=ip,
            user_agent=user_agent,
        )
        self._session.commit()
        self._session.refresh(user)
        return self._build_session(user, raw_refresh=raw_refresh)

    def _create_refresh_row(
        self,
        user: User,
        *,
        ip: str | None,
        user_agent: str | None,
    ) -> tuple[str, RefreshToken]:
        raw_refresh = generate_refresh_token()
        refresh_jti = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
        row = self._refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            jti=refresh_jti,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        return raw_refresh, row

    def _build_session(self, user: User, *, raw_refresh: str) -> AuthSession:
        role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        access = create_access_token(subject=user.id, role=role_value)
        return AuthSession(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=access_token_expires_in_seconds(),
            user=user,
        )

    def _handle_reuse(self, user_id: uuid.UUID) -> None:
        self._refresh_tokens.revoke_all_for_user(user_id)
        self._session.commit()

    def _assert_login_rate_limit(self, *, email: str, ip: str | None) -> None:
        for key in self._login_rate_keys(email=email, ip=ip):
            raw = self._redis.get(key)
            if raw is not None and int(raw) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
                raise RateLimitError("Too many login attempts. Try again later.")

    def _bump_login_rate_limit(self, *, email: str, ip: str | None) -> None:
        for key in self._login_rate_keys(email=email, ip=ip):
            count = self._redis.incr(key)
            if count == 1:
                self._redis.expire(key, LOGIN_RATE_LIMIT_WINDOW_SECONDS)

    def _clear_login_rate_limit(self, *, email: str, ip: str | None) -> None:
        keys = self._login_rate_keys(email=email, ip=ip)
        if keys:
            self._redis.delete(*keys)

    @staticmethod
    def _login_rate_keys(*, email: str, ip: str | None) -> list[str]:
        keys = [REDIS_KEY_LOGIN_RATE_EMAIL.format(email=email.lower())]
        if ip:
            keys.append(REDIS_KEY_LOGIN_RATE_IP.format(ip=ip))
        return keys

    def _deny_jti(self, jti: uuid.UUID, expires_at: datetime) -> None:
        key = REDIS_KEY_AUTH_DENY_JTI.format(jti=str(jti))
        now = datetime.now(UTC)
        expires_at = self._as_utc(expires_at)
        ttl = int((expires_at - now).total_seconds())
        if ttl <= 0:
            return
        self._redis.setex(key, ttl, "1")

    def _is_jti_denied(self, jti: uuid.UUID) -> bool:
        key = REDIS_KEY_AUTH_DENY_JTI.format(jti=str(jti))
        return self._redis.exists(key) == 1

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
