"""User profile use cases (T-2.02 / SDS §9.3)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.domain import ValidationAppError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(
        self,
        session: Session,
        *,
        users: UserRepository | None = None,
    ) -> None:
        self._session = session
        self._users = users or UserRepository(session)

    def get_me(self, user: User) -> User:
        """Return the authenticated user (already loaded by Depends)."""
        return user

    def update_me(self, user: User, *, name: str | None) -> User:
        """Update mutable profile fields. Email is immutable in v1."""
        if name is None:
            return user

        cleaned = name.strip()
        if not cleaned:
            raise ValidationAppError("Name must not be empty")

        updated = self._users.update_name(user, name=cleaned)
        self._session.commit()
        self._session.refresh(updated)
        return updated
