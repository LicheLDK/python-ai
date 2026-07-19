"""S3 StoragePort adapter unit tests (T-14.01 / T-14.03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.adapters.s3_storage_adapter import S3StorageAdapter
from app.adapters.storage_factory import get_storage, reset_storage_cache
import app.adapters.storage_factory as storage_factory


def _client_error(code: str, status: int = 404) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": code},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        "GetObject",
    )


@pytest.fixture
def s3() -> tuple[S3StorageAdapter, MagicMock]:
    client = MagicMock()
    adapter = S3StorageAdapter(bucket="aisaas", client=client)
    return adapter, client


@pytest.mark.unit
def test_build_document_key(s3: tuple[S3StorageAdapter, MagicMock]) -> None:
    adapter, _ = s3
    doc_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    key = adapter.build_document_key(
        doc_id,
        at=datetime(2026, 7, 19, tzinfo=UTC),
    )
    assert key == "documents/2026/07/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/original.bin"


@pytest.mark.unit
def test_put_get_exists_delete(s3: tuple[S3StorageAdapter, MagicMock]) -> None:
    adapter, client = s3
    key = "documents/2026/07/x/original.bin"
    body = MagicMock()
    body.read.return_value = b"hello"
    client.get_object.return_value = {"Body": body}

    adapter.put(key, b"hello")
    client.put_object.assert_called_once_with(
        Bucket="aisaas",
        Key=key,
        Body=b"hello",
    )

    assert adapter.get(key) == b"hello"
    client.get_object.assert_called_with(Bucket="aisaas", Key=key)

    assert adapter.exists(key) is True
    client.head_object.assert_called_with(Bucket="aisaas", Key=key)

    adapter.delete(key)
    client.delete_object.assert_called_once_with(Bucket="aisaas", Key=key)


@pytest.mark.unit
def test_get_missing_raises(s3: tuple[S3StorageAdapter, MagicMock]) -> None:
    adapter, client = s3
    client.get_object.side_effect = _client_error("NoSuchKey")
    with pytest.raises(FileNotFoundError):
        adapter.get("documents/missing.bin")


@pytest.mark.unit
def test_exists_false_on_404(s3: tuple[S3StorageAdapter, MagicMock]) -> None:
    adapter, client = s3
    client.head_object.side_effect = _client_error("404", status=404)
    assert adapter.exists("documents/missing.bin") is False


@pytest.mark.unit
def test_rejects_path_traversal(s3: tuple[S3StorageAdapter, MagicMock]) -> None:
    adapter, _ = s3
    with pytest.raises(ValueError):
        adapter.put("../etc/passwd", b"nope")


@pytest.mark.unit
def test_factory_local_by_default(monkeypatch, tmp_path) -> None:
    reset_storage_cache()
    monkeypatch.setattr(
        storage_factory,
        "settings",
        SimpleNamespace(storage_backend="local", storage_path=str(tmp_path)),
    )
    monkeypatch.setattr(
        "app.adapters.local_storage_adapter.settings",
        SimpleNamespace(storage_path=str(tmp_path)),
    )
    storage = get_storage()
    assert isinstance(storage, LocalStorageAdapter)
    reset_storage_cache()


@pytest.mark.unit
def test_factory_s3_backend(monkeypatch) -> None:
    reset_storage_cache()
    monkeypatch.setattr(
        storage_factory,
        "settings",
        SimpleNamespace(storage_backend="s3"),
    )
    fake = MagicMock(spec=S3StorageAdapter)
    monkeypatch.setattr(
        storage_factory,
        "S3StorageAdapter",
        lambda: fake,
    )
    assert get_storage() is fake
    reset_storage_cache()


@pytest.mark.unit
def test_factory_rejects_unknown(monkeypatch) -> None:
    reset_storage_cache()
    monkeypatch.setattr(
        storage_factory,
        "settings",
        SimpleNamespace(storage_backend="gcs"),
    )
    with pytest.raises(ValueError, match="Unsupported STORAGE_BACKEND"):
        get_storage()
    reset_storage_cache()
