"""AiRequestRepository — DB access only (T-5.06 / SDS §10.12)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai import AiProvider, AiRequest, AiRequestStatus, AiRequestType


class AiRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, request_id: uuid.UUID) -> AiRequest | None:
        return self._session.get(AiRequest, request_id)

    def create(
        self,
        *,
        user_id: uuid.UUID,
        provider: AiProvider,
        model: str,
        request_type: AiRequestType,
        status: AiRequestStatus,
        prompt_id: uuid.UUID | None = None,
        input_ref: dict[str, Any] | None = None,
        output_ref: dict[str, Any] | None = None,
        error: str | None = None,
        request_id: uuid.UUID | None = None,
    ) -> AiRequest:
        row = AiRequest(
            id=request_id or uuid.uuid4(),
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_id=prompt_id,
            request_type=request_type,
            input_ref=input_ref or {},
            output_ref=output_ref,
            status=status,
            error=error,
        )
        self._session.add(row)
        self._session.flush()
        return row
