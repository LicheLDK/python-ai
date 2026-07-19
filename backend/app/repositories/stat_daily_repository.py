"""StatDailyRepository — DB access only (T-7.01 / SDS §10.16)."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Any, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.stats import StatDaily


class StatDailyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def delete_for_date(
        self,
        *,
        day: date_type,
        metrics: Sequence[str],
    ) -> None:
        """Idempotent materialization: wipe the day's rows before re-insert."""
        stmt = delete(StatDaily).where(
            StatDaily.date == day,
            StatDaily.metric.in_(list(metrics)),
        )
        self._session.execute(stmt)
        self._session.flush()

    def add(
        self,
        *,
        day: date_type,
        metric: str,
        value: float,
        user_id: uuid.UUID | None = None,
        dimensions: dict[str, Any] | None = None,
        dim_key: str = "",
    ) -> StatDaily:
        row = StatDaily(
            id=uuid.uuid4(),
            date=day,
            metric=metric,
            user_id=user_id,
            dimensions=dimensions or {},
            dim_key=dim_key,
            value=value,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def query_daily(
        self,
        *,
        date_from: date_type,
        date_to: date_type,
        user_id: uuid.UUID | None,
        is_global: bool,
        metric: str | None = None,
    ) -> list[StatDaily]:
        filters = [StatDaily.date >= date_from, StatDaily.date <= date_to]
        if is_global:
            filters.append(StatDaily.user_id.is_(None))
        else:
            filters.append(StatDaily.user_id == user_id)
        if metric is not None:
            filters.append(StatDaily.metric == metric)
        stmt = (
            select(StatDaily)
            .where(*filters)
            .order_by(StatDaily.date.asc(), StatDaily.metric.asc())
        )
        return list(self._session.scalars(stmt).all())

    def query_monthly(
        self,
        *,
        date_from: date_type,
        date_to: date_type,
        user_id: uuid.UUID | None,
        is_global: bool,
        metric: str | None = None,
    ) -> list[tuple[str, str, float]]:
        """Return (month 'YYYY-MM', metric, value) rollups.

        ``*.avg`` metrics aggregate with AVG, others with SUM.
        """
        month_expr = func.to_char(StatDaily.date, "YYYY-MM")
        agg = func.sum(StatDaily.value)
        avg_agg = func.avg(StatDaily.value)

        filters = [StatDaily.date >= date_from, StatDaily.date <= date_to]
        if is_global:
            filters.append(StatDaily.user_id.is_(None))
        else:
            filters.append(StatDaily.user_id == user_id)
        if metric is not None:
            filters.append(StatDaily.metric == metric)

        out: list[tuple[str, str, float]] = []
        for use_avg in (False, True):
            metric_filter = (
                StatDaily.metric.like("%.avg")
                if use_avg
                else StatDaily.metric.not_like("%.avg")
            )
            stmt = (
                select(
                    month_expr.label("month"),
                    StatDaily.metric,
                    (avg_agg if use_avg else agg).label("value"),
                )
                .where(*filters, metric_filter)
                .group_by(month_expr, StatDaily.metric)
                .order_by(month_expr.asc(), StatDaily.metric.asc())
            )
            for month, m, value in self._session.execute(stmt).all():
                out.append((str(month), str(m), float(value or 0)))
        out.sort(key=lambda t: (t[0], t[1]))
        return out
