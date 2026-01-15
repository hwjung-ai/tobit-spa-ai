from __future__ import annotations

from typing import Any, Dict, List, Tuple

import re

from core.logging import get_logger
from app.modules.ops.services.ci import policy
from app.modules.ops.services.ci.planner.plan_schema import (
    AutoSpec,
    BudgetSpec,
    Intent,
    ListSpec,
    Plan,
    PlanBranch,
    PlanLoop,
    PlanMode,
    PlanStep,
    StepCondition,
    View,
)

AUTO_METRIC_CANDIDATES = ["cpu_usage", "latency", "error"]
AUTO_ALLOWED_GRAPH_VIEWS = {View.COMPOSITION, View.DEPENDENCY, View.IMPACT, View.NEIGHBORS, View.PATH}
AUTO_VIEW_DEFAULT_DEPTHS = {
    View.COMPOSITION: 2,
    View.DEPENDENCY: 2,
    View.IMPACT: 2,
    View.NEIGHBORS: 1,
    View.PATH: 2,
}

logger = get_logger(__name__)


def _clamp_limit(value: int | None, default: int = 5, maximum: int = 50) -> int:
    if value is None:
        return default
    return max(1, min(maximum, value))


def _clamp_list_limit(value: int | None) -> int:
    if value is None:
        return 50
    return max(1, min(50, value))


def _clamp_list_offset(value: int | None) -> int:
    if value is None:
        return 0
    return max(0, min(5000, value))


def _clamp_auto_views(views: List[View]) -> List[View]:
    clamped: List[View] = []
    for view in views:
        if view not in AUTO_ALLOWED_GRAPH_VIEWS:
            continue
        if view not in clamped:
            clamped.append(view)
        if len(clamped) >= 2:
            break
    if not clamped:
        clamped = [View.NEIGHBORS]
    return clamped


def _validate_step_ids_unique(plan: Plan) -> tuple[bool, List[str]]:
    """Check if all step IDs in plan are unique"""
    seen_ids: set[str] = set()
    duplicates: List[str] = []

    for step in plan.steps:
        if step.step_id in seen_ids:
            duplicates.append(step.step_id)
        seen_ids.add(step.step_id)

    for branch in plan.branches:
        if branch.branch_id in seen_ids:
            duplicates.append(branch.branch_id)
        seen_ids.add(branch.branch_id)
        for step in branch.steps:
            if step.step_id in seen_ids:
                duplicates.append(step.step_id)
            seen_ids.add(step.step_id)

    for loop in plan.loops:
        if loop.loop_id in seen_ids:
            duplicates.append(loop.loop_id)
        seen_ids.add(loop.loop_id)
        for step in loop.steps:
            if step.step_id in seen_ids:
                duplicates.append(step.step_id)
            seen_ids.add(step.step_id)

    return len(duplicates) == 0, duplicates


def _validate_step_references(plan: Plan) -> tuple[bool, List[str]]:
    """Check if all step references point to existing steps"""
    all_step_ids: set[str] = set()

    for step in plan.steps:
        all_step_ids.add(step.step_id)

    for branch in plan.branches:
        all_step_ids.add(branch.branch_id)
        for step in branch.steps:
            all_step_ids.add(step.step_id)

    for loop in plan.loops:
        all_step_ids.add(loop.loop_id)
        for step in loop.steps:
            all_step_ids.add(step.step_id)

    errors: List[str] = []

    for step in plan.steps:
        if step.next_step_id and step.next_step_id not in all_step_ids:
            errors.append(f"Step {step.step_id} references unknown next_step_id: {step.next_step_id}")
        if step.error_next_step_id and step.error_next_step_id not in all_step_ids:
            errors.append(f"Step {step.step_id} references unknown error_next_step_id: {step.error_next_step_id}")

    for branch in plan.branches:
        if branch.merge_step_id and branch.merge_step_id not in all_step_ids:
            errors.append(f"Branch {branch.branch_id} references unknown merge_step_id: {branch.merge_step_id}")
        for step in branch.steps:
            if step.next_step_id and step.next_step_id not in all_step_ids:
                errors.append(f"Step {step.step_id} in branch {branch.branch_id} references unknown next_step_id: {step.next_step_id}")

    for loop in plan.loops:
        if loop.next_step_id and loop.next_step_id not in all_step_ids:
            errors.append(f"Loop {loop.loop_id} references unknown next_step_id: {loop.next_step_id}")

    return len(errors) == 0, errors


