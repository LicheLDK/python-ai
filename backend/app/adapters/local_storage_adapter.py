"""Local filesystem StoragePort (T-3.02 / SDS ADR-014, §10.20)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.adapters.ports import StoragePort
from app.core.config import settings


class LocalStorageAdapter:
    """Stores objects under ``STORAGE_PATH`` using relative ``storage_key`` paths."""

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root if root is not None else settings.storage_path).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def build_document_key(
        self,
        document_id: uuid.UUID,
        *,
        at: datetime | None = None,
    ) -> str:
        when = at or datetime.now(UTC)
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        else:
            when = when.astimezone(UTC)
        return f"documents/{when:%Y}/{when:%m}/{document_id}/original.bin"

    def put(self, storage_key: str, data: bytes) -> None:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, storage_key: str) -> bytes:
        path = self._resolve(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path.read_bytes()

    def exists(self, storage_key: str) -> bool:
        return self._resolve(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.is_file():
            path.unlink()

    def absolute_path(self, storage_key: str) -> Path:
        """Absolute filesystem path for debugging/tests."""
        return self._resolve(storage_key)

    def _resolve(self, storage_key: str) -> Path:
        key = storage_key.replace("\\", "/").lstrip("/")
        if not key or key.startswith("..") or "/../" in f"/{key}/":
            raise ValueError(f"Invalid storage_key: {storage_key!r}")
        path = (self._root / key).resolve()
        if path != self._root and self._root not in path.parents:
            raise ValueError(f"storage_key escapes root: {storage_key!r}")
        return path


def get_local_storage() -> StoragePort:
    """Factory for DI (DocumentService will use this in T-3.03)."""
    return LocalStorageAdapter()
