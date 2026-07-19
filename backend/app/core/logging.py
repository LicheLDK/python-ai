"""Structured JSON logging setup (T-0.05)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.request_context import get_request_id


class JsonLogFormatter(logging.Formatter):
    """Emit one JSON object per log line (stdout)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        for key in ("method", "path", "status_code", "latency_ms", "client_ip"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    """Attach current request_id (if any) to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()  # type: ignore[attr-defined]
        return True


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger for JSON stdout. Idempotent-friendly."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)

    # Keep uvicorn access noise down; we emit our own access logs.
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False