def _validate_budget_constraints(plan: Plan) -> tuple[bool, List[str]]:
    """Check budget constraints including timeout and depth policies"""
    errors: List[str] = []
    budget = plan.budget

    total_steps = len(plan.steps)
    for branch in plan.branches:
        total_steps += len(branch.steps)
    for loop in plan.loops:
        total_steps += len(loop.steps) * loop.max_iterations

    if total_steps > budget.max_steps:
        errors.append(f"Total steps ({total_steps}) exceeds max_steps budget ({budget.max_steps})")

    if len(plan.branches) > budget.max_branches:
        errors.append(f"Number of branches ({len(plan.branches)}) exceeds max_branches budget ({budget.max_branches})")

    for loop in plan.loops:
        if loop.max_iterations > budget.max_iterations:
            errors.append(f"Loop {loop.loop_id} max_iterations ({loop.max_iterations}) exceeds budget ({budget.max_iterations})")

    # Validate timeout_seconds
    if budget.timeout_seconds is not None:
        if budget.timeout_seconds < 1:
            errors.append(f"timeout_seconds ({budget.timeout_seconds}) must be >= 1")
        elif budget.timeout_seconds > 3600:
            errors.append(f"timeout_seconds ({budget.timeout_seconds}) exceeds maximum of 3600 seconds (1 hour)")

    # Validate max_depth
    if budget.max_depth < 1:
        errors.append(f"max_depth ({budget.max_depth}) must be >= 1")
    elif budget.max_depth > 10:
        errors.append(f"max_depth ({budget.max_depth}) exceeds maximum of 10")

    return len(errors) == 0, errors


def _validate_multistep_structure(plan: Plan) -> tuple[bool, Dict[str, Any]]:
    """Validate multi-step plan structure"""
    trace: Dict[str, Any] = {}

    if not plan.enable_multistep:
        trace["multistep_enabled"] = False
        return True, trace

    trace["multistep_enabled"] = True

    # Check unique IDs
    unique_ok, duplicate_ids = _validate_step_ids_unique(plan)
    trace["unique_ids"] = {
        "valid": unique_ok,
        "duplicates": duplicate_ids if duplicate_ids else None,
    }

    # Check references
    refs_ok, ref_errors = _validate_step_references(plan)
    trace["references"] = {
        "valid": refs_ok,
        "errors": ref_errors if ref_errors else None,
    }

    # Check budget
    budget_ok, budget_errors = _validate_budget_constraints(plan)
    trace["budget"] = {
        "valid": budget_ok,
        "errors": budget_errors if budget_errors else None,
        "constraints": {
            "max_steps": plan.budget.max_steps,
            "max_branches": plan.budget.max_branches,
            "max_iterations": plan.budget.max_iterations,
            "timeout_seconds": plan.budget.timeout_seconds,
        },
    }

    # Count structure
    trace["structure"] = {
        "total_steps": len(plan.steps),
        "total_branches": len(plan.branches),
        "total_loops": len(plan.loops),
        "steps_in_branches": sum(len(b.steps) for b in plan.branches),
        "steps_in_loops": sum(len(l.steps) for l in plan.loops),
    }

    is_valid = unique_ok and refs_ok and budget_ok
    return is_valid, trace


