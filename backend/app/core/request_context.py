"""Request-scoped context variables (core layer)."""

from __future__ import annotations

from contextvars import ContextVar, Token

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the request id for the current context, or empty string."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> Token[str]:
    """Bind request id into the context; caller must reset the token."""
    return _request_id_ctx.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    """Reset the request id context to the previous value."""
    _request_id_ctx.reset(token)
