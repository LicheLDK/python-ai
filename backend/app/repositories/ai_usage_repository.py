"""AiUsageRepository — DB access only (T-5.06 / T-10.01 / SDS §10.13)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai import AiProvider, AiRequest, AiUsage
from app.utils.pagination import PageParams


class AiUsageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        request_id: uuid.UUID,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        cost_estimate: float,
        usage_id: uuid.UUID | None = None,
    ) -> AiUsage:
        row = AiUsage(
            id=usage_id or uuid.uuid4(),
            request_id=request_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_estimate=cost_estimate,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_joined(
        self,
        *,
        page: PageParams,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        provider: AiProvider | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return joined usage+request rows as plain dicts for admin DTO mapping."""
        filters: list = []
        if date_from is not None:
            filters.append(AiUsage.created_at >= date_from)
        if date_to is not None:
            filters.append(AiUsage.created_at <= date_to)
        if provider is not None:
            filters.append(AiRequest.provider == provider)
        if user_id is not None:
            filters.append(AiRequest.user_id == user_id)

        base = (
            select(AiUsage, AiRequest)
            .join(AiRequest, AiRequest.id == AiUsage.request_id)
            .order_by(AiUsage.created_at.desc())
        )
        count_base = (
            select(func.count())
            .select_from(AiUsage)
            .join(AiRequest, AiRequest.id == AiUsage.request_id)
        )
        if filters:
            base = base.where(*filters)
            count_base = count_base.where(*filters)

        total = int(self._session.scalar(count_base) or 0)
        rows = self._session.execute(
            base.offset(page.offset).limit(page.limit)
        ).all()

        out: list[dict[str, Any]] = []
        for usage, req in rows:
            provider_val = (
                req.provider.value
                if hasattr(req.provider, "value")
                else str(req.provider)
            )
            type_val = (
                req.request_type.value
                if hasattr(req.request_type, "value")
                else str(req.request_type)
            )
            status_val = (
                req.status.value if hasattr(req.status, "value") else str(req.status)
            )
            out.append(
                {
                    "id": usage.id,
                    "request_id": usage.request_id,
                    "user_id": req.user_id,
                    "provider": provider_val,
                    "model": req.model,
                    "request_type": type_val,
                    "status": status_val,
                    "tokens_in": int(usage.tokens_in or 0),
                    "tokens_out": int(usage.tokens_out or 0),
                    "latency_ms": int(usage.latency_ms or 0),
                    "cost_estimate": float(usage.cost_estimate or 0),
                    "created_at": usage.created_at,
                }
            )
        return out, total
