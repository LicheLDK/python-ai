"""OcrResultRepository — DB access only (T-4.05 / SDS §10.10)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ocr import OcrResult


class OcrResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_job(self, job_id: uuid.UUID) -> list[OcrResult]:
        stmt = (
            select(OcrResult)
            .where(OcrResult.job_id == job_id)
            .order_by(OcrResult.page.asc())
        )
        return list(self._session.scalars(stmt).all())

    def create(
        self,
        *,
        job_id: uuid.UUID,
        page: int,
        text: str,
        boxes: list[Any] | None = None,
        confidence: float | None = None,
        result_id: uuid.UUID | None = None,
    ) -> OcrResult:
        conf: Decimal | None = None
        if confidence is not None:
            conf = Decimal(str(round(float(confidence), 4)))
        row = OcrResult(
            id=result_id or uuid.uuid4(),
            job_id=job_id,
            page=page,
            text=text,
            boxes=boxes or [],
            confidence=conf,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def delete_for_job(self, job_id: uuid.UUID) -> None:
        for row in self.list_for_job(job_id):
            self._session.delete(row)
        self._session.flush()
