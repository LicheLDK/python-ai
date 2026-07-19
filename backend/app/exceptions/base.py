"""Application error base hierarchy (T-0.05 / SDS §14)."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error mapped to the standard error envelope."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
