"""Document API test suite (T-3.04) — 415/413/404/ownership + happy path."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.services.document_service as document_service_mod
from app.adapters.local_storage_adapter import LocalStorageAdapter
from app.core.deps import get_db
from app.main import app
from app.routers.documents import get_document_service
from app.services.document_service import DocumentService
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    admin_bearer_headers,
    login_access_token,
    register_user,
    unique_email,
)

pytestmark = [pytest.mark.api]


@pytest.fixture()
def client(tmp_path: Path):
    storage = LocalStorageAdapter(root=tmp_path)

    def _override(db: Session = Depends(get_db)) -> DocumentService:
        return DocumentService(db, storage=storage)

    app.dependency_overrides[get_document_service] = _override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_document_service, None)


def _user_headers(client: TestClient, *, prefix: str = "doc") -> dict[str, str]:
    email = unique_email(prefix)
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}


def _png_file(name: str = "sample.png", size: int = 64) -> dict:
    return {
        "file": (name, b"\x89PNG\r\n\x1a\n" + b"0" * size, "image/png"),
    }


def test_upload_list_get_delete_happy_path(client: TestClient) -> None:
    headers = _user_headers(client)
    created = client.post("/api/v1/documents", headers=headers, files=_png_file())
    assert created.status_code == 201, created.text
    doc_id = created.json()["id"]

    listed = client.get("/api/v1/documents", headers=headers)
    assert listed.status_code == 200
    assert any(i["id"] == doc_id for i in listed.json()["items"])

    detail = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "uploaded"

    assert client.delete(f"/api/v1/documents/{doc_id}", headers=headers).status_code == 204
    assert_error_envelope(
        client.get(f"/api/v1/documents/{doc_id}", headers=headers),
        status_code=404,
        code="not_found",
    )


def test_upload_415_unsupported_media(client: TestClient) -> None:
    headers = _user_headers(client)
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    res = client.post("/api/v1/documents", headers=headers, files=files)
    assert_error_envelope(res, status_code=415, code="unsupported_media_type")


def test_upload_413_payload_too_large(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(document_service_mod.settings, "upload_max_bytes", 32)
    headers = _user_headers(client)
    files = _png_file(size=200)
    res = client.post("/api/v1/documents", headers=headers, files=files)
    assert_error_envelope(res, status_code=413, code="payload_too_large")


def test_get_404_unknown_id(client: TestClient) -> None:
    headers = _user_headers(client)
    res = client.get(f"/api/v1/documents/{uuid.uuid4()}", headers=headers)
    assert_error_envelope(res, status_code=404, code="not_found")


def test_ownership_isolation(client: TestClient) -> None:
    owner = _user_headers(client, prefix="owner")
    other = _user_headers(client, prefix="other")

    created = client.post("/api/v1/documents", headers=owner, files=_png_file())
    assert created.status_code == 201, created.text
    doc_id = created.json()["id"]

    # Other user cannot read or delete
    assert_error_envelope(
        client.get(f"/api/v1/documents/{doc_id}", headers=other),
        status_code=403,
        code="forbidden",
    )
    assert_error_envelope(
        client.delete(f"/api/v1/documents/{doc_id}", headers=other),
        status_code=403,
        code="forbidden",
    )

    # Other user's list does not include owner doc
    listed = client.get("/api/v1/documents", headers=other)
    assert listed.status_code == 200
    assert all(i["id"] != doc_id for i in listed.json()["items"])

    # Owner still sees it
    owner_list = client.get("/api/v1/documents", headers=owner)
    assert any(i["id"] == doc_id for i in owner_list.json()["items"])


def test_admin_can_read_other_users_document(client: TestClient) -> None:
    owner = _user_headers(client, prefix="own2")
    admin_email = unique_email("adm-doc")
    register_user(client, email=admin_email)
    admin = admin_bearer_headers(admin_email)

    created = client.post("/api/v1/documents", headers=owner, files=_png_file())
    assert created.status_code == 201
    doc_id = created.json()["id"]

    detail = client.get(f"/api/v1/documents/{doc_id}", headers=admin)
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == doc_id


def test_documents_require_auth(client: TestClient) -> None:
    assert_error_envelope(
        client.get("/api/v1/documents"),
        status_code=401,
        code="unauthorized",
    )


def test_upload_empty_file_422(client: TestClient) -> None:
    headers = _user_headers(client)
    files = {"file": ("empty.png", b"", "image/png")}
    res = client.post("/api/v1/documents", headers=headers, files=files)
    assert_error_envelope(res, status_code=422, code="validation_error")
