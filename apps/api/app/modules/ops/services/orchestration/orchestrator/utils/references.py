"""Reference extraction and handling utilities.

This module handles extraction, fallback, and formatting of references
from tool calls and execution blocks.
"""

from typing import Any, Dict, List

from schemas.tool_contracts import ToolCall

from app.modules.ops.services.orchestration.blocks import Block


def extract_references_from_blocks(blocks: List[Block]) -> List[Dict[str, Any]]:
    """Extract references from execution blocks.

    Args:
        blocks: List of execution blocks

    Returns:
        List of reference dictionaries
    """
    references: List[Dict[str, Any]] = []

    for block in blocks:
        if isinstance(block, dict):
            block_type = block.get("type")
            if block_type == "references":
                items = block.get("items", [])
                for item in items:
                    if (
                        isinstance(item, dict)
                        and "kind" in item
                        and "payload" in item
                    ):
                        references.append(item)
        else:
            # Pydantic model
            block_type = getattr(block, "type", None)
            if block_type == "references":
                items = getattr(block, "items", [])
                for item in items:
                    item_dict = item.dict() if hasattr(item, "dict") else dict(item)
                    if "kind" in item_dict and "payload" in item_dict:
                        references.append(item_dict)

    return references


def reference_from_tool_call(call: ToolCall) -> Dict[str, Any] | None:
    """Build reference from tool call.

    Args:
        call: Tool call to extract reference from

    Returns:
        Reference dictionary or None
    """
    tool_name = call.tool or "unknown"
    input_params = call.input_params or {}
    output_summary = call.output_summary or {}

    payload: Dict[str, Any] = {
        "tool": tool_name,
        "input": input_params,
        "summary": output_summary,
    }

    if call.query_asset:
        payload["query_asset"] = call.query_asset

    statement_fingerprint = output_summary.get("statement_fingerprint")
    if statement_fingerprint:
        payload["statement_fingerprint"] = statement_fingerprint

    # Tool-specific payload enrichment
    if tool_name == "metric.aggregate":
        payload.update(
            {
                "metric_name": input_params.get("metric_name"),
                "agg": input_params.get("agg"),
                "time_range": input_params.get("time_range"),
                "ci_ids_count": input_params.get("ci_ids_count"),
            }
        )
        title = "metric.aggregate"
    elif tool_name == "metric.series":
        payload.update(
            {
                "metric_name": input_params.get("metric_name"),
                "time_range": input_params.get("time_range"),
                "limit": input_params.get("limit"),
            }
        )
        title = "metric.series"
    elif tool_name == "history.recent":
        payload.update(
            {
                "time_range": input_params.get("time_range"),
                "scope": input_params.get("scope"),
                "limit": input_params.get("limit"),
                "ci_ids_count": input_params.get("ci_ids_count"),
            }
        )
        title = "history.recent"
    elif tool_name == "graph.expand":
        payload.update(
            {
                "view": input_params.get("view"),
                "depth": input_params.get("depth"),
            }
        )
        title = "graph.expand"
    elif tool_name == "graph.path":
        payload.update(
            {
                "hop_count": input_params.get("hops"),
            }
        )
        title = "graph.path"
    elif tool_name == "ci.search":
        payload.update(
            {
                "keywords": input_params.get("keywords"),
                "filter_count": input_params.get("filter_count"),
                "limit": input_params.get("limit"),
            }
        )
        title = "ci.search"
    elif tool_name == "ci.list":
        payload.update(
            {
                "limit": input_params.get("limit"),
                "offset": input_params.get("offset"),
                "filter_count": input_params.get("filter_count"),
            }
        )
        title = "ci.list"
    else:
        title = tool_name

    return {"kind": "row", "title": title, "payload": payload}


def ensure_reference_fallback(
    references: List[Dict[str, Any]], tool_calls: List[ToolCall]
) -> List[Dict[str, Any]]:
    """Ensure references exist, with fallback to tool calls.

    If no references exist, creates references from tool calls.
    If still no references, creates a generic tool calls reference.

    Args:
        references: Existing references
        tool_calls: Tool calls to create references from

    Returns:
        Updated references list
    """
    if references:
        return references

    # Build references from tool calls
    for call in tool_calls:
        reference = reference_from_tool_call(call)
        if reference:
            references.append(reference)

    # Final fallback: generic tool calls reference
    if not references and tool_calls:
        payload = {
            "tool_calls": [call.model_dump() for call in tool_calls],
        }
        references.append({"kind": "row", "title": "tool.calls", "payload": payload})

    return references
