"""PromptService — versioned prompt templates (T-5.05 / SDS §7.8, ADR-013)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.exceptions.domain import ConflictError, NotFoundError, ValidationAppError
from app.models.ai import AiPrompt
from app.models.user import User
from app.repositories.ai_prompt_repository import AiPromptRepository
from app.services.audit_service import AuditService
from app.utils.pagination import PageParams, normalize_page

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PromptService:
    def __init__(
        self,
        session: Session,
        *,
        prompts: AiPromptRepository | None = None,
        audit: AuditService | None = None,
    ) -> None:
        self._session = session
        self._prompts = prompts or AiPromptRepository(session)
        self._audit = audit or AuditService(session)

    def list_prompts(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        name: str | None = None,
        active: bool | None = None,
    ) -> tuple[list[AiPrompt], PageParams, int]:
        params = normalize_page(page, page_size)
        rows, total = self._prompts.list(page=params, name=name, active=active)
        return rows, params, total

    def get(self, prompt_id: uuid.UUID) -> AiPrompt:
        row = self._prompts.get_by_id(prompt_id)
        if row is None:
            raise NotFoundError("Prompt not found")
        return row

    def create(
        self,
        *,
        actor: User,
        name: str,
        template: str,
        variables_schema: dict[str, Any] | None = None,
        activate: bool = False,
        ip: str | None = None,
    ) -> AiPrompt:
        cleaned = name.strip()
        if not cleaned:
            raise ValidationAppError("Prompt name is required")
        version = self._prompts.max_version(cleaned) + 1
        if activate:
            self._prompts.deactivate_active_for_name(cleaned)
        row = self._prompts.create(
            name=cleaned,
            version=version,
            template=template,
            variables_schema=variables_schema or {},
            active=activate,
            created_by=actor.id,
        )
        self._audit.write(
            action="admin.prompt.create",
            resource_type="ai_prompt",
            actor_id=actor.id,
            resource_id=str(row.id),
            payload={"name": cleaned, "version": version, "activate": activate},
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(row)
        return row

    def update(
        self,
        *,
        actor: User,
        prompt_id: uuid.UUID,
        template: str | None = None,
        variables_schema: dict[str, Any] | None = None,
        create_new_version: bool = False,
        ip: str | None = None,
    ) -> AiPrompt:
        current = self.get(prompt_id)
        if create_new_version:
            if template is None and variables_schema is None:
                raise ValidationAppError(
                    "create_new_version requires template and/or variables_schema"
                )
            new_version = self._prompts.max_version(current.name) + 1
            row = self._prompts.create(
                name=current.name,
                version=new_version,
                template=template if template is not None else current.template,
                variables_schema=(
                    variables_schema
                    if variables_schema is not None
                    else dict(current.variables_schema or {})
                ),
                active=False,
                created_by=actor.id,
            )
            self._audit.write(
                action="admin.prompt.version",
                resource_type="ai_prompt",
                actor_id=actor.id,
                resource_id=str(row.id),
                payload={
                    "name": row.name,
                    "version": row.version,
                    "from_prompt_id": str(current.id),
                },
                ip=ip,
                commit=False,
            )
            self._session.commit()
            self._session.refresh(row)
            return row

        if template is None and variables_schema is None:
            raise ValidationAppError("No fields to update")
        if template is not None:
            current.template = template
        if variables_schema is not None:
            current.variables_schema = variables_schema
        self._audit.write(
            action="admin.prompt.update",
            resource_type="ai_prompt",
            actor_id=actor.id,
            resource_id=str(current.id),
            payload={"name": current.name, "version": current.version},
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(current)
        return current

    def activate(
        self,
        *,
        actor: User,
        prompt_id: uuid.UUID,
        ip: str | None = None,
    ) -> AiPrompt:
        row = self.get(prompt_id)
        if row.active:
            return row
        self._prompts.deactivate_active_for_name(row.name)
        row.active = True
        self._audit.write(
            action="admin.prompt.activate",
            resource_type="ai_prompt",
            actor_id=actor.id,
            resource_id=str(row.id),
            payload={"name": row.name, "version": row.version},
            ip=ip,
            commit=False,
        )
        self._session.commit()
        self._session.refresh(row)
        return row

    def resolve(
        self,
        *,
        name: str | None,
        version: int | None = None,
    ) -> AiPrompt | None:
        """Resolve by name+version or active name. Returns None when name omitted."""
        if name is None:
            if version is not None:
                raise ValidationAppError("prompt_version requires prompt_name")
            return None
        cleaned = name.strip()
        if not cleaned:
            raise ValidationAppError("prompt_name is empty")
        if version is not None:
            row = self._prompts.get_by_name_version(cleaned, version)
            if row is None:
                raise NotFoundError(
                    "Prompt version not found",
                    details={"name": cleaned, "version": version},
                )
            return row
        row = self._prompts.get_active_by_name(cleaned)
        if row is None:
            raise NotFoundError(
                "Active prompt not found",
                details={"name": cleaned},
            )
        return row

    def render(
        self,
        prompt: AiPrompt,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Fill ``{placeholders}``; validate against variables_schema when present."""
        vars_in = dict(variables or {})
        schema = prompt.variables_schema or {}
        required = schema.get("required")
        if isinstance(required, list):
            missing = [k for k in required if k not in vars_in]
            if missing:
                raise ValidationAppError(
                    "Missing prompt variables",
                    details={"missing": missing},
                )
        placeholders = set(_PLACEHOLDER_RE.findall(prompt.template))
        missing_ph = sorted(placeholders - set(vars_in.keys()))
        if missing_ph:
            raise ValidationAppError(
                "Missing prompt variables",
                details={"missing": missing_ph},
            )

        class _Map(dict):
            def __missing__(self, key: str) -> str:  # pragma: no cover - guarded above
                raise KeyError(key)

        try:
            return prompt.template.format_map(_Map(vars_in))
        except (KeyError, ValueError) as exc:
            raise ValidationAppError(
                "Invalid prompt variables",
                details={"reason": str(exc)},
            ) from exc

    def ensure_unique_active(self, name: str) -> None:
        """Raise if more than one active row (defensive; DB also enforces)."""
        rows, _ = self._prompts.list(
            page=normalize_page(1, 100),
            name=name,
            active=True,
        )
        if len(rows) > 1:
            raise ConflictError(
                "Multiple active prompts for name",
                details={"name": name, "count": len(rows)},
            )
