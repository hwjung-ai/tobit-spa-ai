"""
Cache Manager for CEP Builder

Provides multi-level caching strategies using Redis to optimize frequently accessed data.
Implements automatic cache invalidation and TTL-based expiration.
"""

import json
import logging
from functools import wraps
from typing import Any, Dict, Optional

try:
    # type: ignore[attr-defined]
    from redis.asyncio import Redis as RedisType  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisType = None

    _redis_client: RedisType | None = None

logger = logging.getLogger(__name__)

# Cache TTL configurations (in seconds)
CACHE_TTL = {
    "rules_list": 300,  # 5 minutes
    "rule_detail": 600,  # 10 minutes
    "notifications_list": 180,  # 3 minutes
    "notification_detail": 600,  # 10 minutes
    "channel_status": 30,  # 30 seconds
    "system_health": 30,  # 30 seconds
    "rule_stats": 60,  # 1 minute
}


class CacheManager:
    """Manages caching for CEP operations"""

    def __init__(
        self, redis_client: Optional[Redis | None] = None, prefix: str = "cep:cache"
    ):
        """
        Initialize cache manager.

        Args:
            redis_client: Redis async client (optional)
            prefix: Redis key prefix
        """
        self.redis_client = redis_client
        self.prefix = prefix
        self.available = redis_client is not None

    async def is_available(self) -> bool:
        """Check if Redis cache is available"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.ping()  # type: ignore[attr-defined]
            return True
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}")
            return False

    # ========================================================================
    # Generic cache operations
    # ========================================================================

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache"""
        if not self.available:
            return None

        try:
            full_key = f"{self.prefix}:{key}"
            data = await self.redis_client.get(full_key)  # type: ignore[attr-defined]
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")

        return None

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: int = 300,
    ) -> bool:
        """Set value in cache with TTL"""
        if not self.available:
            return False

        try:
            full_key = f"{self.prefix}:{key}"
            await self.redis_client.setex(  # type: ignore[attr-defined]
                full_key,
                ttl,
                json.dumps(value, default=str),
            )
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.available:
            return False

        try:
            full_key = f"{self.prefix}:{key}"
            await self.redis_client.delete(full_key)  # type: ignore[attr-defined]
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete multiple keys matching pattern"""
        if not self.available:
            return 0

        try:
            full_pattern = f"{self.prefix}:{pattern}"
            deleted = 0

            while True:
                # type: ignore[attr-defined]
                scan_result = await self.redis_client.scan(cursor, match=full_pattern)
                if scan_result:
                    cursor = scan_result[0]  # type: ignore[attr-defined]
                    keys = scan_result[1] if len(scan_result) > 1 else []
                    if keys:
                        deleted += await self.redis_client.delete(*keys)  # type: ignore[attr-defined]
                if cursor == 0:
                    break

            return deleted
        except Exception as e:
            logger.warning(f"Cache pattern delete failed for {pattern}: {e}")
            return 0

        try:
            full_pattern = f"{self.prefix}:{pattern}"
            cursor: 0
            deleted = 0

            while True:
                # type: ignore[attr-defined]
                cursor, keys = await self.redis_client.scan(cursor, match=full_pattern)
                if keys:
                    deleted += await self.redis_client.delete(*keys)  # type: ignore[attr-defined]
                if cursor == 0:
                    break

            return deleted
        except Exception as e:
            logger.warning(f"Cache pattern delete failed for {pattern}: {e}")
            return 0

    # ========================================================================
    # CEP-specific cache operations
    # ========================================================================

    async def get_rules_list(
        self, trigger_type: Optional[str] = None, active_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get cached rules list"""
        filters = []
        if trigger_type:
            filters.append(f"type={trigger_type}")
        if active_only:
            filters.append("active=true")

        key = "rules_list" + (":" + ":".join(filters) if filters else "")
        return await self.get(key)

    async def set_rules_list(
        self,
        rules_data: Dict[str, Any],
        trigger_type: Optional[str] = None,
        active_only: bool = False,
    ) -> bool:
        """Cache rules list"""
        filters = []
        if trigger_type:
            filters.append(f"type={trigger_type}")
        if active_only:
            filters.append("active=true")

        key = "rules_list" + (":" + ":".join(filters) if filters else "")
        return await self.set(key, rules_data, CACHE_TTL["rules_list"])

    async def get_rule_detail(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get cached rule detail"""
        return await self.get(f"rule:{rule_id}")

    async def set_rule_detail(self, rule_id: str, rule_data: Dict[str, Any]) -> bool:
        """Cache rule detail"""
        return await self.set(f"rule:{rule_id}", rule_data, CACHE_TTL["rule_detail"])

    async def get_notifications_list(
        self, active_only: bool = True, channel: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached notifications list"""
        filters = []
        if active_only:
            filters.append("active=true")
        if channel:
            filters.append(f"channel={channel}")

        key = "notifications_list" + (":" + ":".join(filters) if filters else "")
        return await self.get(key)

    async def set_notifications_list(
        self,
        notifications_data: Dict[str, Any],
        active_only: bool = True,
        channel: Optional[str] = None,
    ) -> bool:
        """Cache notifications list"""
        filters = []
        if active_only:
            filters.append("active=true")
        if channel:
            filters.append(f"channel={channel}")

        key = "notifications_list" + (":" + ":".join(filters) if filters else "")
        return await self.set(key, notifications_data, CACHE_TTL["notifications_list"])

    async def get_notification_detail(
        self, notification_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached notification detail"""
        return await self.get(f"notification:{notification_id}")

    async def set_notification_detail(
        self, notification_id: str, notification_data: Dict[str, Any]
    ) -> bool:
        """Cache notification detail"""
        return await self.set(
            f"notification:{notification_id}",
            notification_data,
            CACHE_TTL["notification_detail"],
        )

    async def get_channel_status(self, channel: str) -> Optional[Dict[str, Any]]:
        """Get cached channel status"""
        return await self.get(f"channel_status:{channel}")

    async def set_channel_status(
        self, channel: str, status_data: Dict[str, Any]
    ) -> bool:
        """Cache channel status"""
        return await self.set(
            f"channel_status:{channel}",
            status_data,
            CACHE_TTL["channel_status"],
        )

    async def get_system_health(self) -> Optional[Dict[str, Any]]:
        """Get cached system health"""
        return await self.get("system_health")

    async def set_system_health(self, health_data: Dict[str, Any]) -> bool:
        """Cache system health"""
        return await self.set("system_health", health_data, CACHE_TTL["system_health"])

    async def get_rule_stats(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get cached rule execution statistics"""
        return await self.get(f"rule_stats:{rule_id}")

    async def set_rule_stats(self, rule_id: str, stats_data: Dict[str, Any]) -> bool:
        """Cache rule execution statistics"""
        return await self.set(
            f"rule_stats:{rule_id}",
            stats_data,
            CACHE_TTL["rule_stats"],
        )

    # ========================================================================
    # Cache invalidation
    # ========================================================================

    async def invalidate_rule(self, rule_id: str) -> int:
        """Invalidate all caches related to a rule"""
        count = 0
        count += await self.delete(f"rule:{rule_id}")
        count += await self.delete(f"rule_stats:{rule_id}")
        # Invalidate list caches
        count += await self.delete_pattern("rules_list*")
        return count

    async def invalidate_notification(self, notification_id: str) -> int:
        """Invalidate all caches related to a notification"""
        count = 0
        count += await self.delete(f"notification:{notification_id}")
        # Invalidate list caches
        count += await self.delete_pattern("notifications_list*")
        return count

    async def invalidate_channel(self, channel: str) -> int:
        """Invalidate cache for a channel"""
        count = 0
        count += await self.delete(f"channel_status:{channel}")
        # Invalidate notifications list for this channel
        count += await self.delete_pattern(f"notifications_list:*channel={channel}*")
        return count

    async def invalidate_all(self) -> int:
        """Invalidate all CEP caches"""
        return await self.delete_pattern("*")


def cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate a cache key from function arguments"""
    key_parts = []

    # Add positional arguments (skip 'self' and 'session')
    for i, arg in enumerate(args):
        if i > 1:  # Skip self and session
            if hasattr(arg, "id"):
                key_parts.append(str(arg.id))
            elif isinstance(arg, (str, int, bool)):
                key_parts.append(str(arg))

    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        if k not in ["session"]:
            if hasattr(v, "id"):
                key_parts.append(f"{k}={v.id}")
            elif isinstance(v, (str, int, bool, type(None))):
                key_parts.append(f"{k}={v}")

    return ":".join(key_parts) if key_parts else "default"


def with_cache(
    cache_manager: Optional[CacheManager],
    ttl: int = 300,
    key_builder=None,
):
    """
    Decorator for caching function results.

    Args:
        cache_manager: CacheManager instance
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not cache_manager or not cache_manager.available:
                return await func(*args, **kwargs)

            # Generate cache key
            if key_builder:
                key = key_builder(*args, **kwargs)
            else:
                key = f"{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached = await cache_manager.get(key)
            if cached is not None:
                return cached

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(key, result, ttl)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not cache_manager or not cache_manager.available:
                return func(*args, **kwargs)

            # For sync functions, we don't cache (requires async context)
            if cache_manager.redis_client:
                pass

            # Call function
            result = func(*args, **kwargs)
            return result

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


import asyncio
