"""Auth-related exceptions (types only; auth feature is a later task)."""

from app.exceptions.base import AppError


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", *, details=None) -> None:
        super().__init__(
            message,
            code="unauthorized",
            status_code=401,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden", *, details=None) -> None:
        super().__init__(
            message,
            code="forbidden",
            status_code=403,
            details=details,
        )


class TokenError(AppError):
    def __init__(self, message: str = "Invalid token", *, details=None) -> None:
        super().__init__(
            message,
            code="unauthorized",
            status_code=401,
            details=details,
        )
