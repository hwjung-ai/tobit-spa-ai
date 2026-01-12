from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from core.db_pg import get_pg_connection
from schemas import (
    AnswerBlock,
    GraphBlock,
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TableBlock,
)

from ..resolvers import resolve_ci, resolve_time_range
from ..ci.tools import history as history_tools


def run_hist(question: str, tenant_id: str = "t1") -> tuple[list[AnswerBlock], list[str]]:
    ci_hits = resolve_ci(question, tenant_id=tenant_id, limit=1)
    if not ci_hits:
        fallback_blocks = _build_history_fallback(tenant_id, question)
        return fallback_blocks, ["postgres", "timescale"]
    ci = ci_hits[0]
    time_range = resolve_time_range(question, datetime.now(timezone.utc))
    work_rows = _fetch_history(
        """
        SELECT start_time, work_type, impact_level, result, summary
        FROM work_history
        WHERE tenant_id = %s AND ci_id = %s AND start_time >= %s AND start_time < %s
        ORDER BY start_time DESC
        LIMIT 50
        """,
        (tenant_id, ci.ci_id, time_range.start, time_range.end),
    )
    maint_rows = _fetch_history(
        """
        SELECT start_time, maint_type, duration_min, result, summary
        FROM maintenance_history
        WHERE tenant_id = %s AND ci_id = %s AND start_time >= %s AND start_time < %s
        ORDER BY start_time DESC
        LIMIT 50
        """,
        (tenant_id, ci.ci_id, time_range.start, time_range.end),
    )
    event_rows = _fetch_history(
        """
        SELECT el.time, el.severity, el.event_type, el.source, el.title, c.ci_code, c.ci_name
        FROM event_log AS el
        LEFT JOIN ci AS c ON c.ci_id = el.ci_id
        WHERE el.tenant_id = %s AND el.ci_id = %s AND el.time >= %s AND el.time < %s
        ORDER BY el.severity DESC, el.time DESC
        LIMIT 50
        """,
        (tenant_id, ci.ci_id, time_range.start, time_range.end),
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
    blocks = _build_blocks(ci, time_range, stats, work_rows, maint_rows, event_rows, include_work, include_maint)
    references = _build_references(work_rows, maint_rows, event_rows, tenant_id, ci, time_range)
    blocks.append(references)
    return blocks, ["postgres", "timescale"]


def _fetch_history(query: str, params: Iterable) -> list[tuple]:
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()


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
                columns=["start_time", "work_type", "impact_level", "result", "summary"],
                rows=[[str(row[0]), row[1], str(row[2]), row[3] or "", row[4] or ""] for row in work_rows],
            )
        )
    if include_maint:
        tables.append(
            TableBlock(
                type="table",
                title="Maintenance history",
                columns=["start_time", "maint_type", "duration_min", "result", "summary"],
                rows=[[str(row[0]), row[1], str(row[2]), row[3] or "", row[4] or ""] for row in maint_rows],
            )
        )
    tables.append(
        TableBlock(
            type="table",
            title="Event log",
            columns=["time", "ci_code", "ci_name", "severity", "event_type", "source", "title"],
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
) -> ReferencesBlock:
    items = []
    if work_rows:
        items.append(
            ReferenceItem(
                kind="sql",
                title="work history query",
                payload={
                    "sql": "SELECT start_time,... FROM work_history ...",
                    "params": [tenant_id, ci.ci_id, time_range.start, time_range.end],
                },
            )
        )
    if maint_rows:
        items.append(
            ReferenceItem(
                kind="sql",
                title="maintenance history query",
                payload={
                    "sql": "SELECT start_time,... FROM maintenance_history ...",
                    "params": [tenant_id, ci.ci_id, time_range.start, time_range.end],
                },
            )
        )
    if event_rows:
        items.append(
            ReferenceItem(
                kind="sql",
                title="event log query",
                payload={
                    "sql": "SELECT time,... FROM event_log ...",
                    "params": [tenant_id, ci.ci_id, time_range.start, time_range.end],
                },
            )
        )
    return ReferencesBlock(type="references", title="History queries", items=items or [
        ReferenceItem(kind="sql", title="history query", payload={"sql": "No rows returned", "params": []})
    ])


def _build_history_fallback(tenant_id: str, question: str) -> list[AnswerBlock]:
    history = history_tools.recent_work_and_maintenance(tenant_id, "last_7d", limit=50)
    work_rows = history.get("work_rows", [])
    maint_rows = history.get("maint_rows", [])
    sections = history_tools.detect_history_sections(question)
    include_work = "work" in sections or not sections
    include_maint = "maintenance" in sections or not sections
    blocks: list[AnswerBlock] = [
        MarkdownBlock(
            type="markdown",
            title="전체 이력 fallback",
            content="CI 없이 전체 이력을 보여드립니다.",
        ),
    ]
    if include_work:
        blocks.append(
            TableBlock(
                type="table",
                title="Work history (최근 7일)",
                columns=["start_time", "ci_code", "ci_name", "work_type", "impact_level", "result", "summary"],
                rows=[
                    [
                        str(row[0]),
                        row[1] or "-",
                        row[2] or "-",
                        row[3],
                        str(row[4]),
                        row[5] or "",
                        row[6] or "",
                    ]
                    for row in work_rows
                ]
                or [["데이터 없음", "-", "-", "-", "-", "-", "-"]],
            )
        )
    if include_maint:
        blocks.append(
            TableBlock(
                type="table",
                title="Maintenance history (최근 7일)",
                columns=["start_time", "ci_code", "ci_name", "maint_type", "duration_min", "result", "summary"],
                rows=[
                    [
                        str(row[0]),
                        row[1] or "-",
                        row[2] or "-",
                        row[3],
                        str(row[4]),
                        row[5] or "",
                        row[6] or "",
                    ]
                    for row in maint_rows
                ]
                or [["데이터 없음", "-", "-", "-", "-", "-", "-"]],
            )
        )
    return blocks
