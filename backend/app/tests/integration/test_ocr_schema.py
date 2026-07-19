"""OCR schema migration check (T-4.01)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.database import engine


def test_ocr_tables_and_enum_exist() -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    assert "ocr_jobs" in tables
    assert "ocr_results" in tables

    job_cols = {c["name"] for c in insp.get_columns("ocr_jobs")}
    assert {
        "id",
        "document_id",
        "user_id",
        "status",
        "options",
        "error",
        "attempt_count",
        "started_at",
        "finished_at",
        "created_at",
        "updated_at",
    } <= job_cols

    result_cols = {c["name"] for c in insp.get_columns("ocr_results")}
    assert {
        "id",
        "job_id",
        "page",
        "text",
        "boxes",
        "confidence",
        "created_at",
    } <= result_cols

    job_indexes = {i["name"] for i in insp.get_indexes("ocr_jobs")}
    assert "ix_ocr_jobs_user_created" in job_indexes
    assert "ix_ocr_jobs_status_created" in job_indexes
    assert "ix_ocr_jobs_document_id" in job_indexes

    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT 1 FROM pg_type WHERE typname = 'ocr_job_status'")
            ).first()
            is not None
        )
        # unique(job_id, page)
        uq = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_ocr_results_job_page'
                """
            )
        ).first()
        assert uq is not None
