"""AI ORM models (T-5.01 / SDS §10.11–10.13).

Prompt CRUD / LLM adapters belong to later Phase 5 tasks.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AiProvider(str, enum.Enum):
    openai = "openai"
    gemini = "gemini"
    ollama = "ollama"


class AiRequestType(str, enum.Enum):
    chat = "chat"
    vision = "vision"
    pipeline = "pipeline"


class AiRequestStatus(str, enum.Enum):
    succeeded = "succeeded"
    failed = "failed"


class AiPrompt(Base):
    __tablename__ = "ai_prompts"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_ai_prompts_name_version"),
        Index(
            "uq_ai_prompts_name_active",
            "name",
            unique=True,
            postgresql_where=text("active IS TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    variables_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    requests: Mapped[list[AiRequest]] = relationship(
        "AiRequest",
        back_populates="prompt",
    )


class AiRequest(Base):
    __tablename__ = "ai_requests"
    __table_args__ = (
        Index("ix_ai_requests_user_created", "user_id", "created_at"),
        Index("ix_ai_requests_provider_created", "provider", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[AiProvider] = mapped_column(
        Enum(AiProvider, name="ai_provider", native_enum=True),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_prompts.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[AiRequestType] = mapped_column(
        Enum(AiRequestType, name="ai_request_type", native_enum=True),
        nullable=False,
    )
    input_ref: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    output_ref: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    status: Mapped[AiRequestStatus] = mapped_column(
        Enum(AiRequestStatus, name="ai_request_status", native_enum=True),
        nullable=False,
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    prompt: Mapped[Optional[AiPrompt]] = relationship(
        "AiPrompt",
        back_populates="requests",
    )
    usage: Mapped[Optional[AiUsage]] = relationship(
        "AiUsage",
        back_populates="request",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AiUsage(Base):
    __tablename__ = "ai_usages"
    __table_args__ = (Index("ix_ai_usages_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tokens_in: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    tokens_out: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_estimate: Mapped[float] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    request: Mapped[AiRequest] = relationship("AiRequest", back_populates="usage")
