"""stat_daily schema migration check (T-7.01)."""

from __future__ import annotations

from sqlalchemy import inspect

from app.core.database import engine


def test_stat_daily_table_and_indexes_exist() -> None:
    insp = inspect(engine)
    assert "stat_daily" in set(insp.get_table_names())

    cols = {c["name"] for c in insp.get_columns("stat_daily")}
    assert {
        "id",
        "date",
        "metric",
        "user_id",
        "dimensions",
        "dim_key",
        "value",
        "created_at",
        "updated_at",
    } <= cols

    indexes = insp.get_indexes("stat_daily")
    names = {i["name"] for i in indexes}
    assert "ux_stat_daily_key" in names
    assert "ix_stat_daily_metric_date" in names
    assert "ix_stat_daily_user_date" in names
    unique_idx = next(i for i in indexes if i["name"] == "ux_stat_daily_key")
    assert unique_idx["unique"] is True
