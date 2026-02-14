"""Redis-based caching layer for improved performance."""

import json
import logging
from typing import Any, Callable, Optional, TypeVar

from core.config import get_settings
from core.redis import get_redis_client

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheManager:
    """Manages Redis-based caching with TTL and key management."""

    def __init__(self, redis_client=None):
        """Initialize cache manager."""
        self.redis_client = redis_client or get_redis_client()
        self.default_ttl = get_settings().cache_ttl if hasattr(get_settings(), 'cache_ttl') else 3600

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = self.redis_client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (defaults to default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.redis_client.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def clear_all(self) -> bool:
        """
        Clear all cached data (use with caution!).
        
        Returns:
            True if successful
        """
        try:
            self.redis_client.flushdb()
            logger.warning("Cache cleared completely")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache keys
        ttl: Time to live in seconds
        key_builder: Custom function to build cache key from arguments
        
    Example:
        @cached("user_profile", ttl=300)
        def get_user_profile(user_id: str):
            # Expensive database query
            return db.query(User).filter(User.id == user_id).first()
            
        @cached("search_results", key_builder=lambda **kwargs: f"search:{kwargs['query']}")
        def search_items(query: str, filters: dict):
            # Complex search logic
            return search_engine.query(query, **filters)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder: use function name and args
                args_str = "_".join(str(arg) for arg in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{func.__name__}:{args_str}:{kwargs_str}"

            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)

            # Cache result
            cache_manager.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


def cache_invalidate_pattern(pattern: str) -> bool:
    """
    Invalidate all cache keys matching a pattern.
    
    Args:
        pattern: Key pattern to invalidate
        
    Returns:
        True if successful
    """
    count = cache_manager.delete_pattern(pattern)
    logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
    return count > 0


class CacheKeys:
    """Standardized cache key patterns."""

    # User data
    USER_PROFILE = "user:profile:{user_id}"
    USER_PERMISSIONS = "user:permissions:{user_id}"

    # Asset data
    ASSET = "asset:{asset_type}:{asset_id}"
    ASSET_LIST = "asset:list:{asset_type}"

    # OPS queries
    OPS_QUERY_RESULT = "ops:query:{query_hash}"
    OPS_ORCHESTRATION_RESULT = "ops:orchestration:{trace_id}"

    # Regression data
    REGRESSION_BASELINE = "regression:baseline:{query_id}"
    REGRESSION_RESULT = "regression:result:{run_id}"

    # CEP data
    CEP_TRIGGER_STATE = "cep:state:{trigger_id}"
    CEP_NOTIFICATION = "cep:notification:{notification_id}"

    # Screen data
    SCREEN_SCHEMA = "screen:schema:{screen_id}"
    SCREEN_RENDER_CACHE = "screen:render:{screen_id}:{version}:{params_hash}"

    # Session data
    SESSION_DATA = "session:{session_id}"
    CHAT_CONTEXT = "chat:context:{session_id}"

    # API Engine
    API_DEFINITION = "api:def:{api_id}"
    API_EXECUTION_CACHE = "api:exec:{api_id}:{params_hash}"


def build_cache_key(template: str, **kwargs) -> str:
    """
    Build a cache key from a template and parameters.
    
    Args:
        template: Key template with placeholders (e.g., "user:{user_id}")
        **kwargs: Values for placeholders
        
    Returns:
        Formatted cache key
    """
    return template.format(**kwargs)


def cache_asset_invalidation(asset_type: str, asset_id: str):
    """
    Invalidate cache when an asset is updated.
    
    Args:
        asset_type: Type of asset (prompt, policy, screen, etc.)
        asset_id: ID of the asset
    """
    # Invalidate specific asset
    cache_manager.delete(build_cache_key(CacheKeys.ASSET, asset_type=asset_type, asset_id=asset_id))

    # Invalidate asset list
    cache_manager.delete(build_cache_key(CacheKeys.ASSET_LIST, asset_type=asset_type))

    logger.info(f"Invalidated cache for {asset_type}:{asset_id}")


def cache_ops_invalidation(query_text: str):
    """
    Invalidate cache when OPS query result might change.
    
    Args:
        query_text: Query text that was executed
    """
    # Simple hash-based invalidation
    import hashlib
    query_hash = hashlib.md5(query_text.encode()).hexdigest()
    cache_manager.delete(build_cache_key(CacheKeys.OPS_QUERY_RESULT, query_hash=query_hash))

    logger.info(f"Invalidated OPS query cache for hash: {query_hash}")


def get_cache_stats() -> dict:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        info = cache_manager.redis_client.info('stats')
        return {
            "hits": info.get('keyspace_hits', 0),
            "misses": info.get('keyspace_misses', 0),
            "hit_rate": info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1),
            "total_keys": info.get('keyspace', {}).get('db0', 0)
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {}
