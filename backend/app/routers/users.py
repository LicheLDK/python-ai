"""User profile routes (T-2.02 / SDS §9.3). Controller only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.schemas.user import UserRead, UserUpdateRequest, to_user_read
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/me", response_model=UserRead)
def get_me(
    user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return to_user_read(service.get_me(user))


@router.patch("/me", response_model=UserRead)
def patch_me(
    body: UserUpdateRequest,
    user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    updated = service.update_me(user, name=body.name)
    return to_user_read(updated)
