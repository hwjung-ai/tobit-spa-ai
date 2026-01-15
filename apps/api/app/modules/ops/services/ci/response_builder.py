from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from apps.api.core.logging import get_logger

from schemas import ReferenceItem, ReferencesBlock

from app.modules.ops.services.ci.blocks import (
    network_block,
    number_block,
    path_block,
    table_block,
    text_block,
)


def _format_value(value: Any) -> str:
    if value is None:
        return "<null>"
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def build_candidate_table(candidates: Iterable[Dict[str, Any]], role: str = "primary") -> Dict[str, Any]:
    columns = ["ci_id", "ci_code", "ci_name", "ci_type", "ci_subtype", "ci_category", "status", "location", "owner"]
    rows: List[List[str]] = []
    for candidate in candidates:
        rows.append([_format_value(candidate.get(col)) for col in columns])
    role_label = {
        "source": "source endpoint",
        "target": "target endpoint",
        "secondary": "secondary endpoint",
        "primary": "primary endpoint",
    }.get(role.lower(), None)
    title = "CI candidates"
    if role_label:
        title = f"{title} ({role_label})"
    block_id = f"ci-candidates-{role}"
    return table_block(columns, rows, title=title, block_id=block_id)


def build_ci_detail_blocks(ci_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    identifiers = ["ci_code", "ci_name", "ci_type", "ci_subtype", "ci_category", "status", "location", "owner"]
    rows = [[field, _format_value(ci_detail.get(field))] for field in identifiers]
    detail_table = table_block(["field", "value"], rows, title="CI details")
    tags = ci_detail.get("tags") or {}
    attrs = ci_detail.get("attributes") or {}
    return [
        text_block(f"{ci_detail.get('ci_code')} · {ci_detail.get('ci_name')}", title="CI summary"),
        detail_table,
        table_block(
            ["tags", "value"],
            [[key, _format_value(value)] for key, value in tags.items()],
            title="Tags",
        )
        if tags
        else text_block("No tags available", title="Tags"),
        table_block(
            ["attributes", "value"],
            [[key, _format_value(value)] for key, value in attrs.items()],
            title="Attributes",
        )
        if attrs
        else text_block("No attributes available", title="Attributes"),
    ]


def build_aggregate_block(aggregate: Dict[str, Any]) -> Dict[str, Any]:
    columns = aggregate.get("columns", [])
    rows = aggregate.get("rows", [])
    total = aggregate.get("total")
    block = table_block(columns, rows, title="Aggregation results")
    if isinstance(total, int):
        return {
            **block,
            "meta": {"total_groups": total},
        }
    return block

def build_aggregate_summary_block(total_count: int) -> Dict[str, Any]:
    return number_block(
        label="전체 CI",
        value=total_count,
        title="전체 CI 수",
        block_id="ci-aggregate-total",
    )


logger = get_logger(__name__)


def build_network_blocks(graph_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    logger.info(
        "ci.graph.response_builder.version",
        extra={
            "marker": "RB_PATCH_20260112",
            "file": __file__,
            "pid": os.getpid(),
        },
    )
    payload_type = type(graph_payload).__name__
    if isinstance(graph_payload, dict):
        nodes = graph_payload.get("nodes", [])
        edges = graph_payload.get("edges", [])
        summary = graph_payload.get("summary", {})
        truncated = graph_payload.get("truncated", False)
        keys = list(graph_payload.keys())
    else:
        nodes = getattr(graph_payload, "nodes", [])
        edges = getattr(graph_payload, "edges", [])
        summary = getattr(graph_payload, "summary", {})
        truncated = getattr(graph_payload, "truncated", False)
        keys = [attr for attr in dir(graph_payload) if not attr.startswith("_")]
    logger.info(
        "ci.graph.network_blocks_payload",
        extra={
            "type": payload_type,
            "keys": keys,
            "nodes_len": len(nodes) if isinstance(nodes, list) else None,
            "edges_len": len(edges) if isinstance(edges, list) else None,
        },
    )
    if not isinstance(nodes, list) or not isinstance(edges, list):
        logger.error(
            "ci.graph.network_blocks_invalid_payload",
            extra={"type": payload_type, "nodes": nodes, "edges": edges},
        )
        return [text_block("Graph payload malformed", title="Graph expansion")]
    rel_counts = summary.get("rel_type_counts", {})
    blocks: List[Dict[str, Any]] = []
    blocks.append(
        network_block(
            nodes,
            edges,
            title="Graph expansion",
            truncated=truncated,
        )
    )
    block_meta = blocks[0].setdefault("meta", {})
    block_meta.update(
        {
            "response_builder_marker": "RB_PATCH_20260112",
            "response_builder_file": __file__,
            "response_builder_pid": os.getpid(),
            "truncated": truncated,
        }
    )
    if rel_counts:
        rows = [[rel_type, str(count)] for rel_type, count in rel_counts.items()]
        blocks.append(
            table_block(["relationship", "count"], rows, title="Relation counts")
        )
    return blocks


def build_path_blocks(path_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes = path_payload.get("nodes", [])
    edges = path_payload.get("edges", [])
    hop_count = path_payload.get("hop_count", 0)
    truncated = path_payload.get("truncated", False)
    summary = text_block(f"Hops: {hop_count}", title="Path summary")
    path_payload["meta"] = path_payload.get("meta") or {}
    path_payload["meta"]["truncated"] = truncated
    return [
        path_block(nodes, edges, hop_count, title="Shortest path", truncated=truncated),
        summary,
    ]


def build_answer_text(answer: str | None, fallback: str = "CI insight ready") -> Dict[str, Any]:
    return text_block(answer or fallback, title="Answer")

def build_sql_reference_block(sql: str, params: list[Any], title: str = "Aggregation query") -> dict[str, Any]:
    block = ReferencesBlock(
        type="references",
        title=title,
        items=[
            ReferenceItem(
                kind="sql",
                title=title,
                payload={"sql": sql, "params": params},
            )
        ],
    )
    return block.model_dump()
