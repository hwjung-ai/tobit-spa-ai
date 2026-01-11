from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict


class TextBlock(TypedDict, total=False):
    type: Literal["text"]
    title: str
    id: str
    text: str


class NumberBlock(TypedDict, total=False):
    type: Literal["number"]
    title: str
    id: str
    label: str
    value: float | int


class TableBlock(TypedDict, total=False):
    type: Literal["table"]
    title: str
    id: str
    columns: List[str]
    rows: List[List[str]]


class NetworkBlock(TypedDict, total=False):
    type: Literal["network"]
    title: str
    id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    meta: Dict[str, Any]


class PathBlock(TypedDict, total=False):
    type: Literal["path"]
    title: str
    id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    hop_count: int
    meta: Dict[str, Any]


Block = TextBlock | NumberBlock | TableBlock | NetworkBlock | PathBlock


def text_block(text: str, title: str | None = None, block_id: str | None = None) -> TextBlock:
    payload: TextBlock = {"type": "text", "text": text}
    if title:
        payload["title"] = title
    if block_id:
        payload["id"] = block_id
    return payload


class ChartSeries(TypedDict, total=False):
    name: str
    points: List[List[Any]]


class ChartMeta(TypedDict, total=False):
    ci_id: str
    metric_name: str
    time_range: str


class ChartBlock(TypedDict, total=False):
    type: Literal["chart"]
    title: str
    chart_type: Literal["line"]
    x: str
    series: List[ChartSeries]
    meta: ChartMeta
    id: str


def chart_block(
    title: str,
    x: str,
    series: List[ChartSeries],
    meta: ChartMeta,
    chart_type: Literal["line"] = "line",
    block_id: str | None = None,
) -> ChartBlock:
    payload: ChartBlock = {
        "type": "chart",
        "chart_type": chart_type,
        "title": title,
        "x": x,
        "series": series,
        "meta": meta,
    }
    if block_id:
        payload["id"] = block_id
    return payload


def number_block(label: str, value: float | int, title: str | None = None, block_id: str | None = None) -> NumberBlock:
    payload: NumberBlock = {"type": "number", "label": label, "value": value}
    if title:
        payload["title"] = title
    if block_id:
        payload["id"] = block_id
    return payload


def table_block(
    columns: List[str],
    rows: List[List[str]],
    title: str | None = None,
    block_id: str | None = None,
) -> TableBlock:
    payload: TableBlock = {"type": "table", "columns": columns, "rows": rows}
    if title:
        payload["title"] = title
    if block_id:
        payload["id"] = block_id
    return payload


def network_block(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    title: str | None = None,
    truncated: bool = False,
    block_id: str | None = None,
) -> NetworkBlock:
    payload: NetworkBlock = {
        "type": "network",
        "nodes": nodes,
        "edges": edges,
        "meta": {"truncated": truncated},
    }
    if title:
        payload["title"] = title
    if block_id:
        payload["id"] = block_id
    return payload


def path_block(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    hop_count: int,
    title: str | None = None,
    truncated: bool = False,
    block_id: str | None = None,
) -> PathBlock:
    payload: PathBlock = {
        "type": "path",
        "nodes": nodes,
        "edges": edges,
        "hop_count": hop_count,
        "meta": {"truncated": truncated},
    }
    if title:
        payload["title"] = title
    if block_id:
        payload["id"] = block_id
    return payload
