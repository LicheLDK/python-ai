"""Statistics use cases (T-7.02 materialize / T-7.03 queries / T-7.04 CSV / T-7.05 cache)."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, date as date_type, datetime, time, timedelta

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.constants import REDIS_KEY_STATS_SUMMARY
from app.core.redis import get_redis
from app.exceptions.auth import ForbiddenError
from app.exceptions.domain import ValidationAppError
from app.models.ai import AiRequest, AiRequestStatus, AiUsage
from app.models.audit import AuditLog
from app.models.ocr import OcrJob, OcrJobStatus
from app.models.pipeline import PipelineRun
from app.models.stats import (
    ALL_METRICS,
    METRIC_AI_COST_ESTIMATE,
    METRIC_AI_REQUESTS_COUNT,
    METRIC_AI_TOKENS_IN,
    METRIC_AI_TOKENS_OUT,
    METRIC_AUTH_LOGIN_FAILED,
    METRIC_OCR_JOBS_COUNT,
    METRIC_OCR_JOBS_FAILED,
    METRIC_OCR_LATENCY_AVG,
    METRIC_PIPELINE_RUNS_COUNT,
    StatDaily,
)
from app.models.user import User, UserRole
from app.repositories.stat_daily_repository import StatDailyRepository

AUDIT_ACTION_LOGIN_FAILED = "auth.login.failed"


def _day_window(day: date_type) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    return start, start + timedelta(days=1)


class StatsService:
    def __init__(
        self,
        session: Session,
        *,
        stats: StatDailyRepository | None = None,
        redis_client: redis.Redis | None = None,
        cfg: Settings | None = None,
    ) -> None:
        self._session = session
        self._stats = stats or StatDailyRepository(session)
        self._redis = redis_client
        self._settings = cfg or settings

    # ------------------------------------------------------------------ T-7.02
    def materialize_day(self, day: date_type) -> dict[str, int]:
        """Delete + rebuild all metric rows for one UTC day. Idempotent.

        Caller owns the commit.
        """
        start, end = _day_window(day)
        self._stats.delete_for_date(day=day, metrics=ALL_METRICS)
        inserted = 0

        # --- OCR: count / failed / latency avg (per user + global) ---
        ocr_rows = self._session.execute(
            select(
                OcrJob.user_id,
                func.count(),
                func.count().filter(OcrJob.status == OcrJobStatus.failed),
                func.avg(
                    func.extract("epoch", OcrJob.finished_at - OcrJob.started_at) * 1000
                ).filter(
                    OcrJob.status == OcrJobStatus.succeeded,
                    OcrJob.started_at.isnot(None),
                    OcrJob.finished_at.isnot(None),
                ),
            )
            .where(OcrJob.created_at >= start, OcrJob.created_at < end)
            .group_by(OcrJob.user_id)
        ).all()
        inserted += self._insert_grouped(
            day,
            ocr_rows,
            [
                (METRIC_OCR_JOBS_COUNT, "sum"),
                (METRIC_OCR_JOBS_FAILED, "sum"),
                (METRIC_OCR_LATENCY_AVG, "avg"),
            ],
        )

        # --- AI: request count (per user + global) ---
        ai_req_rows = self._session.execute(
            select(AiRequest.user_id, func.count())
            .where(AiRequest.created_at >= start, AiRequest.created_at < end)
            .group_by(AiRequest.user_id)
        ).all()
        inserted += self._insert_grouped(
            day,
            ai_req_rows,
            [(METRIC_AI_REQUESTS_COUNT, "sum")],
        )

        # --- AI: tokens / cost from usages (per user + global) ---
        ai_usage_rows = self._session.execute(
            select(
                AiRequest.user_id,
                func.coalesce(func.sum(AiUsage.tokens_in), 0),
                func.coalesce(func.sum(AiUsage.tokens_out), 0),
                func.coalesce(func.sum(AiUsage.cost_estimate), 0),
            )
            .join(AiRequest, AiRequest.id == AiUsage.request_id)
            .where(AiUsage.created_at >= start, AiUsage.created_at < end)
            .group_by(AiRequest.user_id)
        ).all()
        inserted += self._insert_grouped(
            day,
            ai_usage_rows,
            [
                (METRIC_AI_TOKENS_IN, "sum"),
                (METRIC_AI_TOKENS_OUT, "sum"),
                (METRIC_AI_COST_ESTIMATE, "sum"),
            ],
        )

        # --- Pipelines: run count (per user + global) ---
        pipe_rows = self._session.execute(
            select(PipelineRun.user_id, func.count())
            .where(PipelineRun.created_at >= start, PipelineRun.created_at < end)
            .group_by(PipelineRun.user_id)
        ).all()
        inserted += self._insert_grouped(
            day,
            pipe_rows,
            [(METRIC_PIPELINE_RUNS_COUNT, "sum")],
        )

        # --- Auth login failures: global only (admin metric) ---
        failed_logins = int(
            self._session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(
                    AuditLog.action == AUDIT_ACTION_LOGIN_FAILED,
                    AuditLog.created_at >= start,
                    AuditLog.created_at < end,
                )
            )
            or 0
        )
        if failed_logins > 0:
            self._stats.add(
                day=day,
                metric=METRIC_AUTH_LOGIN_FAILED,
                value=float(failed_logins),
                user_id=None,
            )
            inserted += 1

        return {"date": day.isoformat(), "inserted": inserted}

    def _insert_grouped(
        self,
        day: date_type,
        rows: list,
        metrics: list[tuple[str, str]],
    ) -> int:
        """Insert per-user rows + one global rollup per metric.

        ``rows``: (user_id, v1, v2, ...) aligned with ``metrics`` order.
        ``avg`` metrics roll up globally as the average of user averages
        weighted equally (approximation, fine for dashboards).
        """
        inserted = 0
        totals: list[float] = [0.0] * len(metrics)
        avg_parts: list[list[float]] = [[] for _ in metrics]
        for row in rows:
            user_id = row[0]
            for idx, (metric, kind) in enumerate(metrics):
                raw = row[idx + 1]
                if raw is None:
                    continue
                value = float(raw)
                if kind == "avg":
                    avg_parts[idx].append(value)
                else:
                    totals[idx] += value
                self._stats.add(
                    day=day,
                    metric=metric,
                    value=value,
                    user_id=user_id,
                )
                inserted += 1
        for idx, (metric, kind) in enumerate(metrics):
            if kind == "avg":
                if not avg_parts[idx]:
                    continue
                value = sum(avg_parts[idx]) / len(avg_parts[idx])
            else:
                if not rows:
                    continue
                value = totals[idx]
            self._stats.add(day=day, metric=metric, value=value, user_id=None)
            inserted += 1
        return inserted

    # ------------------------------------------------------------------ T-7.03
    def daily(
        self,
        *,
        actor: User,
        date_from: date_type,
        date_to: date_type,
        metric: str | None = None,
        scope: str = "self",
    ) -> list[StatDaily]:
        is_global = self._check_scope(actor, scope)
        if date_from > date_to:
            raise ValidationAppError("`from` must be <= `to`")
        return self._stats.query_daily(
            date_from=date_from,
            date_to=date_to,
            user_id=actor.id,
            is_global=is_global,
            metric=metric,
        )

    def monthly(
        self,
        *,
        actor: User,
        from_month: str,
        to_month: str,
        metric: str | None = None,
        scope: str = "self",
    ) -> list[tuple[str, str, float]]:
        is_global = self._check_scope(actor, scope)
        start = self._parse_month(from_month)
        end_first = self._parse_month(to_month)
        if start > end_first:
            raise ValidationAppError("`from_month` must be <= `to_month`")
        # Inclusive end month → last day of that month.
        if end_first.month == 12:
            end = date_type(end_first.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date_type(end_first.year, end_first.month + 1, 1) - timedelta(days=1)
        return self._stats.query_monthly(
            date_from=start,
            date_to=end,
            user_id=actor.id,
            is_global=is_global,
            metric=metric,
        )

    def summary(self, *, actor: User) -> dict[str, float]:
        """Live KPI for today (self scope) with optional 5m Redis cache (T-7.05)."""
        today = datetime.now(UTC).date()
        cache_key = REDIS_KEY_STATS_SUMMARY.format(
            user_id=str(actor.id),
            day=today.isoformat(),
        )
        redis_client = self._redis
        if redis_client is not None:
            try:
                cached = redis_client.get(cache_key)
            except redis.RedisError:
                cached = None
            if cached:
                try:
                    return json.loads(cached)
                except (ValueError, TypeError):
                    pass

        start, end = _day_window(today)
        ocr_count, ocr_failed = self._session.execute(
            select(
                func.count(),
                func.count().filter(OcrJob.status == OcrJobStatus.failed),
            ).where(
                OcrJob.user_id == actor.id,
                OcrJob.created_at >= start,
                OcrJob.created_at < end,
            )
        ).one()
        ai_count, ai_failed = self._session.execute(
            select(
                func.count(),
                func.count().filter(AiRequest.status == AiRequestStatus.failed),
            ).where(
                AiRequest.user_id == actor.id,
                AiRequest.created_at >= start,
                AiRequest.created_at < end,
            )
        ).one()
        tokens = float(
            self._session.scalar(
                select(
                    func.coalesce(func.sum(AiUsage.tokens_in + AiUsage.tokens_out), 0)
                )
                .select_from(AiUsage)
                .join(AiRequest, AiRequest.id == AiUsage.request_id)
                .where(
                    AiRequest.user_id == actor.id,
                    AiUsage.created_at >= start,
                    AiUsage.created_at < end,
                )
            )
            or 0
        )
        total = int(ocr_count) + int(ai_count)
        failures = int(ocr_failed) + int(ai_failed)
        result = {
            "ocr_jobs_today": int(ocr_count),
            "ai_requests_today": int(ai_count),
            "tokens_today": tokens,
            "error_rate_today": (failures / total) if total else 0.0,
        }
        if redis_client is not None:
            try:
                redis_client.setex(
                    cache_key,
                    int(self._settings.stats_summary_cache_seconds),
                    json.dumps(result),
                )
            except redis.RedisError:
                pass
        return result

    # ------------------------------------------------------------------ T-7.04
    def export_csv(
        self,
        *,
        actor: User,
        date_from: date_type,
        date_to: date_type,
        metric: str | None = None,
        scope: str = "self",
    ) -> str:
        rows = self.daily(
            actor=actor,
            date_from=date_from,
            date_to=date_to,
            metric=metric,
            scope=scope,
        )
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(["date", "metric", "value", "scope"])
        scope_label = "global" if scope == "global" else "self"
        for row in rows:
            writer.writerow(
                [row.date.isoformat(), row.metric, float(row.value), scope_label]
            )
        return buf.getvalue()

    # ------------------------------------------------------------------ helpers
    def _check_scope(self, actor: User, scope: str) -> bool:
        """Return is_global; global requires admin."""
        cleaned = (scope or "self").strip().lower()
        if cleaned not in {"self", "global"}:
            raise ValidationAppError(
                "Invalid scope",
                details={"allowed": ["self", "global"]},
            )
        if cleaned == "global":
            if not self._is_admin(actor):
                raise ForbiddenError("Global scope requires admin role")
            return True
        return False

    @staticmethod
    def _parse_month(value: str) -> date_type:
        try:
            parsed = datetime.strptime(value.strip(), "%Y-%m")
        except (ValueError, AttributeError) as exc:
            raise ValidationAppError(
                "Invalid month format (expected YYYY-MM)",
                details={"value": value},
            ) from exc
        return date_type(parsed.year, parsed.month, 1)

    @staticmethod
    def _is_admin(user: User) -> bool:
        role = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return role == UserRole.admin.value


def get_stats_redis() -> redis.Redis:
    return get_redis()
