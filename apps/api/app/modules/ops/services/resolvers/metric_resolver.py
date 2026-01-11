from __future__ import annotations

from typing import Iterable

from scripts.seed.utils import get_postgres_conn

from .types import MetricHit

METRIC_KEYWORDS = [
    ("temperature", {"온도", "temperature", "temp"}),
    ("cpu_usage", {"cpu", "cpu 사용", "사용률"}),
    ("memory_usage", {"메모리", "ram", "memory"}),
    ("disk_io", {"disk", "iops", "io"}),
    ("network_in", {"network", "트래픽", "bandwidth", "inbound"}),
]


def resolve_metric(question: str) -> MetricHit | None:
    normalized = question.lower()
    for metric_name, keywords in METRIC_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            hit = _fetch_metric(metric_name)
            if hit:
                return hit
    return None


def _fetch_metric(metric_name: str) -> MetricHit | None:
    with get_postgres_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT metric_id, metric_name
                FROM metric_def
                WHERE metric_name = %s
                LIMIT 1
                """,
                (metric_name,),
            )
            row = cur.fetchone()
            if not row:
                return None
            metric_id, name = row
            return MetricHit(metric_id=str(metric_id), metric_name=name)
