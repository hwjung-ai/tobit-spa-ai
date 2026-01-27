from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable

from schemas import (
    AnswerBlock,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TableBlock,
)
from schemas.tool_contracts import ExecutorResult, ToolCall

from app.modules.asset_registry.loader import load_query_asset, load_source_asset
from app.modules.ops.services.connections import ConnectionFactory
from app.shared.config_loader import load_text
from core.config import get_settings

from ..ci.tools import history as history_tools
from ..resolvers import resolve_ci, resolve_time_range


def _get_connection():
    """Get connection using source asset."""
    settings = get_settings()
    source_asset = load_source_asset(settings.ops_default_source_asset)
    return ConnectionFactory.create(source_asset)


def _load_query_sql(scope: str, name: str) -> str:
    """Load query SQL from Asset Registry only (no fallback)."""
    asset, _ = load_query_asset(scope, name)
    if asset and "sql" in asset:
        return asset.get("sql")
    raise ValueError(f"Query asset not found in Asset Registry: {name} (scope={scope})")


def run_hist(question: str, tenant_id: str = "t1") -> ExecutorResult:
    start_time = perf_counter()
    tool_calls: list[ToolCall] = []
    references_list: list[dict] = []
    used_tools = ["postgres", "timescale"]

    work_h_query = _load_query_sql("history", "work_history")
    maint_h_query = _load_query_sql("history", "maintenance_history")
    event_l_query = _load_query_sql("history", "event_log")

    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        error_block = MarkdownBlock(
            type="markdown",
            title="No CI Found",
            content="### CI를 찾을 수 없습니다\n- 질문에서 CI를 지정하거나 검색어를 사용해 주세요.",
        )
        return ExecutorResult(
            blocks=[error_block.dict()],
            used_tools=used_tools,
            tool_calls=tool_calls,
            references=references_list,
            summary={"status": "no_ci"},
        )
    ci = ci_hits[0]
    time_range = resolve_time_range(question, datetime.now(timezone.utc))

    params = (tenant_id, ci.ci_id, time_range.start, time_range.end)
    fetch_start = perf_counter()
    work_rows = _fetch_history(work_h_query, params)
    maint_rows = _fetch_history(maint_h_query, params)
    event_rows = _fetch_history(event_l_query, params)
    fetch_elapsed_ms = int((perf_counter() - fetch_start) * 1000)

    # Record history.recent tool call
    tool_calls.append(
        ToolCall(
            tool="history.recent",
            elapsed_ms=fetch_elapsed_ms,
            input_params={
                "time_range": time_range.bucket,
                "ci_id": ci.ci_id,
                "ci_ids_count": 1,
            },
            output_summary={
                "work_rows": len(work_rows),
                "maint_rows": len(maint_rows),
                "event_rows": len(event_rows),
            },
        )
    )

    stats = {
        "work": len(work_rows),
        "maint": len(maint_rows),
        "events": len(event_rows),
        "max_severity": max((row[1] for row in event_rows), default=0),
    }
    sections = history_tools.detect_history_sections(question)
    include_work = "work" in sections or not sections
    include_maint = "maintenance" in sections or not sections
    blocks = _build_blocks(
        ci,
        time_range,
        stats,
        work_rows,
        maint_rows,
        event_rows,
        include_work,
        include_maint,
    )

    references_block = _build_references(
        work_rows,
        maint_rows,
        event_rows,
        tenant_id,
        ci,
        time_range,
        work_h_query,
        maint_h_query,
        event_l_query,
    )
    blocks.append(references_block)

    # Extract references from blocks
    for block in blocks:
        if isinstance(block, ReferencesBlock):
            for item in block.items:
                references_list.append(item.dict())

    # Convert blocks to dicts
    blocks_dict = [
        block.dict() if hasattr(block, "dict") else block for block in blocks
    ]

    int((perf_counter() - start_time) * 1000)
    return ExecutorResult(
        blocks=blocks_dict,
        used_tools=used_tools,
        tool_calls=tool_calls,
        references=references_list,
        summary={
            "status": "success",
            "ci_code": ci.ci_code,
            "stats": stats,
        },
    )


def _fetch_history(query: str, params: Iterable) -> list[tuple]:
    connection = _get_connection()
    try:
        conn = connection.connection if hasattr(connection, 'connection') else connection
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()
    finally:
        connection.close()


def _build_blocks(
    ci,
    time_range,
    stats,
    work_rows: list[tuple],
    maint_rows: list[tuple],
    event_rows: list[tuple],
    include_work: bool = True,
    include_maint: bool = True,
) -> list[AnswerBlock]:
    markdown = MarkdownBlock(
        type="markdown",
        title="History summary",
        content=(
            f"CI: {ci.ci_code} ({ci.ci_name})\n"
            f"Range: {time_range.start.isoformat()} ~ {time_range.end.isoformat()}\n"
            f"Work: {stats['work']} jobs, Maintenance: {stats['maint']} entries, "
            f"Events: {stats['events']} records (max severity {stats['max_severity']})"
        ),
    )
    tables: list[TableBlock] = []
    if include_work:
        tables.append(
            TableBlock(
                type="table",
                title="Work history",
                columns=[
                    "start_time",
                    "work_type",
                    "impact_level",
                    "result",
                    "summary",
                ],
                rows=[
                    [str(row[0]), row[1], str(row[2]), row[3] or "", row[4] or ""]
                    for row in work_rows
                ],
            )
        )
    if include_maint:
        tables.append(
            TableBlock(
                type="table",
                title="Maintenance history",
                columns=[
                    "start_time",
                    "maint_type",
                    "duration_min",
                    "result",
                    "summary",
                ],
                rows=[
                    [str(row[0]), row[1], str(row[2]), row[3] or "", row[4] or ""]
                    for row in maint_rows
                ],
            )
        )
    tables.append(
        TableBlock(
            type="table",
            title="Event log",
            columns=[
                "time",
                "ci_code",
                "ci_name",
                "severity",
                "event_type",
                "source",
                "title",
            ],
            rows=[
                [
                    str(row[0]),
                    row[5] or "-",
                    row[6] or "-",
                    str(row[1]),
                    row[2],
                    row[3],
                    row[4] or "",
                ]
                for row in event_rows
            ],
        )
    )
    return [markdown] + tables


def _build_references(
    work_rows: list[tuple],
    maint_rows: list[tuple],
    event_rows: list[tuple],
    tenant_id: str,
    ci,
    time_range,
    work_h_query: str,
    maint_h_query: str,
    event_l_query: str,
) -> ReferencesBlock:
    items = []
    params = [tenant_id, ci.ci_id, time_range.start, time_range.end]
    if work_rows:
        items.append(
            ReferenceItem(
                kind="sql",
                title="work history query",
                payload={"sql": work_h_query, "params": params},
            )
        )
    if maint_rows:
        items.append(
            ReferenceItem(
                kind="sql",
                title="maintenance history query",
                payload={"sql": maint_h_query, "params": params},
            )
        )
    if event_rows:
        items.append(
            ReferenceItem(
                kind="sql",
                title="event log query",
                payload={"sql": event_l_query, "params": params},
            )
        )
    return ReferencesBlock(
        type="references",
        title="History queries",
        items=items
        or [
            ReferenceItem(
                kind="sql",
                title="history query",
                payload={"sql": "No rows returned", "params": []},
            )
        ],
    )
