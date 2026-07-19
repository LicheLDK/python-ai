"""Shared constants (T-1.03/T-1.04 auth rate limit; T-5.07 AI rate limit)."""

from __future__ import annotations

# Login rate limit (SDS: aisaas:rl:login:{email_or_ip}, TTL 15m)
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60

REDIS_KEY_LOGIN_RATE_EMAIL = "aisaas:rl:login:email:{email}"
REDIS_KEY_LOGIN_RATE_IP = "aisaas:rl:login:ip:{ip}"
REDIS_KEY_AUTH_DENY_JTI = "aisaas:auth:deny:{jti}"

# AI per-user rate limit (SDS §10.19 style; T-5.07)
AI_RATE_LIMIT_MAX_REQUESTS = 60
AI_RATE_LIMIT_WINDOW_SECONDS = 60
REDIS_KEY_AI_RATE_USER = "aisaas:rl:ai:{user_id}"

# Stats summary cache (SDS §10.19: aisaas:cache:stats:{user}:{day}, TTL 5m; T-7.05)
REDIS_KEY_STATS_SUMMARY = "aisaas:cache:stats:{user_id}:{day}"

# Cookies / CSRF (SDS §9.2)
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
AUTH_COOKIE_PATH = "/api/v1/auth"

# Document upload (SDS §9.4)
ALLOWED_DOCUMENT_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
)
