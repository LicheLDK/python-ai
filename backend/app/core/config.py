"""Application settings loaded from environment / `.env` (T-0.05).

Uses pydantic-settings. Does not open DB or Redis connections.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Singleton configuration mirroring docs/SDS.md §6.6."""

    model_config = SettingsConfigDict(
        # Prefer repo-root `.env` when commands run from `backend/`.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="local", description="local | staging | production")

    # Default matches docker-compose host publish (5433:5432).
    database_url: str = Field(
        default="postgresql+asyncpg://aisaas:aisaas@localhost:5433/ai_saas",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    jwt_secret: str = Field(default="change-me-local-placeholder-not-a-real-secret")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_minutes: int = Field(default=30)
    refresh_token_ttl_days: int = Field(default=14)

    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated origin allowlist",
    )

    openai_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    ai_primary_provider: str = Field(default="openai")
    ai_fallback_provider: str = Field(default="gemini")
    ai_fallback_enabled: bool = Field(default=False)
    ai_rate_limit_max: int = Field(
        default=60,
        description="Max AI chat/vision requests per user per window (T-5.07)",
    )
    ai_rate_limit_window_seconds: int = Field(
        default=60,
        description="AI rate-limit window seconds",
    )

    # Ollama local LLM (T-13.01)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama HTTP base URL (no trailing slash)",
    )
    ollama_chat_model: str = Field(default="llama3.2")
    ollama_vision_model: str = Field(default="llava")
    ollama_timeout_seconds: float = Field(
        default=120.0,
        description="Ollama HTTP timeout seconds (local models can be slow)",
    )

    storage_path: str = Field(default="/data/storage")
    storage_backend: str = Field(
        default="local",
        description="StoragePort backend: local | s3 (T-14.02)",
    )
    s3_endpoint_url: str = Field(
        default="",
        description="S3/MinIO endpoint (empty = AWS default)",
    )
    s3_access_key_id: str = Field(default="")
    s3_secret_access_key: str = Field(default="")
    s3_bucket: str = Field(default="")
    s3_region: str = Field(default="us-east-1")
    s3_force_path_style: bool = Field(
        default=True,
        description="Path-style addressing (required for most MinIO setups)",
    )

    ocr_lang: str = Field(default="korean+en")
    ocr_max_pages: int = Field(default=20)
    ocr_max_attempts: int = Field(
        default=3,
        description="Max OCR worker attempts before permanent failed (T-4.06)",
    )
    ocr_retry_base_seconds: float = Field(
        default=2.0,
        description="Exponential backoff base: base * 2^(attempt-1)",
    )
    ocr_reconcile_enabled: bool = Field(
        default=True,
        description="ARQ cron reconciler for stale queued/running OCR jobs (T-4.09)",
    )
    ocr_stale_queued_seconds: int = Field(
        default=180,
        description="Re-enqueue queued jobs with no progress older than this",
    )
    ocr_stale_running_seconds: int = Field(
        default=1200,
        description="Reset+requeue running jobs stuck longer than this (worker crash)",
    )
    upload_max_bytes: int = Field(default=10_485_760)

    stats_materialize_enabled: bool = Field(
        default=True,
        description="ARQ cron materializing stat_daily from activity (T-7.02)",
    )
    stats_summary_cache_seconds: int = Field(
        default=300,
        description="Redis TTL for /stats/summary cache (T-7.05)",
    )

    # RAG (T-15.01+) — embeddings store + retrieval
    embedding_provider: str = Field(
        default="openai",
        description="EmbeddingPort backend: openai | hash",
    )
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(
        default=1536,
        description="Vector size (hash adapter often uses 64)",
    )
    rag_chunk_size: int = Field(default=800, description="Character chunk window")
    rag_chunk_overlap: int = Field(default=120, description="Chunk overlap chars")
    rag_top_k: int = Field(default=5, description="Default retrieve top-k")

    # Soft multi-tenant (T-16.01+)
    default_org_name: str = Field(
        default="Default Organization",
        description="Name used when ensuring the default org on register/seed",
    )

    next_public_api_base_url: str = Field(default="http://localhost:8000")

    # Admin seed (T-1.07) — local defaults only; override in real environments.
    seed_admin_email: str = Field(default="admin@example.com")
    seed_admin_password: str = Field(default="ChangeMeAdmin1!")
    seed_admin_name: str = Field(default="Admin")

    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list (for later CORS middleware tasks)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return Settings()


# Eager singleton for convenient imports: `from app.core.config import settings`
settings: Settings = get_settings()
