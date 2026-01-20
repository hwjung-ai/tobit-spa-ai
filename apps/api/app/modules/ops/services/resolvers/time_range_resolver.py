from __future__ import annotations

import calendar
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .types import TimeRange

DEFAULT_BUCKET = "5 minutes"
ASIA_SEOUL = ZoneInfo("Asia/Seoul")

MONTH_PATTERN = re.compile(r"(\d+)\s*개월", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"(\d+)\s*년", re.IGNORECASE)

# 범위 날짜 파싱: "2025-12-01부터 2025-12-31까지", "2025-12-01 ~ 2025-12-31"
DATE_RANGE_PATTERN = re.compile(
    r"(\d{4})[-년/.](\d{1,2})[-월/.](\d{1,2})(?:\s*부터|\s*에서)?\s*(?:[-~부터]|에서)?\s*(\d{4})[-년/.](\d{1,2})[-월/.](\d{1,2})(?:\s*까지)?",
    re.IGNORECASE,
)
# 단일 명시적 날짜 패턴
ISO_DATE_PATTERN = re.compile(r"(\d{4})[-년/.](\d{1,2})[-월/.](\d{1,2})")

WEEK_PATTERN = re.compile(
    r"(?P<year>\d{4})\s*년\s*(?P<month>\d{1,2})\s*월\s*(?P<week>[^\\s]+?)\s*주",
    re.IGNORECASE,
)
WEEK_WORD_MAP = {
    "첫": 1,
    "첫째": 1,
    "1": 1,
    "1번째": 1,
    "1주": 1,
    "둘": 2,
    "둘째": 2,
    "2": 2,
    "2번째": 2,
    "2주": 2,
    "셋": 3,
    "셋째": 3,
    "3": 3,
    "3번째": 3,
    "3주": 3,
    "넷": 4,
    "넷째": 4,
    "4": 4,
    "4번째": 4,
    "4주": 4,
    "다섯": 5,
    "다섯째": 5,
    "5": 5,
    "5번째": 5,
    "5주": 5,
    "마지막": -1,
    "끝": -1,
    "마지막주": -1,
    "마지막 주": -1,
    "last": -1,
    "final": -1,
}


def resolve_time_range(question: str, now: datetime, tz: ZoneInfo | None = None) -> TimeRange:
    zone = tz or ASIA_SEOUL
    current = now.astimezone(zone)
    text = question.lower()

    # 범위 날짜 파싱 우선 (예: "2025-12-01부터 2025-12-31까지")
    date_range = _parse_date_range(text, zone)
    if date_range:
        return date_range

    week_range = _parse_week_of_month(text, zone)
    if week_range:
        return week_range
    month_match = MONTH_PATTERN.search(text)
    if month_match:
        months = int(month_match.group(1))
        start = _shift_months(current, months)
        return TimeRange(start=start, end=current, bucket="1 day")
    year_match = YEAR_PATTERN.search(text)
    if year_match:
        years = int(year_match.group(1))
        start = _shift_years(current, years)
        return TimeRange(start=start, end=current, bucket="1 day")
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


def _parse_week_of_month(text: str, zone: ZoneInfo) -> TimeRange | None:
    match = WEEK_PATTERN.search(text)
    if not match:
        return None
    year = int(match.group("year"))
    month = int(match.group("month"))
    week_token = match.group("week").strip().lower()
    week_index = _week_index_from_token(week_token)
    if week_index is None:
        return None
    return _build_week_range(year, month, week_index, zone)


def _weekday_range(year: int, month: int, week_index: int, zone: ZoneInfo) -> TimeRange | None:
    month_start = datetime(year, month, 1, tzinfo=zone)
    total_days = calendar.monthrange(year, month)[1]
    next_month_start = (
        datetime(year + 1, 1, 1, tzinfo=zone)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=zone)
    )
    max_weeks = (total_days + 6) // 7
    if week_index < 1:
        week_index = max_weeks if week_index == -1 else None  # fallback
    if week_index is None:
        return None
    if week_index > max_weeks:
        week_index = max_weeks
    start = month_start + timedelta(days=7 * (week_index - 1))
    if start >= next_month_start:
        return None
    end = start + timedelta(days=7)
    if end > next_month_start:
        end = next_month_start
    return TimeRange(start=start, end=end, bucket="6 hours")


def _build_week_range(year: int, month: int, week_index: int, zone: ZoneInfo) -> TimeRange | None:
    return _weekday_range(year, month, week_index, zone)


def _week_index_from_token(token: str) -> int | None:
    cleaned = token.replace("번째", "").replace("주", "").strip()
    if not cleaned:
        return None
    if cleaned in WEEK_WORD_MAP:
        return WEEK_WORD_MAP[cleaned]
    if cleaned.isdigit():
        return int(cleaned)
    return None


def _shift_months(timestamp: datetime, months: int) -> datetime:
    year = timestamp.year
    month = timestamp.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(timestamp.day, calendar.monthrange(year, month)[1])
    return timestamp.replace(year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)


def _shift_years(timestamp: datetime, years: int) -> datetime:
    try:
        return timestamp.replace(year=timestamp.year - years, hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        # handle leap day
        return timestamp.replace(month=2, day=28, year=timestamp.year - years, hour=0, minute=0, second=0, microsecond=0)


def _parse_date_range(text: str, zone: ZoneInfo) -> TimeRange | None:
    """범위 날짜 파싱: '2025-12-01부터 2025-12-31까지' 형태"""
    match = DATE_RANGE_PATTERN.search(text)
    if not match:
        return None

    try:
        # 시작 날짜
        start_year = int(match.group(1))
        start_month = int(match.group(2))
        start_day = int(match.group(3))
        start = datetime(start_year, start_month, start_day, 0, 0, 0, 0, tzinfo=zone)

        # 종료 날짜
        end_year = int(match.group(4))
        end_month = int(match.group(5))
        end_day = int(match.group(6))
        end = datetime(end_year, end_month, end_day, 23, 59, 59, 0, tzinfo=zone)

        return TimeRange(start=start, end=end, bucket="1 day")
    except (ValueError, IndexError):
        return None
