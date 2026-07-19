"""AiPromptRepository — DB access only (T-5.05 / SDS §10.11)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.ai import AiPrompt
from app.utils.pagination import PageParams


class AiPromptRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, prompt_id: uuid.UUID) -> AiPrompt | None:
        return self._session.get(AiPrompt, prompt_id)

    def get_by_name_version(self, name: str, version: int) -> AiPrompt | None:
        stmt = select(AiPrompt).where(
            AiPrompt.name == name,
            AiPrompt.version == version,
        )
        return self._session.scalars(stmt).first()

    def get_active_by_name(self, name: str) -> AiPrompt | None:
        stmt = select(AiPrompt).where(
            AiPrompt.name == name,
            AiPrompt.active.is_(True),
        )
        return self._session.scalars(stmt).first()

    def max_version(self, name: str) -> int:
        stmt = select(func.max(AiPrompt.version)).where(AiPrompt.name == name)
        value = self._session.scalar(stmt)
        return int(value or 0)

    def list(
        self,
        *,
        page: PageParams,
        name: str | None = None,
        active: bool | None = None,
    ) -> tuple[list[AiPrompt], int]:
        filters = []
        if name is not None:
            filters.append(AiPrompt.name == name)
        if active is not None:
            filters.append(AiPrompt.active.is_(active))

        count_stmt = select(func.count()).select_from(AiPrompt)
        list_stmt = select(AiPrompt).order_by(
            AiPrompt.name.asc(),
            AiPrompt.version.desc(),
        )
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = int(self._session.scalar(count_stmt) or 0)
        rows = list(
            self._session.scalars(
                list_stmt.offset(page.offset).limit(page.limit)
            ).all()
        )
        return rows, total

    def create(
        self,
        *,
        name: str,
        version: int,
        template: str,
        variables_schema: dict[str, Any] | None = None,
        active: bool = False,
        created_by: uuid.UUID | None = None,
        prompt_id: uuid.UUID | None = None,
    ) -> AiPrompt:
        row = AiPrompt(
            id=prompt_id or uuid.uuid4(),
            name=name,
            version=version,
            template=template,
            variables_schema=variables_schema or {},
            active=active,
            created_by=created_by,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def deactivate_active_for_name(self, name: str) -> None:
        stmt = (
            update(AiPrompt)
            .where(AiPrompt.name == name, AiPrompt.active.is_(True))
            .values(active=False)
        )
        self._session.execute(stmt)
        self._session.flush()
