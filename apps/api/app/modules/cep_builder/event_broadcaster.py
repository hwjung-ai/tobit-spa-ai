from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CepEventBroadcaster:
    """
    CEP 이벤트 브로드캐스터

    - 메모리 기반 (asyncio.Queue) 로컬 구독자 지원
    - Redis Pub/Sub 옵션 지원 (분산 환경)
    - 양쪽 모드 동시 지원 가능

    특징:
    - 로컬 asyncio.Queue로 메모리 기반 메시징 지원
    - Redis Pub/Sub으로 분산 환경 지원
    - 자동 폴백: Redis 미사용 시 메모리만 사용
    - 스레드-안전 구독자 관리
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[
            tuple[asyncio.Queue[dict[str, Any]], asyncio.AbstractEventLoop]
        ] = []

        # Redis Pub/Sub (선택사항)
        self._redis = None
        self._redis_pubsub = None
        self._redis_listen_task = None
        self._redis_url = redis_url

        # Redis URL 자동 감지
        if not redis_url:
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self._redis_url = redis_url

        if self._redis_url:
            self._setup_redis(self._redis_url)

    def _setup_redis(self, redis_url: str) -> None:
        """Redis 연결 설정"""
        try:
            import redis.asyncio as redis

            self._redis_url = redis_url
            logger.info(f"Redis Pub/Sub 초기화 예정: {redis_url}")
        except ImportError:
            logger.warning("redis 패키지를 설치하세요 (pip install redis)")
            self._redis = None
            self._redis_url = None

    async def _start_redis_listener(self) -> None:
        """Redis Pub/Sub 리스너 시작"""
        if not self._redis_url:
            return

        try:
            import redis.asyncio as redis

            logger.info(f"Redis Pub/Sub 연결 중: {self._redis_url}")
            self._redis = await redis.from_url(self._redis_url, decode_responses=True)

            # 연결 테스트
            await self._redis.ping()
            logger.info("Redis Pub/Sub 연결 성공")

            self._redis_pubsub = self._redis.pubsub()
            await self._redis_pubsub.subscribe("cep:*")
            logger.info("Redis Pub/Sub 구독 시작: cep:*")

            # 수신 루프 시작
            async for message in self._redis_pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        self._broadcast_to_local_subscribers(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from Redis: {message['data']}")
        except Exception as e:
            logger.error(f"Redis listener error: {e}", exc_info=True)
            self._redis = None
            self._redis_pubsub = None

    async def ensure_redis_listener(self) -> None:
        """Redis 리스너 시작 (필요시 중복 호출해도 안전)"""
        if not self._redis_url:
            return

        # 이미 실행 중인 경우 무시
        if self._redis_listen_task and not self._redis_listen_task.done():
            return

        # 새로운 리스너 태스크 생성
        self._redis_listen_task = asyncio.create_task(self._start_redis_listener())

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """로컬 구독자 등록"""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers.append((queue, loop))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """로컬 구독자 등록 해제"""
        with self._lock:
            self._subscribers = [
                (item_queue, loop)
                for item_queue, loop in self._subscribers
                if item_queue is not queue
            ]

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """이벤트 발행"""
        payload = {"type": event_type, "data": data}

        # 로컬 구독자에게 전송
        self._broadcast_to_local_subscribers(payload)

        # Redis에도 발행
        if self._redis:
            self._publish_to_redis(event_type, payload)

    def _broadcast_to_local_subscribers(self, payload: dict[str, Any]) -> None:
        """로컬 구독자에게 메시지 전송"""
        with self._lock:
            subscribers = list(self._subscribers)
        for queue, loop in subscribers:
            try:
                loop.call_soon_threadsafe(_safe_put_nowait, queue, payload)
            except RuntimeError:
                continue

    def _publish_to_redis(self, event_type: str, payload: dict[str, Any]) -> None:
        """Redis Pub/Sub으로 발행"""
        try:
            import asyncio as aio

            # 비동기 작업 스케줄
            asyncio_loop = None
            try:
                asyncio_loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if asyncio_loop:
                asyncio_loop.create_task(
                    self._async_redis_publish(event_type, payload)
                )
        except Exception as e:
            logger.debug(f"Redis publish error: {e}")

    async def _async_redis_publish(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        """비동기 Redis 발행"""
        try:
            if self._redis:
                channel = f"cep:{event_type}"
                await self._redis.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.debug(f"Async Redis publish failed: {e}")


def _safe_put_nowait(
    queue: asyncio.Queue[dict[str, Any]], payload: dict[str, Any]
) -> None:
    """안전한 비동기 큐 전송"""
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        return


# 글로벌 브로드캐스터 인스턴스
event_broadcaster = CepEventBroadcaster()
