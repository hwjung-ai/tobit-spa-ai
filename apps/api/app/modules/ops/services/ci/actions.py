from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict


class GraphLimitsPatch(TypedDict, total=False):
    max_nodes: int
    max_edges: int


class GraphPatch(TypedDict, total=False):
    depth: int
    limits: GraphLimitsPatch
    view: Literal["SUMMARY", "COMPOSITION", "DEPENDENCY", "IMPACT", "PATH", "NEIGHBORS"]


class AggregatePatch(TypedDict, total=False):
    group_by: List[str]
    top_n: int


class OutputPatch(TypedDict, total=False):
    primary: Literal["text", "table", "network", "path", "number", "markdown"]
    blocks: List[str]


class MetricPatch(TypedDict, total=False):
    time_range: Literal["last_1h", "last_24h", "last_7d"]
    agg: Literal["count", "max", "min", "avg"]
    mode: Literal["aggregate", "series"]
    scope: Literal["ci", "graph"]


class HistoryPatch(TypedDict, total=False):
    time_range: Literal["last_24h", "last_7d", "last_30d"]
    limit: int
    scope: Literal["ci", "graph"]


class ListPatch(TypedDict, total=False):
    offset: int
    limit: int


class RerunPatch(TypedDict, total=False):
    view: Literal["SUMMARY", "COMPOSITION", "DEPENDENCY", "IMPACT", "PATH", "NEIGHBORS"]
    graph: GraphPatch
    aggregate: AggregatePatch
    output: OutputPatch
    metric: MetricPatch
    history: HistoryPatch
    list: ListPatch


class RerunPayload(TypedDict, total=False):
    selected_ci_id: str
    selected_secondary_ci_id: str
    patch: RerunPatch


class RerunAction(TypedDict):
    type: Literal["rerun"]
    label: str
    payload: RerunPayload


class OpenTraceAction(TypedDict):
    type: Literal["open_trace"]
    label: str


class CopyPayloadAction(TypedDict):
    type: Literal["copy_payload"]
    label: str
    payload: Any


NextAction = RerunAction | OpenTraceAction | CopyPayloadAction
