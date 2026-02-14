"""
OPS Routes Utilities

Common utilities shared across OPS routes, including dependency providers,
helper functions, and common patterns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.auth import get_current_user
from core.config import get_settings
from core.tenant import get_current_tenant
from fastapi import Depends, HTTPException

from app.modules.auth.models import TbUser
from app.modules.ops.schemas import RerunPatch
from app.modules.ops.services.orchestration.planner.plan_schema import Plan


def _tenant_id(
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> str:
    """Resolve tenant_id from request state and verify against authenticated user."""
    settings = get_settings()
    if settings.enable_auth and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return tenant_id


def generate_references_from_tool_calls(
    tool_calls: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate references from tool calls for trace documentation.

    Each tool call represents a data access or operation that should be documented
    as a reference in the execution trace.

    Args:
        tool_calls: List of tool call dictionaries

    Returns:
        List of reference dictionaries
    """
    references = []
    for i, tool_call in enumerate(tool_calls or []):
        if not isinstance(tool_call, dict):
            continue

        tool_name = tool_call.get("tool") or tool_call.get("name") or f"tool_{i}"
        params = tool_call.get("params") or tool_call.get("arguments") or {}
        result = tool_call.get("result") or tool_call.get("output")

        ref = {
            "type": "tool_call",
            "tool_name": tool_name,
            "params": params if isinstance(params, dict) else {},
            "result_summary": str(result)[:200] if result else None,
            "index": i,
        }
        references.append(ref)

    return references


def apply_patch(plan: Plan, patch: Optional[RerunPatch]) -> Plan:
    """Apply a rerun patch to a plan, updating specific fields.

    This function handles selective updates to different parts of a plan,
    including graph, aggregate, output, metric, history, list, and auto patches.

    Args:
        plan: The original plan
        patch: The patch to apply (if None, returns plan unchanged)

    Returns:
        Updated plan with patch applied
    """
    if not patch:
        return plan

    updates: dict[str, Any] = {}

    # Apply view patch
    if patch.view:
        updates["view"] = patch.view

    # Apply graph patch
    if patch.graph:
        graph_updates: dict[str, Any] = {}
        if patch.graph.depth is not None:
            graph_updates["depth"] = patch.graph.depth
        if patch.graph.limits:
            graph_updates["limits"] = patch.graph.limits
        if patch.graph.view:
            graph_updates["view"] = patch.graph.view
        updates["graph"] = plan.graph.copy(update=graph_updates)

    # Apply aggregate patch
    if patch.aggregate:
        agg_updates: dict[str, Any] = {}
        if patch.aggregate.group_by:
            agg_updates["group_by"] = patch.aggregate.group_by
        if patch.aggregate.top_n is not None:
            agg_updates["top_n"] = patch.aggregate.top_n
        updates["aggregate"] = plan.aggregate.copy(update=agg_updates)

    # Apply output patch
    if patch.output:
        out_updates: dict[str, Any] = {}
        if patch.output.primary:
            out_updates["primary"] = patch.output.primary
        if patch.output.blocks:
            out_updates["blocks"] = patch.output.blocks
        updates["output"] = plan.output.copy(update=out_updates)

    # Apply metric patch
    if patch.metric and plan.metric:
        metric_updates: dict[str, Any] = {}
        if patch.metric.time_range:
            metric_updates["time_range"] = patch.metric.time_range
        if patch.metric.agg:
            metric_updates["agg"] = patch.metric.agg
        if patch.metric.mode:
            metric_updates["mode"] = patch.metric.mode
        if metric_updates:
            updates["metric"] = plan.metric.copy(update=metric_updates)

    # Apply history patch
    if patch.history and plan.history:
        history_updates: dict[str, Any] = {}
        if patch.history.time_range:
            history_updates["time_range"] = patch.history.time_range
        if patch.history.limit is not None:
            history_updates["limit"] = patch.history.limit
        if history_updates:
            updates["history"] = plan.history.copy(update=history_updates)

    # Apply list patch
    if patch.list and plan.list:
        list_updates: dict[str, Any] = {}
        if patch.list.offset is not None:
            list_updates["offset"] = patch.list.offset
        if patch.list.limit is not None:
            list_updates["limit"] = patch.list.limit
        if list_updates:
            updates["list"] = plan.list.copy(update=list_updates)

    # Apply auto patch
    if patch.auto:
        auto_updates: dict[str, Any] = {}
        if patch.auto.path:
            path_updates: dict[str, Any] = {}
            if patch.auto.path.source_ci_code is not None:
                path_updates["source_ci_code"] = patch.auto.path.source_ci_code
            if patch.auto.path.target_ci_code is not None:
                path_updates["target_ci_code"] = patch.auto.path.target_ci_code
            if path_updates:
                auto_updates["path"] = plan.auto.path.copy(update=path_updates)
        if patch.auto.graph_scope:
            graph_updates: dict[str, Any] = {}
            if patch.auto.graph_scope.include_metric is not None:
                graph_updates["include_metric"] = patch.auto.graph_scope.include_metric
            if patch.auto.graph_scope.include_history is not None:
                graph_updates["include_history"] = (
                    patch.auto.graph_scope.include_history
                )
            if graph_updates:
                auto_updates["graph_scope"] = plan.auto.graph_scope.copy(
                    update=graph_updates
                )
        if auto_updates:
            updates["auto"] = plan.auto.copy(update=auto_updates)

    return plan.copy(update=updates) if updates else plan
