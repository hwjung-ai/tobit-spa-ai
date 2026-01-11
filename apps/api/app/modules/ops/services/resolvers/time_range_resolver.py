from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .types import TimeRange

DEFAULT_BUCKET = "5 minutes"
ASIA_SEOUL = ZoneInfo("Asia/Seoul")


def resolve_time_range(question: str, now: datetime, tz: ZoneInfo | None = None) -> TimeRange:
    zone = tz or ASIA_SEOUL
    current = now.astimezone(zone)
    text = question.lower()
    if "2025-12" in text:
        return TimeRange(
            start=current.replace(year=2025, month=12, day=1, hour=0, minute=0, second=0, microsecond=0),
            end=current.replace(year=2025, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=31),
            bucket="6 hours",
        )
    if "지난 7일" in text:
        return TimeRange(
            start=current - timedelta(days=7),
            end=current,
            bucket="1 hour",
        )
    if "지난 30일" in text or "지난달" in text:
        return TimeRange(
            start=current - timedelta(days=30),
            end=current,
            bucket="6 hours",
        )
    if "어제" in text:
        yesterday = (current - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return TimeRange(
            start=yesterday,
            end=yesterday + timedelta(days=1),
            bucket="1 hour",
        )
    if "오늘" in text:
        today_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
        return TimeRange(
            start=today_start,
            end=current,
            bucket="15 minutes",
        )
    return TimeRange(
        start=current - timedelta(hours=24),
        end=current,
        bucket=DEFAULT_BUCKET,
    )
