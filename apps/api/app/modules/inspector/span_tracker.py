"""
Execution flow span tracking utility for Inspector telemetry.

Provides context-based span tracking to record execution stages:
- planner, validator, runner, executor, tool calls, answer assembly, ui_render

Spans are organized in a parent-child hierarchy and include timing, status, error info, and links.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from time import perf_counter
from typing import Any, Dict, List

_span_stack: ContextVar[List[Dict[str, Any]]] = ContextVar("span_stack", default=[])


def _get_epoch_ms() -> int:
    """Get current time in milliseconds since epoch."""
    return int(perf_counter() * 1000)


def start_span(
    name: str,
    kind: str,
    parent_span_id: str | None = None,
) -> str:
    """
    Start a new span and return span_id.

    Args:
        name: Span name (e.g., "planner", "validator", "runner", "tool:sql", "tool:http")
        kind: Span kind (e.g., "stage", "tool", "render")
        parent_span_id: Parent span ID if this is a child span

    Returns:
        span_id (8-char shortid)
    """
    span_id = str(uuid.uuid4())[:8]
    ts_start_ms = _get_epoch_ms()

    span: Dict[str, Any] = {
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "kind": kind,
        "status": "ok",
        "ts_start_ms": ts_start_ms,
        "ts_end_ms": ts_start_ms,
        "duration_ms": 0,
        "summary": {},
        "links": {},
    }

    stack = list(_span_stack.get())
    stack.append(span)
    _span_stack.set(stack)

    return span_id


def end_span(
    span_id: str,
    status: str = "ok",
    summary: Dict[str, Any] | None = None,
    links: Dict[str, Any] | None = None,
) -> None:
    """
    End a span by span_id and update its metadata.

    Args:
        span_id: Span ID to end
        status: Final status ("ok" or "error")
        summary: Summary dict with note, error_type, error_message, etc.
        links: Links dict with plan_path, tool_call_id, block_id, etc.
    """
    stack = list(_span_stack.get())

    for span in reversed(stack):
        if span["span_id"] == span_id:
            ts_end_ms = _get_epoch_ms()
            span["ts_end_ms"] = ts_end_ms
            span["duration_ms"] = ts_end_ms - span["ts_start_ms"]
            span["status"] = status

            if summary:
                span["summary"].update(summary)
            if links:
                span["links"].update(links)

            _span_stack.set(stack)
            return

    # Span not found (should not happen in normal flow)
    _span_stack.set(stack)


def get_all_spans() -> List[Dict[str, Any]]:
    """
    Retrieve all collected spans in order.

    Returns:
        List of span dicts
    """
    return list(_span_stack.get())


def clear_spans() -> None:
    """Clear all spans (call at start of new trace)."""
    _span_stack.set([])


def get_current_span_id() -> str | None:
    """Get the ID of the most recent (active) span."""
    stack = _span_stack.get()
    if stack:
        return stack[-1]["span_id"]
    return None
