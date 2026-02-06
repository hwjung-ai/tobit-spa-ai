"""
Notification Retry Mechanism with Exponential Backoff

알림 전송 실패 시 지수 백오프를 적용한 자동 재시도 메커니즘
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """재시도 정책 설정"""

    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # seconds (5분)
    backoff_multiplier: float = 2.0
    jitter: bool = True  # 지터 추가 (충돌 방지)

    def get_delay(self, attempt: int) -> float:
        """
        지정된 시도 번호에 대한 대기 시간 계산

        Args:
            attempt: 시도 번호 (0-based)

        Returns:
            대기 시간 (초)
        """
        # 지수 백오프 계산
        delay = self.initial_delay * (self.backoff_multiplier ** attempt)

        # 최대 지연 시간 제한
        delay = min(delay, self.max_delay)

        # 지터 추가 (±10%)
        if self.jitter:
            import random

            jitter_factor = 1.0 + random.uniform(-0.1, 0.1)
            delay = delay * jitter_factor

        return delay

    def should_retry(self, attempt: int, last_http_status: Optional[int] = None) -> bool:
        """
        재시도 여부 판단

        Args:
            attempt: 현재 시도 번호
            last_http_status: 마지막 HTTP 상태 코드 (선택사항)

        Returns:
            재시도 여부
        """
        # 최대 재시도 횟수 확인
        if attempt >= self.max_retries:
            return False

        # HTTP 상태 코드 기반 재시도 판단
        # 5xx: 재시도 가능 (서버 에러)
        # 429: 재시도 가능 (Rate Limit)
        # 3xx, 4xx (408, 425 제외): 재시도 불가능 (클라이언트 에러)
        if last_http_status:
            if last_http_status >= 500:
                return True  # 서버 에러
            if last_http_status == 429:
                return True  # Rate Limit
            if last_http_status == 408:
                return True  # Request Timeout
            if last_http_status == 425:
                return True  # Too Early
            if 400 <= last_http_status < 500:
                return False  # 클라이언트 에러는 재시도 불가

        return True  # 기타 경우 (네트워크 에러 등)


@dataclass
class RetryRecord:
    """재시도 기록"""

    notification_id: str
    channel_id: str
    attempt: int
    last_error: Optional[str]
    last_status_code: Optional[int]
    next_retry_at: datetime
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "notification_id": self.notification_id,
            "channel_id": self.channel_id,
            "attempt": self.attempt,
            "last_error": self.last_error,
            "last_status_code": self.last_status_code,
            "next_retry_at": self.next_retry_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class NotificationRetryManager:
    """알림 재시도 관리자"""

    def __init__(self, retry_policy: Optional[RetryPolicy] = None):
        """
        초기화

        Args:
            retry_policy: 재시도 정책 (기본값: 표준 정책)
        """
        self.policy = retry_policy or RetryPolicy()
        self.retry_records: Dict[str, RetryRecord] = {}

    def create_retry_record(
        self,
        notification_id: str,
        channel_id: str,
        error: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> RetryRecord:
        """
        재시도 기록 생성

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID
            error: 에러 메시지
            status_code: HTTP 상태 코드

        Returns:
            생성된 재시도 기록
        """
        key = f"{notification_id}:{channel_id}"
        record = self.retry_records.get(key)

        if not record:
            # 새 기록 생성
            attempt = 0
            created_at = datetime.utcnow()
        else:
            # 기존 기록 업데이트
            attempt = record.attempt + 1
            created_at = record.created_at

        # 다음 재시도 시간 계산
        delay = self.policy.get_delay(attempt)
        next_retry_at = datetime.utcnow() + timedelta(seconds=delay)

        # 재시도 기록 생성/업데이트
        retry_record = RetryRecord(
            notification_id=notification_id,
            channel_id=channel_id,
            attempt=attempt,
            last_error=error,
            last_status_code=status_code,
            next_retry_at=next_retry_at,
            created_at=created_at,
            updated_at=datetime.utcnow(),
        )

        self.retry_records[key] = retry_record
        return retry_record

    def get_retry_record(
        self, notification_id: str, channel_id: str
    ) -> Optional[RetryRecord]:
        """
        재시도 기록 조회

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID

        Returns:
            재시도 기록 (없으면 None)
        """
        key = f"{notification_id}:{channel_id}"
        return self.retry_records.get(key)

    def should_retry(
        self,
        notification_id: str,
        channel_id: str,
        last_status_code: Optional[int] = None,
    ) -> bool:
        """
        재시도 여부 판단

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID
            last_status_code: 마지막 HTTP 상태 코드

        Returns:
            재시도 여부
        """
        record = self.get_retry_record(notification_id, channel_id)
        if not record:
            return True  # 처음 시도

        # 최대 재시도 횟수 확인
        if not self.policy.should_retry(record.attempt, last_status_code):
            logger.warning(
                f"Max retries reached for notification {notification_id} "
                f"on channel {channel_id} (attempt: {record.attempt})"
            )
            return False

        # 다음 재시도 시간 확인
        if datetime.utcnow() < record.next_retry_at:
            logger.debug(
                f"Notification {notification_id} on channel {channel_id} "
                f"will retry at {record.next_retry_at.isoformat()}"
            )
            return False

        return True

    def wait_until_retry(
        self, notification_id: str, channel_id: str
    ) -> Optional[float]:
        """
        다음 재시도까지 대기

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID

        Returns:
            대기 시간 (초) 또는 None (재시도 불가)
        """
        record = self.get_retry_record(notification_id, channel_id)
        if not record:
            return 0.0

        now = datetime.utcnow()
        if now >= record.next_retry_at:
            return 0.0

        wait_seconds = (record.next_retry_at - now).total_seconds()
        return max(0.0, wait_seconds)

    def reset_record(self, notification_id: str, channel_id: str) -> None:
        """
        재시도 기록 초기화 (성공 시 호출)

        Args:
            notification_id: 알림 ID
            channel_id: 채널 ID
        """
        key = f"{notification_id}:{channel_id}"
        if key in self.retry_records:
            del self.retry_records[key]
            logger.debug(
                f"Retry record cleared for notification {notification_id} "
                f"on channel {channel_id}"
            )

    def clear_expired(self, expiry_hours: int = 24) -> int:
        """
        만료된 재시도 기록 삭제

        Args:
            expiry_hours: 만료 시간 (시간)

        Returns:
            삭제된 기록 수
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=expiry_hours)
        expired_keys = [
            key
            for key, record in self.retry_records.items()
            if record.updated_at < cutoff_time
        ]

        for key in expired_keys:
            del self.retry_records[key]

        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired retry records")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        재시도 통계 조회

        Returns:
            통계 정보
        """
        if not self.retry_records:
            return {
                "total_records": 0,
                "by_attempt": {},
                "oldest_record": None,
                "newest_record": None,
            }

        records = list(self.retry_records.values())
        attempts = {}
        for record in records:
            attempts[record.attempt] = attempts.get(record.attempt, 0) + 1

        return {
            "total_records": len(records),
            "by_attempt": attempts,
            "oldest_record": min(r.created_at for r in records).isoformat(),
            "newest_record": max(r.updated_at for r in records).isoformat(),
        }


async def send_with_retry(
    send_func,
    notification_id: str,
    channel_id: str,
    retry_manager: NotificationRetryManager,
    *args,
    **kwargs,
) -> bool:
    """
    재시도 기능이 있는 알림 전송

    Args:
        send_func: 알림 전송 함수 (async)
        notification_id: 알림 ID
        channel_id: 채널 ID
        retry_manager: 재시도 관리자
        *args: send_func의 위치 인수
        **kwargs: send_func의 키워드 인수

    Returns:
        전송 성공 여부
    """
    attempt = 0
    last_error = None
    last_status_code = None

    while True:
        try:
            # 재시도 여부 확인
            if not retry_manager.should_retry(
                notification_id, channel_id, last_status_code
            ):
                logger.error(
                    f"Notification {notification_id} on channel {channel_id} "
                    f"failed after {retry_manager.policy.max_retries} attempts"
                )
                return False

            # 대기 시간이 남아있으면 대기
            wait_time = retry_manager.wait_until_retry(notification_id, channel_id)
            if wait_time and wait_time > 0:
                logger.info(
                    f"Waiting {wait_time:.1f}s before retrying "
                    f"notification {notification_id} on channel {channel_id}"
                )
                await asyncio.sleep(wait_time)

            # 알림 전송 시도
            logger.info(
                f"Sending notification {notification_id} on channel {channel_id} "
                f"(attempt {attempt + 1}/{retry_manager.policy.max_retries + 1})"
            )

            try:
                result = await send_func(*args, **kwargs)

                if result:
                    # 성공
                    logger.info(
                        f"Notification {notification_id} on channel {channel_id} "
                        f"sent successfully after {attempt} retry attempt(s)"
                    )
                    retry_manager.reset_record(notification_id, channel_id)
                    return True

                # 실패 (함수 반환 False)
                last_error = "Send function returned False"
                last_status_code = None

            except Exception as e:
                # 예외 발생
                last_error = str(e)
                last_status_code = None
                logger.warning(
                    f"Error sending notification {notification_id} "
                    f"on channel {channel_id}: {last_error}"
                )

            # 재시도 기록 생성
            retry_manager.create_retry_record(
                notification_id,
                channel_id,
                error=last_error,
                status_code=last_status_code,
            )

            attempt += 1

        except Exception as e:
            logger.error(
                f"Unexpected error in send_with_retry: {str(e)}", exc_info=True
            )
            return False
