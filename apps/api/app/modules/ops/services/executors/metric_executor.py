from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Tuple

from app.shared.config_loader import load_text
from core.db_pg import get_pg_connection
from schemas import (
    AnswerBlock,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TimeSeriesBlock,
    TimeSeriesPoint,
    TimeSeriesSeries,
)

from ..resolvers import resolve_ci, resolve_metric, resolve_time_range
from ..resolvers.types import CIHit, MetricHit, TimeRange


def run_metric(question: str, tenant_id: str = "t1") -> tuple[list[AnswerBlock], list[str]]:
    query_template = load_text("queries/postgres/metric/metric_timeseries.sql")
    if not query_template:
        return [
            MarkdownBlock(
                type="markdown",
                title="Error",
                content="### 쿼리 파일 로드 실패\n- `metric_timeseries.sql` 파일을 찾을 수 없거나 읽는 데 실패했습니다.",
            )
        ], []

    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        markdown = MarkdownBlock(
            type="markdown",
            title="Metric 결과 없음",
            content="CI를 찾을 수 없습니다.",
        )
        return [markdown], ["postgres", "timescale"]
    ci = ci_hits[0]

    metric_hit = resolve_metric(question)
    if not metric_hit:
        markdown = MarkdownBlock(
            type="markdown",
            title="Metric 결과 없음",
            content="요청한 메트릭을 찾을 수 없습니다.",
        )
        return [markdown], ["postgres", "timescale"]

    time_range = resolve_time_range(question, datetime.now(timezone.utc))
    params = _build_metric_params(tenant_id, ci, metric_hit, time_range)
    rows = _fetch_timeseries(query_template, params)

    if not rows:
        markdown = MarkdownBlock(
            type="markdown",
            title="Metric 결과 없음",
            content="해당 기간에 메트릭 데이터가 없습니다.",
        )
        return [markdown], ["postgres", "timescale"]

    stats = _calculate_stats(rows)
    blocks = _build_blocks(ci, metric_hit, time_range, stats, rows, query_template, params)
    return blocks, ["postgres", "timescale"]


def _build_metric_params(
    tenant_id: str, ci: CIHit, metric: MetricHit, time_range: TimeRange
) -> list:
    return [
        time_range.bucket,
        tenant_id,
        ci.ci_id,
        metric.metric_id,
        time_range.start,
        time_range.end,
    ]


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
            f"last {stats['last']:.2f} (count {int(stats['count'])})"
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
                payload={"sql": query.strip(), "params": [p for p in params]},
            )
        ],
    )
    return [markdown, timeseries, references]
