from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


class MarkdownBlock(BaseModel):
    type: Literal["markdown"]
    title: str | None = None
    content: str
    id: str | None = None


class TableBlock(BaseModel):
    type: Literal["table"]
    title: str | None = None
    columns: list[str]
    rows: list[list[str]]
    id: str | None = None


class TimeSeriesPoint(BaseModel):
    timestamp: str
    value: float


class TimeSeriesSeries(BaseModel):
    name: str | None = None
    data: list[TimeSeriesPoint]


class TimeSeriesBlock(BaseModel):
    type: Literal["timeseries"]
    title: str | None = None
    series: list[TimeSeriesSeries]
    id: str | None = None


class GraphPosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str
    data: dict[str, str]
    position: GraphPosition
    type: str | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class GraphBlock(BaseModel):
    type: Literal["graph"]
    title: str | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    id: str | None = None


class ReferenceItem(BaseModel):
    kind: Literal["sql", "cypher", "row"]
    title: str
    payload: Any


class ReferencesBlock(BaseModel):
    type: Literal["references"]
    title: str | None = None
    items: list[ReferenceItem]
    id: str | None = None


class TextBlock(BaseModel):
    type: Literal["text"]
    title: str | None = None
    id: str | None = None
    text: str


class NumberBlock(BaseModel):
    type: Literal["number"]
    title: str | None = None
    id: str | None = None
    value: float
    unit: str | None = None


class NetworkBlock(BaseModel):
    type: Literal["network"]
    title: str | None = None
    id: str | None = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    meta: dict[str, Any] = Field(default_factory=dict)


class PathBlock(BaseModel):
    type: Literal["path"]
    title: str | None = None
    id: str | None = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    hop_count: int


class ChartBlock(BaseModel):
    type: Literal["chart"]
    chart_type: Literal["line", "bar", "scatter"] = "line"
    title: str | None = None
    id: str | None = None
    x: str
    series: list[dict[str, Any]]
    meta: dict[str, Any] = Field(default_factory=dict)


AnswerBlock = Annotated[
    Union[
        MarkdownBlock,
        TableBlock,
        TimeSeriesBlock,
        GraphBlock,
        ReferencesBlock,
        TextBlock,
        NumberBlock,
        NetworkBlock,
        PathBlock,
        ChartBlock,
    ],
    Field(discriminator="type"),
]


class AnswerMeta(BaseModel):
    route: str
    route_reason: str
    timing_ms: int
    summary: str | None = None
    used_tools: list[str] = []
    fallback: bool = False
    error: str | None = None
    trace_id: str | None = None
    parent_trace_id: str | None = None


class AnswerEnvelope(BaseModel):
    meta: AnswerMeta
    blocks: list[AnswerBlock]
