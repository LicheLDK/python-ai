"""Shared API schemas — error envelope (T-0.05) + pagination (T-2.03)."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorEnvelope(BaseModel):
    """Standard error response body for all API failures."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable summary")
    details: Any | None = Field(default=None, description="Optional structured details")
    request_id: str = Field(..., description="Correlation id from X-Request-ID")


class Page(BaseModel, Generic[T]):
    """Offset pagination response body (SDS §9)."""

    items: list[T]
    page: int
    page_size: int
    total: int
