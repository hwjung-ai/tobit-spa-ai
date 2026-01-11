from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Tuple

from core.db_pg import get_pg_connection
from ..resolvers import resolve_ci, resolve_metric, resolve_time_range
from ..resolvers.types import CIHit, MetricHit, TimeRange
from schemas import (
    AnswerBlock,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TimeSeriesBlock,
    TimeSeriesPoint,
    TimeSeriesSeries,
)


def run_metric(question: str, tenant_id: str = "t1") -> tuple[list[AnswerBlock], list[str]]:
    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        raise ValueError("CI not found")
    ci = ci_hits[0]
    metric_hit = resolve_metric(question)
    if not metric_hit:
        raise ValueError("Metric not found")
    time_range = resolve_time_range(question, datetime.now(timezone.utc))
    query, params = _build_metric_query(tenant_id, ci, metric_hit, time_range)
    rows = _fetch_timeseries(query, params)
    if not rows:
        raise ValueError("No metric data")
    stats = _calculate_stats(rows)
    blocks = _build_blocks(ci, metric_hit, time_range, stats, rows, query, params)
    return blocks, ["postgres", "timescale"]


def _build_metric_query(
    tenant_id: str, ci: CIHit, metric: MetricHit, time_range: TimeRange
) -> Tuple[str, Iterable]:
    query = """
        SELECT time_bucket(%s, time) AS bucket_time, AVG(value) AS value
        FROM metric_value
        WHERE tenant_id = %s
          AND ci_id = %s
          AND metric_id = %s
          AND time >= %s
          AND time < %s
        GROUP BY bucket_time
        ORDER BY bucket_time
    """
    params = [
        time_range.bucket,
        tenant_id,
        ci.ci_id,
        metric.metric_id,
        time_range.start,
        time_range.end,
    ]
    return query, params


def _fetch_timeseries(query: str, params: Iterable) -> list[tuple]:
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()


def _calculate_stats(rows: list[tuple]) -> dict[str, float]:
    values = [float(row[1]) for row in rows]
    return {
        "max": max(values),
        "min": min(values),
        "avg": sum(values) / len(values),
        "last": values[-1],
        "count": len(values),
    }


def _build_blocks(
    ci: CIHit,
    metric: MetricHit,
    time_range: TimeRange,
    stats: dict[str, float],
    rows: list[tuple],
    query: str,
    params: Iterable,
) -> list[AnswerBlock]:
    markdown = MarkdownBlock(
        type="markdown",
        title="Metric summary",
        content=(
            f"**CI**: {ci.ci_code} ({ci.ci_name})\n"
            f"**Metric**: {metric.metric_name}\n"
            f"**Range**: {time_range.start.isoformat()} ~ {time_range.end.isoformat()}\n"
            f"**Stats**: max {stats['max']:.2f}, min {stats['min']:.2f}, avg {stats['avg']:.2f}, "
            f"last {stats['last']:.2f} (count {stats['count']})"
        ),
    )
    series = TimeSeriesSeries(
        name=metric.metric_name,
        data=[TimeSeriesPoint(timestamp=row[0].isoformat(), value=float(row[1])) for row in rows],
    )
    timeseries = TimeSeriesBlock(type="timeseries", title="Metric trend", series=[series])
    references = ReferencesBlock(
        type="references",
        title="Metric SQL",
        items=[
        ReferenceItem(
            kind="sql",
            title="metric query",
            payload={"sql": query.strip(), "params": params},
        )
    ],
)
    return [markdown, timeseries, references]
