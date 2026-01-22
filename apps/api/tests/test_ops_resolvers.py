from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app.modules.ops.services.resolvers.ci_resolver import resolve_ci
from app.modules.ops.services.resolvers.metric_resolver import resolve_metric
from app.modules.ops.services.resolvers.time_range_resolver import resolve_time_range
from scripts.seed.utils import get_postgres_conn

ASIA_SEOUL = ZoneInfo("Asia/Seoul")


def _has_postgres() -> bool:
    try:
        with get_postgres_conn():
            pass
        return True
    except Exception:
        return False


HAS_DB = _has_postgres()


@pytest.mark.skipif(not HAS_DB, reason="Postgres not configured")
def test_ci_resolver_exact_code():
    hits = resolve_ci("Inspect srv-erp-01 status")
    assert hits
    assert hits[0].ci_code == "srv-erp-01"
    assert hits[0].score == 1.0


@pytest.mark.skipif(not HAS_DB, reason="Postgres not configured")
def test_ci_resolver_name_fallback():
    hits = resolve_ci("Check ERP System health")
    assert hits
    assert hits[0].score == 0.6
    assert "ERP" in hits[0].ci_name


@pytest.mark.skipif(not HAS_DB, reason="Postgres not configured")
def test_metric_resolver_cpu():
    hit = resolve_metric("CPU 사용률을 보여줘")
    assert hit
    assert hit.metric_name == "cpu_usage"


def test_time_range_last_7_days():
    now = datetime(2025, 12, 31, 12, 0, tzinfo=ASIA_SEOUL)
    tr = resolve_time_range("지난 7일", now, tz=ASIA_SEOUL)
    assert tr.bucket == "1 hour"
    assert tr.end == now
    assert tr.start == now - timedelta(days=7)


def test_time_range_month_2025_12():
    now = datetime(2025, 12, 15, 10, 0, tzinfo=ASIA_SEOUL)
    tr = resolve_time_range("2025-12 월간", now, tz=ASIA_SEOUL)
    assert tr.bucket == "6 hours"
    assert tr.start == datetime(2025, 12, 1, 0, 0, tzinfo=ASIA_SEOUL)
    assert tr.end == datetime(2026, 1, 1, 0, 0, tzinfo=ASIA_SEOUL)
