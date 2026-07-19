"""Stats API + materialize tests (T-7.06)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.constants import REDIS_KEY_STATS_SUMMARY
from app.core.database import SessionLocal
from app.core.redis import get_redis
from app.models.ai import AiProvider, AiRequestStatus, AiRequestType
from app.models.ocr import OcrJobStatus
from app.models.stats import (
    METRIC_AI_REQUESTS_COUNT,
    METRIC_AI_TOKENS_IN,
    METRIC_AUTH_LOGIN_FAILED,
    METRIC_OCR_JOBS_COUNT,
    METRIC_OCR_JOBS_FAILED,
)
from app.repositories.ai_request_repository import AiRequestRepository
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.ocr_job_repository import OcrJobRepository
from app.services.stats_service import StatsService
from app.tests.conftest import assert_error_envelope
from app.tests.helpers import (
    admin_bearer_headers,
    login_access_token,
    register_user,
    unique_email,
    user_id_by_email,
)

pytestmark = [pytest.mark.api]

TODAY = datetime.now(UTC).date()


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def _seed_activity(user_id: uuid.UUID) -> None:
    """Insert one succeeded + one failed OCR job and one AI request/usage."""
    now = datetime.now(UTC)
    with SessionLocal() as db:
        docs = DocumentRepository(db)
        doc = docs.create(
            document_id=uuid.uuid4(),
            owner_id=user_id,
            filename="stats.png",
            mime_type="image/png",
            size_bytes=10,
            checksum_sha256="0" * 64,
            storage_key=f"documents/test/{uuid.uuid4()}/original.bin",
            page_count=1,
        )
        jobs = OcrJobRepository(db)
        ok = jobs.create(document_id=doc.id, user_id=user_id)
        jobs.mark_running(ok, started_at=now - timedelta(seconds=3))
        jobs.mark_succeeded(ok, finished_at=now)
        bad = jobs.create(document_id=doc.id, user_id=user_id)
        jobs.mark_running(bad, started_at=now - timedelta(seconds=1))
        jobs.mark_failed(bad, finished_at=now, error="boom")

        reqs = AiRequestRepository(db)
        req = reqs.create(
            user_id=user_id,
            provider=AiProvider.openai,
            model="m",
            request_type=AiRequestType.chat,
            status=AiRequestStatus.succeeded,
        )
        AiUsageRepository(db).create(
            request_id=req.id,
            tokens_in=7,
            tokens_out=5,
            latency_ms=10,
            cost_estimate=0.001,
        )
        db.commit()


def _materialize_today() -> None:
    with SessionLocal() as db:
        StatsService(db).materialize_day(TODAY)
        db.commit()


def _user(client: TestClient, prefix: str = "stats") -> tuple[dict[str, str], uuid.UUID]:
    email = unique_email(prefix)
    register_user(client, email=email)
    token = login_access_token(client, email=email)
    return {"Authorization": f"Bearer {token}"}, user_id_by_email(email)


def test_daily_self_scope_after_materialize(client: TestClient) -> None:
    headers, user_id = _user(client)
    _seed_activity(user_id)
    _materialize_today()

    res = client.get(
        "/api/v1/stats/daily",
        headers=headers,
        params={"from": TODAY.isoformat(), "to": TODAY.isoformat()},
    )
    assert res.status_code == 200, res.text
    points = res.json()["points"]
    by_metric = {p["metric"]: p["value"] for p in points}
    assert by_metric.get(METRIC_OCR_JOBS_COUNT) == 2
    assert by_metric.get(METRIC_OCR_JOBS_FAILED) == 1
    assert by_metric.get(METRIC_AI_REQUESTS_COUNT) == 1
    assert by_metric.get(METRIC_AI_TOKENS_IN) == 7


def test_daily_global_scope_requires_admin(client: TestClient) -> None:
    headers, _ = _user(client, prefix="stats-noadm")
    res = client.get(
        "/api/v1/stats/daily",
        headers=headers,
        params={
            "from": TODAY.isoformat(),
            "to": TODAY.isoformat(),
            "scope": "global",
        },
    )
    assert_error_envelope(res, status_code=403, code="forbidden")


def test_daily_global_scope_admin_sees_login_failures(client: TestClient) -> None:
    # Force a failed login → audit row → materialize → global metric.
    email = unique_email("stats-fail")
    register_user(client, email=email)
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Wrong-P@ss-1!"},
    )
    assert bad.status_code == 401

    _materialize_today()

    admin_email = unique_email("stats-admin")
    register_user(client, email=admin_email)
    admin_headers = admin_bearer_headers(admin_email)
    res = client.get(
        "/api/v1/stats/daily",
        headers=admin_headers,
        params={
            "from": TODAY.isoformat(),
            "to": TODAY.isoformat(),
            "scope": "global",
            "metric": METRIC_AUTH_LOGIN_FAILED,
        },
    )
    assert res.status_code == 200, res.text
    points = res.json()["points"]
    assert len(points) == 1
    assert points[0]["value"] >= 1


def test_monthly_rollup(client: TestClient) -> None:
    headers, user_id = _user(client, prefix="stats-mo")
    _seed_activity(user_id)
    _materialize_today()

    month = TODAY.strftime("%Y-%m")
    res = client.get(
        "/api/v1/stats/monthly",
        headers=headers,
        params={"from_month": month, "to_month": month},
    )
    assert res.status_code == 200, res.text
    points = res.json()["points"]
    by_metric = {p["metric"]: p for p in points}
    assert by_metric[METRIC_OCR_JOBS_COUNT]["month"] == month
    assert by_metric[METRIC_OCR_JOBS_COUNT]["value"] == 2


def test_monthly_invalid_month_422(client: TestClient) -> None:
    headers, _ = _user(client, prefix="stats-badmo")
    res = client.get(
        "/api/v1/stats/monthly",
        headers=headers,
        params={"from_month": "2026/07", "to_month": "2026-07"},
    )
    assert_error_envelope(res, status_code=422, code="validation_error")


def test_summary_live_and_cached(client: TestClient) -> None:
    headers, user_id = _user(client, prefix="stats-sum")
    redis = get_redis()
    cache_key = REDIS_KEY_STATS_SUMMARY.format(
        user_id=str(user_id),
        day=TODAY.isoformat(),
    )
    redis.delete(cache_key)
    try:
        _seed_activity(user_id)
        res = client.get("/api/v1/stats/summary", headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["ocr_jobs_today"] == 2
        assert body["ai_requests_today"] == 1
        assert body["tokens_today"] == 12
        assert 0 < body["error_rate_today"] < 1
        # Cached now (T-7.05) — same response served from Redis.
        assert redis.get(cache_key) is not None
        res2 = client.get("/api/v1/stats/summary", headers=headers)
        assert res2.json() == body
    finally:
        redis.delete(cache_key)


def test_export_csv(client: TestClient) -> None:
    headers, user_id = _user(client, prefix="stats-csv")
    _seed_activity(user_id)
    _materialize_today()

    res = client.get(
        "/api/v1/stats/export",
        headers=headers,
        params={"from": TODAY.isoformat(), "to": TODAY.isoformat()},
    )
    assert res.status_code == 200, res.text
    assert "text/csv" in res.headers["content-type"]
    lines = res.text.strip().splitlines()
    assert lines[0] == "date,metric,value,scope"
    assert any(METRIC_OCR_JOBS_COUNT in line for line in lines[1:])


def test_materialize_idempotent(client: TestClient) -> None:
    headers, user_id = _user(client, prefix="stats-idem")
    _seed_activity(user_id)
    _materialize_today()
    _materialize_today()  # second run must not duplicate

    res = client.get(
        "/api/v1/stats/daily",
        headers=headers,
        params={
            "from": TODAY.isoformat(),
            "to": TODAY.isoformat(),
            "metric": METRIC_OCR_JOBS_COUNT,
        },
    )
    points = res.json()["points"]
    assert len(points) == 1
    assert points[0]["value"] == 2
