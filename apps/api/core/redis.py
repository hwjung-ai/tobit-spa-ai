from __future__ import annotations

from redis import Redis
from redis.exceptions import RedisError

from .config import AppSettings


def create_redis_client(settings: AppSettings) -> Redis:
    if not settings.redis_url:
        raise ValueError("Redis URL is not configured")
    return Redis.from_url(settings.redis_url, decode_responses=True)


def test_redis_connection(settings: AppSettings) -> bool:
    """
    Simple ping test that validates the Redis connection configuration.
    """
    client = create_redis_client(settings)
    try:
        client.ping()
        return True
    except RedisError as exc:
        raise RuntimeError("Redis ping failed") from exc
