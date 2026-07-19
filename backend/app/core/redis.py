"""Redis client factory (T-0.07).

Uses REDIS_URL from Settings / `.env`. Redis is not the system of record.
"""

from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """Return a process-wide Redis client singleton."""
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def ping_redis() -> bool:
    """Return True if Redis responds to PING."""
    try:
        return bool(get_redis().ping())
    except redis.RedisError:
        return False
