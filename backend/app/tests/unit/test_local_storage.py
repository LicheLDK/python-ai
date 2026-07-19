"""LocalStorageAdapter tests (T-3.02)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.local_storage_adapter import LocalStorageAdapter


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageAdapter:
    return LocalStorageAdapter(root=tmp_path)


def test_put_creates_file_on_disk(storage: LocalStorageAdapter, tmp_path: Path) -> None:
    doc_id = uuid.uuid4()
    key = storage.build_document_key(
        doc_id,
        at=datetime(2026, 7, 18, tzinfo=UTC),
    )
    assert key == f"documents/2026/07/{doc_id}/original.bin"

    payload = b"%PDF-1.4 fake"
    storage.put(key, payload)

    abs_path = storage.absolute_path(key)
    assert abs_path.is_file()
    assert abs_path.read_bytes() == payload
    assert storage.exists(key)
    assert storage.get(key) == payload
    assert str(abs_path).startswith(str(tmp_path.resolve()))


def test_delete_and_missing(storage: LocalStorageAdapter) -> None:
    key = storage.build_document_key(uuid.uuid4())
    storage.put(key, b"x")
    storage.delete(key)
    assert storage.exists(key) is False
    with pytest.raises(FileNotFoundError):
        storage.get(key)


def test_rejects_path_traversal(storage: LocalStorageAdapter) -> None:
    with pytest.raises(ValueError):
        storage.put("../etc/passwd", b"nope")
