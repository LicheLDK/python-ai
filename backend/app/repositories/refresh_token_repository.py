"""RefreshTokenRepository — DB access only (T-1.03 / SDS §5.10, §10.7)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        jti: uuid.UUID,
        expires_at: datetime,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> RefreshToken:
        row = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            jti=jti,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(RefreshToken)
            .options(joinedload(RefreshToken.user))
            .where(RefreshToken.token_hash == token_hash)
        )
        return self._session.scalars(stmt).first()

    def revoke(self, token: RefreshToken, *, at: datetime | None = None) -> None:
        token.revoked_at = at or datetime.now(UTC)
        self._session.flush()

    def set_replaced_by(
        self,
        token: RefreshToken,
        *,
        replaced_by_id: uuid.UUID,
    ) -> None:
        token.replaced_by_id = replaced_by_id
        self._session.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke every non-revoked refresh token for the user. Returns row count."""
        now = datetime.now(UTC)
        result = self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        self._session.flush()
        return int(result.rowcount or 0)
