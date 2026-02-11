"""
Redis-based state manager for CEP Engine

Provides distributed state management for CEP rules and retry records,
enabling horizontal scaling and high availability.
"""

import json
import logging
from typing import Any, Dict, Optional

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None

logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = "redis://localhost:6379"
DEFAULT_EXPIRY_HOURS = 24


class RedisStateManager:
    """Redis를 기반으로 하는 분산 상태 관리자"""

    def __init__(self, redis_url: str = DEFAULT_REDIS_URL):
        """
        초기화

        Args:
            redis_url: Redis 서버 URL
        """
        if not REDIS_AVAILABLE:
            logger.warning(
                "Redis not available. Install 'redis' package to enable distributed state."
            )
            self.redis_client = None
            return

        self.redis_url = redis_url
        self.redis_client: Optional[Redis] = None
        self.prefix = "cep"

    async def connect(self) -> None:
        """Redis에 연결"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available")
            return

        try:
            self.redis_client = await redis.from_url(self.redis_url)
            # 연결 확인
            await self.redis_client.ping()
            logger.info(f"Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def is_available(self) -> bool:
        """Redis 가용성 확인"""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False

    # ========================================================================
    # Retry Record Management
    # ========================================================================

    async def save_retry_record(
        self,
        notification_id: str,
        channel_id: str,
        record: Dict[str, Any],
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> bool:
        """
        재시도 기록 저장

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID
            record: 재시도 기록
            expiry_hours: 만료 시간 (시간)

        Returns:
            저장 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.prefix}:retry:{notification_id}:{channel_id}"
            value = json.dumps(record, default=str)
            expire_seconds = expiry_hours * 3600

            await self.redis_client.setex(key, expire_seconds, value)
            logger.debug(f"Saved retry record: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to save retry record: {e}")
            return False

    async def get_retry_record(
        self,
        notification_id: str,
        channel_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        재시도 기록 조회

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID

        Returns:
            재시도 기록 또는 None
        """
        if not self.redis_client:
            return None

        try:
            key = f"{self.prefix}:retry:{notification_id}:{channel_id}"
            value = await self.redis_client.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get retry record: {e}")
            return None

    async def delete_retry_record(
        self,
        notification_id: str,
        channel_id: str,
    ) -> bool:
        """
        재시도 기록 삭제

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID

        Returns:
            삭제 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.prefix}:retry:{notification_id}:{channel_id}"
            await self.redis_client.delete(key)
            logger.debug(f"Deleted retry record: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete retry record: {e}")
            return False

    async def list_retry_records(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 재시도 기록 조회

        Returns:
            재시도 기록 딕셔너리
        """
        if not self.redis_client:
            return {}

        try:
            pattern = f"{self.prefix}:retry:*"
            keys = await self.redis_client.keys(pattern)
            records = {}

            for key in keys:
                value = await self.redis_client.get(key)
                if value:
                    records[key.decode()] = json.loads(value)

            return records

        except Exception as e:
            logger.error(f"Failed to list retry records: {e}")
            return {}

    # ========================================================================
    # Rule State Management
    # ========================================================================

    async def save_rule_state(
        self,
        rule_id: str,
        state: Dict[str, Any],
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> bool:
        """
        규칙 상태 저장

        Args:
            rule_id: 규칙 ID
            state: 규칙 상태
            expiry_hours: 만료 시간 (시간)

        Returns:
            저장 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.prefix}:rule:{rule_id}:state"
            value = json.dumps(state, default=str)
            expire_seconds = expiry_hours * 3600

            await self.redis_client.setex(key, expire_seconds, value)
            logger.debug(f"Saved rule state: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to save rule state: {e}")
            return False

    async def get_rule_state(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        규칙 상태 조회

        Args:
            rule_id: 규칙 ID

        Returns:
            규칙 상태 또는 None
        """
        if not self.redis_client:
            return None

        try:
            key = f"{self.prefix}:rule:{rule_id}:state"
            value = await self.redis_client.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get rule state: {e}")
            return None

    # ========================================================================
    # Anomaly Detection Baseline Management
    # ========================================================================

    async def store_baseline(
        self,
        rule_id: str,
        values: list[float],
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> bool:
        """
        Store baseline values for anomaly detection.

        Args:
            rule_id: Rule ID
            values: Baseline numeric values
            expiry_hours: TTL in hours (default 24h)

        Returns:
            Whether the store succeeded
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.prefix}:baseline:{rule_id}"
            value = json.dumps(values)
            expire_seconds = expiry_hours * 3600

            await self.redis_client.setex(key, expire_seconds, value)
            logger.debug(f"Stored baseline for rule {rule_id}: {len(values)} values")
            return True

        except Exception as e:
            logger.error(f"Failed to store baseline for rule {rule_id}: {e}")
            return False

    async def get_baseline(self, rule_id: str) -> Optional[list[float]]:
        """
        Retrieve baseline values for anomaly detection.

        Args:
            rule_id: Rule ID

        Returns:
            List of baseline values or None
        """
        if not self.redis_client:
            return None

        try:
            key = f"{self.prefix}:baseline:{rule_id}"
            value = await self.redis_client.get(key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get baseline for rule {rule_id}: {e}")
            return None

    async def append_baseline(
        self,
        rule_id: str,
        new_value: float,
        max_size: int = 1000,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> bool:
        """
        Append a value to the baseline, keeping at most max_size entries.

        Args:
            rule_id: Rule ID
            new_value: New value to append
            max_size: Maximum baseline size
            expiry_hours: TTL in hours

        Returns:
            Whether the operation succeeded
        """
        if not self.redis_client:
            return False

        try:
            existing = await self.get_baseline(rule_id)
            values = existing or []
            values.append(new_value)
            if len(values) > max_size:
                values = values[-max_size:]
            return await self.store_baseline(rule_id, values, expiry_hours)

        except Exception as e:
            logger.error(f"Failed to append baseline for rule {rule_id}: {e}")
            return False

    # ========================================================================
    # Template Cache Management
    # ========================================================================

    async def cache_template(
        self,
        template_name: str,
        template_content: str,
        expiry_hours: int = 24,
    ) -> bool:
        """
        템플릿 캐시 저장

        Args:
            template_name: 템플릿 이름
            template_content: 템플릿 내용
            expiry_hours: 캐시 만료 시간 (시간)

        Returns:
            저장 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.prefix}:template:{template_name}"
            expire_seconds = expiry_hours * 3600

            await self.redis_client.setex(key, expire_seconds, template_content)
            logger.debug(f"Cached template: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to cache template: {e}")
            return False

    async def get_cached_template(self, template_name: str) -> Optional[str]:
        """
        캐시된 템플릿 조회

        Args:
            template_name: 템플릿 이름

        Returns:
            템플릿 내용 또는 None
        """
        if not self.redis_client:
            return None

        try:
            key = f"{self.prefix}:template:{template_name}"
            value = await self.redis_client.get(key)

            if value:
                return value.decode()
            return None

        except Exception as e:
            logger.error(f"Failed to get cached template: {e}")
            return None

    async def clear_template_cache(self) -> bool:
        """
        템플릿 캐시 전부 삭제

        Returns:
            삭제 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            pattern = f"{self.prefix}:template:*"
            keys = await self.redis_client.keys(pattern)

            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cached templates")
            return True

        except Exception as e:
            logger.error(f"Failed to clear template cache: {e}")
            return False

    # ========================================================================
    # Event Queue Management (Pub/Sub)
    # ========================================================================

    async def publish_event(self, channel: str, event: Dict[str, Any]) -> bool:
        """
        이벤트 발행

        Args:
            channel: 채널 이름
            event: 이벤트 데이터

        Returns:
            발행 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            key = f"{self.prefix}:channel:{channel}"
            message = json.dumps(event, default=str)
            await self.redis_client.publish(key, message)
            logger.debug(f"Published event to {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    async def subscribe_to_channel(self, channel: str):
        """
        채널 구독 (async generator)

        Args:
            channel: 채널 이름

        Yields:
            구독한 메시지
        """
        if not self.redis_client:
            logger.warning("Redis not available")
            return

        try:
            pubsub = self.redis_client.pubsub()
            key = f"{self.prefix}:channel:{channel}"
            await pubsub.subscribe(key)

            logger.info(f"Subscribed to {key}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in message: {message}")

        except Exception as e:
            logger.error(f"Error subscribing to channel: {e}")
        finally:
            await pubsub.close()

    # ========================================================================
    # General Utilities
    # ========================================================================

    async def set_key(
        self,
        key: str,
        value: Dict[str, Any],
        expiry_hours: int = DEFAULT_EXPIRY_HOURS,
    ) -> bool:
        """
        일반 키-값 저장

        Args:
            key: 키
            value: 값 (딕셔너리 또는 JSON 직렬화 가능 객체)
            expiry_hours: 만료 시간 (시간)

        Returns:
            저장 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            full_key = f"{self.prefix}:{key}"
            json_value = json.dumps(value, default=str)
            expire_seconds = expiry_hours * 3600

            await self.redis_client.setex(full_key, expire_seconds, json_value)
            return True

        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    async def get_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        일반 키-값 조회

        Args:
            key: 키

        Returns:
            값 또는 None
        """
        if not self.redis_client:
            return None

        try:
            full_key = f"{self.prefix}:{key}"
            value = await self.redis_client.get(full_key)

            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    async def delete_key(self, key: str) -> bool:
        """
        일반 키 삭제

        Args:
            key: 키

        Returns:
            삭제 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            full_key = f"{self.prefix}:{key}"
            await self.redis_client.delete(full_key)
            return True

        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        모든 CEP 관련 키 삭제

        Returns:
            삭제 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            pattern = f"{self.prefix}:*"
            keys = await self.redis_client.keys(pattern)

            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys from Redis")
            return True

        except Exception as e:
            logger.error(f"Failed to clear all keys: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        Redis 통계 조회

        Returns:
            통계 정보
        """
        if not self.redis_client:
            return {"available": False}

        try:
            retry_keys = await self.redis_client.keys(f"{self.prefix}:retry:*")
            rule_keys = await self.redis_client.keys(f"{self.prefix}:rule:*")
            template_keys = await self.redis_client.keys(f"{self.prefix}:template:*")

            info = await self.redis_client.info()

            return {
                "available": True,
                "connected": True,
                "retry_records": len(retry_keys),
                "rule_states": len(rule_keys),
                "cached_templates": len(template_keys),
                "memory_usage_mb": info.get("used_memory", 0) / 1024 / 1024,
                "connected_clients": info.get("connected_clients", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"available": False, "error": str(e)}


# 전역 Redis 상태 관리자 인스턴스
_global_redis_manager: Optional[RedisStateManager] = None


def get_redis_state_manager(
    redis_url: str = DEFAULT_REDIS_URL,
) -> RedisStateManager:
    """
    Redis 상태 관리자 인스턴스 획득

    Args:
        redis_url: Redis 서버 URL

    Returns:
        RedisStateManager 인스턴스
    """
    global _global_redis_manager

    if _global_redis_manager is None:
        _global_redis_manager = RedisStateManager(redis_url)

    return _global_redis_manager
