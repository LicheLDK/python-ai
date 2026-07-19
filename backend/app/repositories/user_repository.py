"""UserRepository — DB access only (T-1.03 / T-2.03 / SDS §5.10)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus
from app.utils.pagination import PageParams


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self._session.scalars(stmt).first()

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        name: str,
        org_id: uuid.UUID,
        role: UserRole = UserRole.user,
        status: UserStatus = UserStatus.active,
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email.lower(),
            password_hash=password_hash,
            name=name,
            org_id=org_id,
            role=role,
            status=status,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def update_name(self, user: User, *, name: str) -> User:
        user.name = name
        self._session.flush()
        return user

    def list_filtered(
        self,
        *,
        page: PageParams,
        q: str | None = None,
        role: UserRole | None = None,
        status: UserStatus | None = None,
    ) -> tuple[list[User], int]:
        filters = []
        if q:
            like = f"%{q.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(User.email).like(like),
                    func.lower(User.name).like(like),
                )
            )
        if role is not None:
            filters.append(User.role == role)
        if status is not None:
            filters.append(User.status == status)

        count_stmt = select(func.count()).select_from(User)
        list_stmt = select(User).order_by(User.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(
            self._session.scalars(
                list_stmt.offset(page.offset).limit(page.limit)
            ).all()
        )
        return rows, total

    def apply_admin_update(
        self,
        user: User,
        *,
        name: str | None = None,
        role: UserRole | None = None,
        status: UserStatus | None = None,
        org_id: uuid.UUID | None = None,
    ) -> User:
        if name is not None:
            user.name = name
        if role is not None:
            user.role = role
        if status is not None:
            user.status = status
        if org_id is not None:
            user.org_id = org_id
        self._session.flush()
        return user

    def anonymize_and_deactivate(self, user: User) -> User:
        """GDPR-style local SoR erase — keep row for FK/audit history."""
        from app.core.security import hash_password

        user.email = f"erased+{user.id}@erased.local"
        user.name = "Erased User"
        user.status = UserStatus.inactive
        user.password_hash = hash_password(f"erased-{user.id}-{uuid.uuid4().hex}")
        self._session.flush()
        return user
