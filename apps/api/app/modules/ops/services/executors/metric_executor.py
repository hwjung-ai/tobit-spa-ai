from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable, Tuple

from app.shared.config_loader import load_text
from app.modules.asset_registry.loader import load_query_asset
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
from schemas.tool_contracts import ExecutorResult, ToolCall

from ..resolvers import resolve_ci, resolve_metric, resolve_time_range
from ..resolvers.types import CIHit, MetricHit, TimeRange


def _load_query_sql(scope: str, name: str) -> str | None:
    """Load query SQL with DB priority fallback to file."""
    asset = load_query_asset(scope, name)
    if asset:
        return asset.get("sql")
    return None


def run_metric(question: str, tenant_id: str = "t1") -> ExecutorResult:
    start_time = perf_counter()
    tool_calls: list[ToolCall] = []
    references: list[dict] = []
    used_tools = ["postgres", "timescale"]

    query_template = _load_query_sql("metric", "metric_timeseries") or load_text("queries/postgres/metric/metric_timeseries.sql")
    if not query_template:
        error_block = MarkdownBlock(
            type="markdown",
            title="Error",
            content="### 쿼리 파일 로드 실패\n- `metric_timeseries.sql` 파일을 찾을 수 없거나 읽는 데 실패했습니다.",
        )
        return ExecutorResult(
            blocks=[error_block.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references,
            summary={"status": "error", "reason": "query_load_failed"},
        )

    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        markdown = MarkdownBlock(
            type="markdown",
            title="Metric 결과 없음",
            content="CI를 찾을 수 없습니다.",
        )
        return ExecutorResult(
            blocks=[markdown.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references,
            summary={"status": "no_ci"},
        )
    ci = ci_hits[0]

    metric_hit = resolve_metric(question)
    if not metric_hit:
        markdown = MarkdownBlock(
            type="markdown",
            title="Metric 결과 없음",
            content="요청한 메트릭을 찾을 수 없습니다.",
        )
        return ExecutorResult(
            blocks=[markdown.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references,
            summary={"status": "no_metric"},
        )

    time_range = resolve_time_range(question, datetime.now(timezone.utc))
    params = _build_metric_params(tenant_id, ci, metric_hit, time_range)
    fetch_start = perf_counter()
    rows = _fetch_timeseries(query_template, params)
    fetch_elapsed_ms = int((perf_counter() - fetch_start) * 1000)

    # Record metric.series tool call
    tool_calls.append(
        ToolCall(
            tool="metric.series",
            elapsed_ms=fetch_elapsed_ms,
            input_params={
                "metric": metric_hit.metric_name,
                "time_range": time_range.bucket,
                "ci_id": ci.ci_id,
            },
            output_summary={"rows_count": len(rows)},
        )
    )

    if not rows:
        markdown = MarkdownBlock(
            type="markdown",
            title="Metric 결과 없음",
            content="해당 기간에 메트릭 데이터가 없습니다.",
        )
        return ExecutorResult(
            blocks=[markdown.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references,
            summary={"status": "no_data"},
        )

    stats = _calculate_stats(rows)
    blocks = _build_blocks(ci, metric_hit, time_range, stats, rows, query_template, params)

    # Extract references from blocks
    for block in blocks:
        if isinstance(block, ReferencesBlock):
            for item in block.items:
                references.append(item.dict())

    # Convert blocks to dicts
    blocks_dict = [block.dict() if hasattr(block, "dict") else block for block in blocks]

    elapsed_ms = int((perf_counter() - start_time) * 1000)
    return ExecutorResult(
        blocks=blocks_dict,
        used_tools=used_tools,
        tool_calls=tool_calls,
        references=references,
        summary={
            "status": "success",
            "metric": metric_hit.metric_name,
            "ci_code": ci.ci_code,
            "rows_count": len(rows),
            "stats": stats,
        },
    )


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
