"""Documents migration check (T-3.01)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.database import engine


def test_documents_table_and_enum_exist() -> None:
    insp = inspect(engine)
    assert "documents" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("documents")}
    assert {
        "id",
        "owner_id",
        "filename",
        "mime_type",
        "size_bytes",
        "checksum_sha256",
        "storage_key",
        "page_count",
        "status",
        "created_at",
        "updated_at",
    } <= cols
    indexes = {i["name"] for i in insp.get_indexes("documents")}
    assert "ix_documents_owner_created" in indexes
    assert "ix_documents_status" in indexes

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'document_status'")
        ).first()
        assert row is not None
