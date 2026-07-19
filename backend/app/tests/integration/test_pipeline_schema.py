"""Pipeline schema migration check (T-6.01)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.database import engine


def test_pipeline_runs_table_and_enum_exist() -> None:
    insp = inspect(engine)
    assert "pipeline_runs" in set(insp.get_table_names())

    cols = {c["name"] for c in insp.get_columns("pipeline_runs")}
    assert {
        "id",
        "user_id",
        "document_id",
        "status",
        "stages",
        "ocr_job_id",
        "ai_request_id",
        "error",
        "created_at",
        "finished_at",
        "updated_at",
    } <= cols

    indexes = {i["name"] for i in insp.get_indexes("pipeline_runs")}
    assert "ix_pipeline_runs_user_created" in indexes
    assert "ix_pipeline_runs_status" in indexes

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT enumlabel FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'pipeline_run_status' "
                "ORDER BY enumsortorder"
            )
        ).fetchall()
    labels = [r[0] for r in rows]
    assert labels == ["queued", "running", "succeeded", "failed", "cancelled"]
