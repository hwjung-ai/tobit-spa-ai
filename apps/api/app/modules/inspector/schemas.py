from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FlowSpan(BaseModel):
    """Execution flow span for timeline visualization."""

    span_id: str
    parent_span_id: str | None = None
    name: str
    kind: str
    status: str
    ts_start_ms: int
    ts_end_ms: int
    duration_ms: int
    summary: Dict[str, Any] = Field(default_factory=dict)
    links: Dict[str, Any] = Field(default_factory=dict)


class TraceSummary(BaseModel):
    trace_id: str
    created_at: datetime
    feature: str
    status: str
    duration_ms: int
    question_snippet: str
    applied_asset_versions: List[str] = Field(default_factory=list)


class ExecutionTraceRead(BaseModel):
    trace_id: str
    parent_trace_id: str | None
    created_at: datetime
    feature: str
    endpoint: str
    method: str
    ops_mode: str
    question: str
    status: str
    duration_ms: int
    request_payload: Dict[str, Any] | None
    applied_assets: Dict[str, Any] | None
    asset_versions: List[str] | None
    fallbacks: Dict[str, bool] | None
    plan_raw: Dict[str, Any] | None
    plan_validated: Dict[str, Any] | None
    execution_steps: List[Dict[str, Any]] | None
    references: List[Dict[str, Any]] | None
    answer: Dict[str, Any] | None
    ui_render: Dict[str, Any] | None
    audit_links: Dict[str, Any] | None
    flow_spans: List[FlowSpan] | None = None
    route: str | None = None
    stage_inputs: List[Dict[str, Any]] | None = None
    stage_outputs: List[Dict[str, Any]] | None = None
    replan_events: List[Dict[str, Any]] | None = None


class TraceListRequest(BaseModel):
    q: str | None = None
    feature: str | None = None
    status: str | None = None
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    limit: int = 20
    offset: int = 0
    asset_id: str | None = None
    parent_trace_id: str | None = None


class UIRenderPayload(BaseModel):
    rendered_blocks: List[Dict[str, Any]]
    warnings: List[str] = Field(default_factory=list)