def _apply_auto_mode(plan: Plan, auto_spec: AutoSpec) -> tuple[Plan, Dict[str, Any]]:
    views_requested = auto_spec.views or []
    applied_views = _clamp_auto_views(views_requested)
    depth_hint = auto_spec.depth_hint
    depth_map: Dict[str, int] = {}
    for view in applied_views:
        requested_depth = depth_hint or AUTO_VIEW_DEFAULT_DEPTHS.get(view, 2)
        depth_map[view.value] = policy.clamp_depth(view.value, requested_depth)
    primary_view = applied_views[0] if applied_views else View.NEIGHBORS
    primary_depth = depth_map.get(primary_view.value, policy.clamp_depth(primary_view.value, depth_hint or 2))
    normalized_graph = plan.graph.copy(update={"view": primary_view, "depth": primary_depth})
    applied_path = auto_spec.path
    path_warnings: List[str] = []
    if (
        applied_path.source_ci_code
        and applied_path.target_ci_code
        and applied_path.source_ci_code.lower() == applied_path.target_ci_code.lower()
    ):
        applied_path = applied_path.copy(update={"target_ci_code": None})
        path_warnings.append("Target CI matches source; target cleared")
    applied_auto = auto_spec.copy(update={"views": applied_views, "path": applied_path})
    updated_plan = plan.copy(update={"graph": normalized_graph, "auto": applied_auto})
    metric_spec = updated_plan.metric
    metric_trace: Dict[str, Any] = {
        "include_metric_requested": auto_spec.include_metric,
        "metric_mode_requested": auto_spec.metric_mode,
        "spec_present": bool(metric_spec),
    }
    if not auto_spec.include_metric:
        metric_spec = None
        metric_trace["status"] = "disabled"
    elif metric_spec:
        mode_applied = auto_spec.metric_mode if auto_spec.metric_mode in {"aggregate", "series"} else metric_spec.mode
        if metric_spec.mode != mode_applied:
            metric_spec = metric_spec.copy(update={"mode": mode_applied})
        metric_trace["status"] = "enabled"
        metric_trace["mode_applied"] = metric_spec.mode
    updated_plan = updated_plan.copy(update={"metric": metric_spec})
    history_spec = updated_plan.history
    history_trace: Dict[str, Any] = {"include_history_requested": auto_spec.include_history}
    if auto_spec.include_history:
        history_updates = {"enabled": True}
        if not history_spec.enabled:
            history_updates.update(
                {
                    "scope": "ci",
                    "mode": "recent",
                    "time_range": "last_7d",
                    "limit": 20,
                }
            )
        history_spec = history_spec.copy(update=history_updates)
        history_trace.update(
            {
                "status": "enabled",
                "time_range": history_spec.time_range,
                "limit": history_spec.limit,
            }
        )
    else:
        history_spec = history_spec.copy(update={"enabled": False})
        history_trace.update({"status": "disabled"})
    updated_plan = updated_plan.copy(update={"history": history_spec})
    cep_spec = updated_plan.cep
    cep_enabled = bool(auto_spec.include_cep and cep_spec and cep_spec.rule_id)
    if not cep_enabled:
        cep_spec = None
    updated_plan = updated_plan.copy(update={"cep": cep_spec})
    cep_trace = {
        "include_cep_requested": auto_spec.include_cep,
        "enabled": cep_enabled,
        "rule_id": cep_spec.rule_id if cep_spec else None,
    }
    path_spec = auto_spec.path
    graph_scope_spec = auto_spec.graph_scope
    auto_trace = {
        "auto_recipe_applied": True,
        "views": {
            "requested": [view.value for view in views_requested],
            "applied": [view.value for view in applied_views],
            "depth_hint_requested": depth_hint,
            "depths": depth_map,
        },
        "metrics": metric_trace,
        "history": history_trace,
        "cep": cep_trace,
        "path": {
            "requested": path_spec.dict(),
            "applied": applied_path.dict(),
            "warnings": path_warnings if path_warnings else None,
        },
        "graph_scope": {
            "requested": graph_scope_spec.dict(),
            "applied": graph_scope_spec.dict(),
        },
    }
    return updated_plan, auto_trace


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_absolute_date(value: str) -> bool:
    return bool(DATE_PATTERN.match(value))


def validate_plan(plan: Plan) -> Tuple[Plan, Dict[str, Any]]:
    normalized = plan.copy()
    mode = normalized.mode
    logger.info(
        "ci.validator.start",
        extra={
            "mode": mode.value if mode else None,
            "intent": normalized.intent.value if normalized.intent else None,
            "multistep_enabled": normalized.enable_multistep,
        },
    )
    # Validate multi-step structure first if enabled
    multistep_valid, multistep_trace = _validate_multistep_structure(normalized)
    if normalized.enable_multistep and not multistep_valid:
        error_msgs = []
        if multistep_trace.get("unique_ids", {}).get("duplicates"):
            error_msgs.append(f"Duplicate step IDs: {multistep_trace['unique_ids']['duplicates']}")
        if multistep_trace.get("references", {}).get("errors"):
            error_msgs.extend(multistep_trace["references"]["errors"])
        if multistep_trace.get("budget", {}).get("errors"):
            error_msgs.extend(multistep_trace["budget"]["errors"])
        raise ValueError(f"Multi-step plan validation failed: {'; '.join(error_msgs)}")
    if normalized.intent == Intent.PATH:
        normalized.view = View.PATH
    view = normalized.view or View.SUMMARY
    primary_limit = _clamp_limit(normalized.primary.limit)
    graph_view = normalized.graph.view or view
    requested_depth = normalized.graph.depth
    clamped_depth = policy.clamp_depth(graph_view.value, requested_depth)
    if clamped_depth != requested_depth:
        logger.info(
            "ci.validator.clamp",
            extra={
                "field": "graph.depth",
                "from": requested_depth,
                "to": clamped_depth,
                "policy_code": "depth_clamp",
            },
        )
    normalized = normalized.copy(
        update={
            "primary": normalized.primary.copy(update={"limit": primary_limit}),
            "view": view,
            "graph": normalized.graph.copy(update={"view": graph_view, "depth": clamped_depth}),
        }
    )
