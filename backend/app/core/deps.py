"""FastAPI dependencies (T-0.06 DB session, T-1.05 auth guards).

SDS §5: `core/deps.py` — db, current_user, roles.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db as _get_db
from app.core.security import decode_access_token
from app.exceptions.auth import ForbiddenError, TokenError, UnauthorizedError
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import UserRepository

# Re-export for `Depends(get_db)`.
get_db = _get_db

_bearer = HTTPBearer(auto_error=False)


def get_db_session() -> Generator[Session, None, None]:
    """Alias kept for readability in routers."""
    yield from _get_db()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ] = None,
    db: Session = Depends(get_db),
) -> User:
    """Resolve Bearer access JWT → active User. Raises 401/403."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Not authenticated")

    try:
        claims = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise UnauthorizedError(exc.message) from exc

    user = UserRepository(db).get_by_id(claims.sub)
    if user is None:
        raise UnauthorizedError("User not found")

    if user.status != UserStatus.active:
        raise ForbiddenError("User account is inactive")

    return user


def require_roles(*roles: UserRole | str) -> Callable[..., User]:
    """Dependency factory: current user must have one of the given roles."""
    allowed = {
        role.value if isinstance(role, UserRole) else str(role) for role in roles
    }

    def _require_roles(user: User = Depends(get_current_user)) -> User:
        role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        if role_value not in allowed:
            raise ForbiddenError("Insufficient role")
        return user

    return _require_roles


require_admin = require_roles(UserRole.admin)

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
