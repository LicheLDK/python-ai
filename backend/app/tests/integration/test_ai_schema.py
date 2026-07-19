"""AI schema migration check (T-5.01)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from app.core.database import engine


def test_ai_tables_enums_and_constraints_exist() -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    assert "ai_prompts" in tables
    assert "ai_requests" in tables
    assert "ai_usages" in tables

    prompt_cols = {c["name"] for c in insp.get_columns("ai_prompts")}
    assert {
        "id",
        "name",
        "version",
        "template",
        "variables_schema",
        "active",
        "created_by",
        "created_at",
        "updated_at",
    } <= prompt_cols

    request_cols = {c["name"] for c in insp.get_columns("ai_requests")}
    assert {
        "id",
        "user_id",
        "provider",
        "model",
        "prompt_id",
        "request_type",
        "input_ref",
        "output_ref",
        "status",
        "error",
        "created_at",
    } <= request_cols

    usage_cols = {c["name"] for c in insp.get_columns("ai_usages")}
    assert {
        "id",
        "request_id",
        "tokens_in",
        "tokens_out",
        "latency_ms",
        "cost_estimate",
        "created_at",
    } <= usage_cols

    request_indexes = {i["name"] for i in insp.get_indexes("ai_requests")}
    assert "ix_ai_requests_user_created" in request_indexes
    assert "ix_ai_requests_provider_created" in request_indexes

    usage_indexes = {i["name"] for i in insp.get_indexes("ai_usages")}
    assert "ix_ai_usages_created_at" in usage_indexes

    with engine.connect() as conn:
        for typname in ("ai_provider", "ai_request_type", "ai_request_status"):
            assert (
                conn.execute(
                    text("SELECT 1 FROM pg_type WHERE typname = :t"),
                    {"t": typname},
                ).first()
                is not None
            )

        assert (
            conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_ai_prompts_name_version'
                    """
                )
            ).first()
            is not None
        )
        assert (
            conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_indexes
                    WHERE indexname = 'uq_ai_prompts_name_active'
                    """
                )
            ).first()
            is not None
        )
        assert (
            conn.execute(
                text(
                    """
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_ai_usages_request_id'
                    """
                )
            ).first()
            is not None
        )