# Auto mode adjustments
    auto_trace: Dict[str, Any] | None = None
    if mode == PlanMode.AUTO:
        normalized, auto_trace = _apply_auto_mode(normalized, normalized.auto)
    view = normalized.view or View.SUMMARY
    graph_view = normalized.graph.view or view
    requested_depth = normalized.graph.depth
    trace: Dict[str, Any] = {
        "policy_decisions": policy.build_policy_trace(graph_view.value, requested_depth)
    }
    graph_views = {View.COMPOSITION, View.DEPENDENCY, View.IMPACT, View.NEIGHBORS, View.PATH}
    if normalized.list.enabled and (
        view in graph_views
        or graph_view in graph_views
        or "network" in (normalized.output.blocks or [])
    ):
        list_spec = normalized.list
        normalized = normalized.copy(
            update={"list": list_spec.copy(update={"enabled": False})}
        )
        trace["list"] = {
            "requested": list_spec.dict(),
            "applied": normalized.list.dict(),
            "disabled_for_graph": True,
        }
        logger.info(
            "ci.validator.clamp",
            extra={
                "field": "list.enabled",
                "from": True,
                "to": False,
                "policy_code": "list_disabled_for_graph",
            },
        )
    list_spec = normalized.list
    if list_spec.enabled:
        limit_applied = _clamp_list_limit(list_spec.limit)
        offset_applied = _clamp_list_offset(list_spec.offset)
        applied_spec = list_spec.copy(update={"limit": limit_applied, "offset": offset_applied})
        normalized = normalized.copy(update={"list": applied_spec})
        list_trace: Dict[str, Any] = {
            "requested": list_spec.dict(),
            "applied": applied_spec.dict(),
        }
        if limit_applied != list_spec.limit:
            list_trace["limit_clamped"] = True
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "list.limit",
                    "from": list_spec.limit,
                    "to": limit_applied,
                    "policy_code": "list_limit",
                },
            )
        if offset_applied != list_spec.offset:
            list_trace["offset_clamped"] = True
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "list.offset",
                    "from": list_spec.offset,
                    "to": offset_applied,
                    "policy_code": "list_offset",
                },
            )
        trace["list"] = list_trace
    metric_trace: Dict[str, Any] = {}
    metric_spec = normalized.metric
    if metric_spec:
        allowed_time_ranges = {"last_1h", "last_24h", "last_7d"}
        allowed_aggs = {"count", "max", "min", "avg"}
        allowed_modes = {"aggregate"} if metric_spec.scope == "graph" else {"aggregate", "series"}
        if not (
            metric_spec.time_range in allowed_time_ranges
            or _is_absolute_date(metric_spec.time_range)
        ):
            raise ValueError(f"Invalid time_range '{metric_spec.time_range}' for metric")
        if metric_spec.agg not in allowed_aggs:
            raise ValueError(f"Invalid agg '{metric_spec.agg}' for metric")
        scope_requested = metric_spec.scope
        mode_requested = metric_spec.mode
        mode_applied = mode_requested if mode_requested in allowed_modes else "aggregate"
        warnings: List[str] = []
        if metric_spec.scope == "graph" and metric_spec.mode == "series":
            warnings.append("Series charts are not supported over graph scope; forcing aggregate")
            mode_applied = "aggregate"
        normalized_metric = metric_spec
        if mode_requested != mode_applied:
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "metric.mode",
                    "from": mode_requested,
                    "to": mode_applied,
                    "policy_code": "metric_mode",
                },
            )
            normalized_metric = metric_spec.copy(update={"mode": mode_applied})
        normalized = normalized.copy(update={"metric": normalized_metric})
        metric_trace = {
            "metric": normalized_metric.dict(),
            "scope_requested": scope_requested,
            "scope_applied": scope_requested,
            "mode_requested": mode_requested,
            "mode_applied": mode_applied,
        }
        if warnings:
            metric_trace["warnings"] = warnings
        if scope_requested == "graph":
            metric_trace["graph"] = {
                "view_requested": graph_view.value,
                "view_applied": graph_view.value,
                "depth_requested": requested_depth,
                "depth_applied": clamped_depth,
            }
    if metric_trace:
        trace["metric"] = metric_trace
    history_spec = normalized.history
    if history_spec.enabled:
        allowed_history_ranges = {"last_24h", "last_7d", "last_30d"}
        history_updates: dict[str, Any] = {}
        history_trace: dict[str, Any] = {
            "requested": history_spec.dict(),
        }
        warnings: list[str] = []
        if history_spec.time_range not in allowed_history_ranges:
            raise ValueError(f"Invalid history time_range '{history_spec.time_range}'")
        clamped_limit = max(1, min(200, history_spec.limit))
        history_updates["limit"] = clamped_limit
        history_trace["limit_applied"] = clamped_limit
        if clamped_limit != history_spec.limit:
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "history.limit",
                    "from": history_spec.limit,
                    "to": clamped_limit,
                    "policy_code": "history_limit",
                },
            )
        allowed_scopes = {"ci", "graph"}
        scope_applied = history_spec.scope if history_spec.scope in allowed_scopes else "ci"
        if history_spec.scope not in allowed_scopes:
            warnings.append(f"scope '{history_spec.scope}' not supported, falling back to 'ci'")
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "history.scope",
                    "from": history_spec.scope,
                    "to": scope_applied,
                    "policy_code": "history_scope",
                },
            )
        history_updates["scope"] = scope_applied
        history_trace["scope_applied"] = scope_applied
        allowed_modes = {"recent"}
        mode_applied = history_spec.mode if history_spec.mode in allowed_modes else "recent"
        if history_spec.mode not in allowed_modes:
            warnings.append(f"mode '{history_spec.mode}' not supported, forcing 'recent'")
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "history.mode",
                    "from": history_spec.mode,
                    "to": mode_applied,
                    "policy_code": "history_mode",
                },
            )
        history_updates["mode"] = mode_applied
        history_trace["mode_applied"] = mode_applied
        if history_spec.source != "event_log":
            warnings.append(f"source '{history_spec.source}' not supported, forcing 'event_log'")
            logger.info(
                "ci.validator.clamp",
                extra={
                    "field": "history.source",
                    "from": history_spec.source,
                    "to": "event_log",
                    "policy_code": "history_source",
                },
            )
        history_updates["source"] = "event_log"
        history_trace["source"] = "event_log"
        normalized = normalized.copy(update={"history": history_spec.copy(update=history_updates)})
        if warnings:
            history_trace["warnings"] = warnings
        if history_updates.get("scope") == "graph":
            graph_view_trace = normalized.graph.view or view
            requested_depth_history = normalized.graph.depth
            clamped_history_depth = policy.clamp_depth(graph_view_trace.value, requested_depth_history)
            normalized = normalized.copy(
                update={
                    "graph": normalized.graph.copy(update={"view": graph_view_trace, "depth": clamped_history_depth})
                }
            )
            history_trace["graph"] = {
                "view_requested": graph_view_trace.value,
                "view_applied": graph_view_trace.value,
                "depth_requested": requested_depth_history,
                "depth_applied": clamped_history_depth,
            }
        trace["history"] = history_trace
    cep_spec = normalized.cep
    if cep_spec:
        cep_updates: dict[str, Any] = {}
        cep_trace: dict[str, Any] = {"requested": cep_spec.dict()}
        cep_trace["dry_run"] = True
        cep_updates["dry_run"] = True
        cep_updates["mode"] = "simulate"
        rule_id = cep_spec.rule_id
        if rule_id and not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", rule_id):
            rule_id = None
        cep_updates["rule_id"] = rule_id
        cep_trace["rule_id_parsed"] = rule_id
        normalized = normalized.copy(update={"cep": cep_spec.copy(update=cep_updates)})
        trace["cep"] = cep_trace
    if auto_trace:
        trace["auto"] = auto_trace
    if normalized.normalized_from and normalized.normalized_to:
        trace["normalized_from"] = normalized.normalized_from
        trace["normalized_to"] = normalized.normalized_to
    # Add multi-step trace
    if multistep_trace:
        trace["multistep"] = multistep_trace
    logger.info(
        "ci.validator.done",
        extra={
            "view": view.value,
            "depth": normalized.graph.depth,
            "mode": normalized.mode.value if normalized.mode else None,
            "multistep_enabled": normalized.enable_multistep,
        },
    )
    return normalized, trace
