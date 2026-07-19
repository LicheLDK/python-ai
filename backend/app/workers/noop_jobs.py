"""No-op ARQ jobs used to verify the worker/queue path (T-4.02)."""

from __future__ import annotations

from typing import Any


async def noop_job(ctx: dict[str, Any], message: str = "ping") -> dict[str, Any]:
    """Minimal job: proves enqueue → worker consume → result round-trip."""
    return {"ok": True, "message": message}
