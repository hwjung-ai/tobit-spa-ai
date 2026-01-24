"""Tool execution contract definitions.

This module defines standard Pydantic schemas for tool return values,
enabling type-safe tool integration and API contracts.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


# Graph Tool Contracts
class GraphExpandResult(BaseModel):
    """Result of graph expansion operation."""

    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    ids: List[str]
    summary: Dict[str, Any]
    truncated: bool
    meta: Dict[str, Any] = Field(default_factory=dict)


class GraphPathResult(BaseModel):
    """Result of graph path operation."""

    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    hop_count: int
    truncated: bool
    meta: Dict[str, Any] = Field(default_factory=dict)


# Metric Tool Contracts
class MetricAggregateResult(BaseModel):
    """Result of metric aggregation."""

    metric_name: str
    agg: str
    time_range: str
    time_from: str  # ISO format
    time_to: str  # ISO format
    ci_count_used: int
    ci_ids_truncated: bool
    ci_requested: int
    value: float | None = None
    ci_ids: List[str]


class MetricSeriesResult(BaseModel):
    """Result of metric series query."""

    metric_name: str
    time_range: str
    rows: List[tuple[str, str]]  # (timestamp_iso, value)


# CI Tool Contracts
class CIRecord(BaseModel):
    """CI configuration record."""

    ci_id: str
    ci_code: str
    ci_name: str
    ci_type: str
    ci_subtype: str | None = None
    ci_category: str | None = None
    status: str | None = None
    location: str | None = None
    owner: str | None = None
    tags: Dict[str, Any] = Field(default_factory=dict)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class CISearchResult(BaseModel):
    """Result of CI search operation."""

    records: List[CIRecord]
    total: int
    query: str | None = None
    params: List[Any] = Field(default_factory=list)


class CIAggregateResult(BaseModel):
    """Result of CI aggregation."""

    columns: List[str]
    rows: List[List[Any]]
    total: int
    query: str
    params: List[Any]


class CIListResult(BaseModel):
    """Result of CI list operation."""

    rows: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    query: str
    params: List[Any]


# History Tool Contracts
class HistoryRecord(BaseModel):
    """Historical change record."""

    timestamp: str  # ISO format
    event_type: str
    ci_id: str
    ci_code: str
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)


class HistoryResult(BaseModel):
    """Result of history query."""

    records: List[HistoryRecord]
    total: int
    time_range: str


# Tool Execution Trace
class ToolCall(BaseModel):
    """Record of a single tool execution."""

    tool: str  # e.g., "ci.search", "graph.expand", "metric.aggregate"
    elapsed_ms: int
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_summary: Dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    query_asset: str | None = (
        None  # Query asset identifier: "{asset_id}:v{version}" if used
    )


class ToolCallTrace(BaseModel):
    """Complete trace of tool executions."""

    tool_calls: List[ToolCall]
    total_elapsed_ms: int
    total_calls: int


# Executor Results
class ExecutorResult(BaseModel):
    """Standard result format from OPS executors (metric, hist, graph).

    Wraps blocks with Tool Contract metadata for standardized execution tracking.
    """

    blocks: List[Dict[str, Any]]  # Answer blocks to display
    used_tools: List[
        str
    ]  # Tools used during execution (e.g., ["postgres", "timescale"])
    tool_calls: List[ToolCall] = Field(default_factory=list)  # Tool execution trace
    references: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # Extracted references
    summary: Dict[str, Any] = Field(default_factory=dict)  # Execution summary
