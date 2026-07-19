"""Provider exceptions (types only; provider adapters are later tasks)."""

from app.exceptions.base import AppError


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limited", *, details=None) -> None:
        super().__init__(
            message,
            code="rate_limited",
            status_code=429,
            details=details,
        )


class ProviderTimeoutError(AppError):
    def __init__(self, message: str = "Provider timeout", *, details=None) -> None:
        super().__init__(
            message,
            code="provider_timeout",
            status_code=502,
            details=details,
        )


class ProviderError(AppError):
    def __init__(self, message: str = "Provider error", *, details=None) -> None:
        super().__init__(
            message,
            code="provider_error",
            status_code=502,
            details=details,
        )


class ProviderAuthError(AppError):
    def __init__(self, message: str = "Provider authentication failed", *, details=None) -> None:
        super().__init__(
            message,
            code="provider_error",
            status_code=502,
            details=details,
        )
