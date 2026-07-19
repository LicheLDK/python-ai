"""Organization / soft-tenant unit tests (T-16.01–T-16.05)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.constants import REDIS_KEY_AI_RATE_ORG, REDIS_KEY_AI_RATE_USER
from app.exceptions.domain import RateLimitError
from app.repositories.organization_repository import slugify
from app.services.ai_service import AiService
from app.services.organization_service import OrganizationService


@pytest.mark.unit
def test_slugify() -> None:
    assert slugify("Acme Corp!") == "acme-corp"
    assert slugify("  ") == "org"


@pytest.mark.unit
def test_effective_ai_quota_falls_back_to_settings() -> None:
    service = OrganizationService(
        MagicMock(),
        orgs=MagicMock(),
        cfg=SimpleNamespace(ai_rate_limit_max=60, ai_rate_limit_window_seconds=60),
    )
    org = SimpleNamespace(ai_rate_limit_max=None, ai_rate_limit_window_seconds=None)
    assert service.effective_ai_quota(org) == (60, 60)
    org2 = SimpleNamespace(ai_rate_limit_max=10, ai_rate_limit_window_seconds=30)
    assert service.effective_ai_quota(org2) == (10, 30)


@pytest.mark.unit
def test_ai_org_rate_limit_blocks(monkeypatch) -> None:
    redis = MagicMock()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    actor = SimpleNamespace(id=user_id, org_id=org_id)

    # user under limit, org over limit
    def _get(key):
        if "org" in key:
            return b"10"
        return b"1"

    redis.get.side_effect = _get

    org_repo = MagicMock()
    org_repo.get_by_id.return_value = SimpleNamespace(
        ai_rate_limit_max=10,
        ai_rate_limit_window_seconds=60,
    )
    monkeypatch.setattr(
        "app.services.ai_service.OrganizationRepository",
        lambda _session: org_repo,
    )

    service = AiService(
        MagicMock(),
        redis_client=redis,
        cfg=SimpleNamespace(
            ai_rate_limit_max=60,
            ai_rate_limit_window_seconds=60,
            ai_primary_provider="openai",
        ),
    )
    with pytest.raises(RateLimitError) as exc:
        service._assert_ai_rate_limit(actor)
    assert exc.value.details["scope"] == "organization"
    assert REDIS_KEY_AI_RATE_ORG.format(org_id=str(org_id))
    assert REDIS_KEY_AI_RATE_USER.format(user_id=str(user_id))


@pytest.mark.unit
def test_to_organization_read_effective() -> None:
    from datetime import UTC, datetime

    from app.schemas.organization import to_organization_read

    now = datetime.now(UTC)
    org = SimpleNamespace(
        id=uuid.uuid4(),
        name="Acme",
        slug="acme",
        status="active",
        ai_rate_limit_max=None,
        ai_rate_limit_window_seconds=None,
        branding={"logo_url": "https://example.com/logo.png"},
        created_at=now,
        updated_at=now,
    )
    read = to_organization_read(org, default_ai_max=60, default_ai_window=45)
    assert read.effective_ai_rate_limit_max == 60
    assert read.effective_ai_rate_limit_window_seconds == 45
    assert read.branding["logo_url"].startswith("https://")
