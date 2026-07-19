"""Domain exceptions (T-0.05 / SDS §14)."""

from app.exceptions.base import AppError


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found", *, details=None) -> None:
        super().__init__(
            message,
            code="not_found",
            status_code=404,
            details=details,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", *, details=None) -> None:
        super().__init__(
            message,
            code="conflict",
            status_code=409,
            details=details,
        )


class ValidationAppError(AppError):
    def __init__(self, message: str = "Validation error", *, details=None) -> None:
        super().__init__(
            message,
            code="validation_error",
            status_code=422,
            details=details,
        )


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded", *, details=None) -> None:
        super().__init__(
            message,
            code="rate_limited",
            status_code=429,
            details=details,
        )


class PayloadTooLargeError(AppError):
    def __init__(self, message: str = "Payload too large", *, details=None) -> None:
        super().__init__(
            message,
            code="payload_too_large",
            status_code=413,
            details=details,
        )


class UnsupportedMediaTypeError(AppError):
    def __init__(
        self,
        message: str = "Unsupported media type",
        *,
        details=None,
    ) -> None:
        super().__init__(
            message,
            code="unsupported_media_type",
            status_code=415,
            details=details,
        )


class ProviderError(AppError):
    """Upstream LLM/OCR provider failure (SDS §9.6 → HTTP 502)."""

    def __init__(self, message: str = "Upstream provider error", *, details=None) -> None:
        super().__init__(
            message,
            code="provider_error",
            status_code=502,
            details=details,
        )
