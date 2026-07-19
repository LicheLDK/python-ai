"""Storage backend factory (T-14.02) — local volume or S3-compatible."""

from __future__ import annotations

from functools import lru_cache

from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.ports import StoragePort
from app.adapters.s3_storage_adapter import S3StorageAdapter
from app.core.config import settings


@lru_cache(maxsize=1)
def get_storage() -> StoragePort:
    """Process-wide StoragePort selected by ``STORAGE_BACKEND``."""
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "s3":
        return S3StorageAdapter()
    if backend in {"local", "fs", "filesystem"}:
        return LocalStorageAdapter()
    raise ValueError(
        f"Unsupported STORAGE_BACKEND={settings.storage_backend!r}; "
        "use 'local' or 's3'"
    )


def reset_storage_cache() -> None:
    """Clear factory cache (tests)."""
    get_storage.cache_clear()
