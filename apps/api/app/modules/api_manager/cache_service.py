from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from core.config import get_settings
from core.redis import create_redis_client
from redis import Redis

logger = logging.getLogger(__name__)


@dataclass
class _CacheItem:
    value: dict[str, Any]
    expires_at: float


class APICacheService:
    """
    API result cache with Redis primary + in-memory fallback.
    Used by CEP-triggered API actions to reduce repeated runtime calls.
    """

    def __init__(
        self,
        *,
        use_redis: bool | None = None,
        redis_client: Redis | None = None,
    ):
        settings = get_settings()
        self._items: dict[str, _CacheItem] = {}
        self._hit_count = 0
        self._miss_count = 0
        self._backend = settings.api_cache_backend
        self._prefix = settings.api_cache_prefix
        self._default_ttl = max(1, int(settings.api_cache_default_ttl_seconds or 300))
        self._redis: Redis | None = None
        self._redis_enabled = (
            bool(use_redis)
            if use_redis is not None
            else self._backend in {"auto", "redis"}
        )
        if self._redis_enabled and settings.redis_url:
            try:
                self._redis = redis_client or create_redis_client(settings)
                self._redis.ping()
            except Exception as exc:  # noqa: BLE001
                self._redis = None
                if self._backend == "redis":
                    logger.warning(
                        "APICacheService redis backend unavailable, falling back to memory: %s",
                        exc,
                    )
                elif self._backend == "auto":
                    logger.info(
                        "APICacheService redis unavailable in auto mode, using memory fallback: %s",
                        exc,
                    )
        elif self._backend == "redis":
            logger.warning(
                "APICacheService configured with redis backend but REDIS_URL is missing; using memory fallback"
            )

    def _make_key(self, api_id: str, params: dict[str, Any]) -> str:
        payload = json.dumps(params or {}, sort_keys=True, default=str)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{self._prefix}{api_id}:{digest}"

    @property
    def backend(self) -> str:
        if self._redis is not None:
            return "redis"
        return "memory"

    def get(self, api_id: str, params: dict[str, Any]) -> dict[str, Any] | None:
        key = self._make_key(api_id, params)
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                if not raw:
                    self._miss_count += 1
                    return None
                value = json.loads(raw)
                if isinstance(value, dict):
                    self._hit_count += 1
                    return value
                self._miss_count += 1
                return None
            except Exception as exc:
                logger.warning("APICacheService redis get failed, fallback to memory: %s", exc)
                self._redis = None

        item = self._items.get(key)
        if not item:
            self._miss_count += 1
            return None
        if item.expires_at < time.time():
            self._items.pop(key, None)
            self._miss_count += 1
            return None
        self._hit_count += 1
        return item.value

    def set(
        self,
        api_id: str,
        params: dict[str, Any],
        value: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        key = self._make_key(api_id, params)
        ttl = max(1, int(ttl_seconds or self._default_ttl))
        if self._redis is not None:
            try:
                self._redis.setex(key, ttl, json.dumps(value, default=str))
                return
            except Exception as exc:
                logger.warning("APICacheService redis set failed, fallback to memory: %s", exc)
                self._redis = None

        self._items[key] = _CacheItem(
            value=value,
            expires_at=time.time() + ttl,
        )

    def get_stats(self) -> dict[str, Any]:
        total = self._hit_count + self._miss_count
        return {
            "backend": self.backend,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": (self._hit_count / total) if total else 0.0,
            "memory_items": len(self._items),
        }
