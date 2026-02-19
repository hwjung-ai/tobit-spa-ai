from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.inspector.asset_context import get_tracked_assets
from app.modules.inspector.crud import create_execution_trace
from app.modules.inspector.models import TbExecutionTrace


def _summarize_asset(asset: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not asset:
        return None
    return {
        "asset_id": asset.get("asset_id"),
        "name": asset.get("name"),
        "version": asset.get("version"),
        "source": asset.get("source"),
        "scope": asset.get("scope"),
        "engine": asset.get("engine"),
        "policy_type": asset.get("policy_type"),
        "mapping_type": asset.get("mapping_type"),
    }


def _build_applied_assets(state: dict[str, Any]) -> Dict[str, Any]:
    return {
        "prompt": _summarize_asset(state.get("prompt")),
        "prompts": [
            _summarize_asset(entry) for entry in state.get("prompts", []) if entry
        ],
        "policy": _summarize_asset(state.get("policy")),
        "policies": [
            _summarize_asset(entry) for entry in state.get("policies", []) if entry
        ],
        "mapping": _summarize_asset(state.get("mapping")),
        "mappings": [
            _summarize_asset(entry) for entry in state.get("mappings", []) if entry
        ],
        "source": _summarize_asset(state.get("source")),
        "catalog": _summarize_asset(state.get("catalog")),
        "resolver": _summarize_asset(state.get("resolver")),
        "tools": [
            _summarize_asset(entry) for entry in state.get("tools", []) if entry
        ],
    }


def _compute_asset_versions(state: dict[str, Any]) -> List[str]:
    versions: List[str] = []
    for key in ("prompt", "policy", "mapping", "source", "resolver"):
        info = state.get(key)
        if info:
            asset_id = info.get("asset_id")
            if asset_id:
                versions.append(asset_id)
            else:
                versions.append(f"{info.get('name')}@{info.get('source')}")
    catalog = state.get("catalog")
    if catalog:
        asset_id = catalog.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(
                f"{catalog.get('name')}@{catalog.get('source')}"
            )
    for entry in state.get("tools", []):
        if not entry:
            continue
        asset_id = entry.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(f"{entry.get('name')}@{entry.get('source', 'tool')}")
    for entry in state.get("prompts", []):
        if not entry:
            continue
        asset_id = entry.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(f"{entry.get('name')}@{entry.get('source', 'prompt')}")
    for entry in state.get("policies", []):
        if not entry:
            continue
        asset_id = entry.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(f"{entry.get('name')}@{entry.get('source', 'policy')}")
    for entry in state.get("mappings", []):
        if not entry:
            continue
        asset_id = entry.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(f"{entry.get('name')}@{entry.get('source', 'mapping')}")
    return versions


def _compute_fallbacks(state: dict[str, Any]) -> Dict[str, bool]:
    def _is_external(
        info: Dict[str, Any] | None,
        entries: List[Dict[str, Any]] | None = None,
    ) -> bool:
        if isinstance(info, dict):
            return info.get("source") != "asset_registry"
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("source") == "asset_registry":
                return False
        return True

    return {
        "prompt": _is_external(state.get("prompt"), state.get("prompts")),
        "policy": _is_external(state.get("policy"), state.get("policies")),
        "mapping": _is_external(state.get("mapping"), state.get("mappings")),
        "source": _is_external(state.get("source")),
        "catalog": _is_external(state.get("catalog")),
        "resolver": _is_external(state.get("resolver")),
        "tool": any(
            entry.get("source") != "asset_registry"
            for entry in state.get("tools", [])
            if entry
        ),
    }


def _build_execution_steps(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    for idx, call in enumerate(tool_calls):
        status = "error" if call.get("error") else "success"
        steps.append(
            {
                "step_id": call.get("tool") or f"tool-{idx}",
                "tool_name": call.get("tool"),
                "status": status,
                "duration_ms": call.get("elapsed_ms", 0),
                "request": call.get("input_params"),
                "response": call.get("output_summary"),
                "error": {"message": call.get("error")} if call.get("error") else None,
                "references": [],
            }
        )
    return steps


def _asset_exists(session: Session, asset_id: str | None) -> bool:
    if not asset_id:
        return False
    try:
        asset_uuid = uuid.UUID(str(asset_id))
    except (ValueError, TypeError):
        return False
    try:
        return (
            session.exec(
                select(TbAssetRegistry.asset_id).where(
                    TbAssetRegistry.asset_id == asset_uuid
                )
            ).first()
            is not None
        )
    except Exception:
        return False


def _asset_ref(asset: Dict[str, Any] | None) -> str | None:
    if not asset:
        return None
    asset_id = asset.get("asset_id")
    version = asset.get("version")
    name = asset.get("name")
    if asset_id and version is not None:
        return f"{asset_id}:v{version}"
    if asset_id:
        return str(asset_id)
    if name and version is not None:
        return f"{name}:v{version}"
    if name:
        return str(name)
    return None


_INTERNAL_TOOL_ALIASES = {"primary", "aggregate", "history", "graph"}


def _is_internal_tool_alias(name: str | None) -> bool:
    if not isinstance(name, str):
        return False
    return name.strip().lower() in _INTERNAL_TOOL_ALIASES


def _extract_plan_alias_tool_types(trace: TbExecutionTrace) -> Dict[str, str]:
    plan = trace.plan_validated if isinstance(trace.plan_validated, dict) else {}
    if not plan:
        return {}

    alias_map: Dict[str, str] = {}
    for alias in ("primary", "secondary", "aggregate", "history", "graph", "auto"):
        block = plan.get(alias)
        if not isinstance(block, dict):
            continue
        tool_type = block.get("tool_type")
        if isinstance(tool_type, str) and tool_type.strip():
            alias_map[alias] = tool_type.strip()
    return alias_map


def _normalize_tool_name_with_plan(
    raw_name: str | None, alias_map: Dict[str, str]
) -> str | None:
    if not isinstance(raw_name, str):
        return None
    name = raw_name.strip()
    if not name:
        return None
    alias = name.lower()
    if alias in alias_map:
        return alias_map[alias]
    if _is_internal_tool_alias(name):
        return None
    return name


def _extract_tool_names(trace: TbExecutionTrace) -> List[str]:
    names: List[str] = []
    alias_map = _extract_plan_alias_tool_types(trace)

    for step in trace.execution_steps or []:
        if not isinstance(step, dict):
            continue
        resolved = _normalize_tool_name_with_plan(step.get("tool_name"), alias_map)
        if resolved:
            names.append(resolved)

    for stage_output in trace.stage_outputs or []:
        if not isinstance(stage_output, dict):
            continue
        if stage_output.get("stage") != "execute":
            continue
        result = stage_output.get("result")
        if not isinstance(result, dict):
            continue

        execution_results = result.get("execution_results")
        if not isinstance(execution_results, list):
            base_result = result.get("base_result")
            if isinstance(base_result, dict):
                execution_results = base_result.get("execution_results")
        if not isinstance(execution_results, list):
            continue

        for item in execution_results:
            if not isinstance(item, dict):
                continue
            resolved = _normalize_tool_name_with_plan(item.get("tool_name"), alias_map)
            if resolved:
                names.append(resolved)

    # Preserve order while deduplicating
    seen: set[str] = set()
    deduped: List[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def normalize_trace_for_inspector(
    session: Session, trace: TbExecutionTrace
) -> Dict[str, Any]:
    """
    Normalize stored trace payload for Inspector UI.

    This read-time normalization keeps older traces displayable by:
    - removing stale asset references to deleted Asset Registry entries,
    - filtering deprecated per-stage keys,
    - evidence-based legacy backfill when stage assets were stored as empty maps.
    """
    data = trace.model_dump()

    raw_applied = data.get("applied_assets") or {}
    applied_assets: Dict[str, Any] = {
        "prompt": raw_applied.get("prompt"),
        "prompts": list(raw_applied.get("prompts") or []),
        "policy": raw_applied.get("policy"),
        "policies": list(raw_applied.get("policies") or []),
        "mapping": raw_applied.get("mapping"),
        "mappings": list(raw_applied.get("mappings") or []),
        "source": raw_applied.get("source"),
        "catalog": raw_applied.get("catalog"),
        "resolver": raw_applied.get("resolver"),
        "tools": list(raw_applied.get("tools") or []),
    }

    # Legacy traces may only have a single prompt slot.
    if not applied_assets["prompts"] and isinstance(applied_assets.get("prompt"), dict):
        applied_assets["prompts"] = [applied_assets["prompt"]]
    if not applied_assets["policies"] and isinstance(applied_assets.get("policy"), dict):
        applied_assets["policies"] = [applied_assets["policy"]]
    if not applied_assets["mappings"] and isinstance(applied_assets.get("mapping"), dict):
        applied_assets["mappings"] = [applied_assets["mapping"]]

    # Drop deleted asset-registry references.
    for key in ("prompt", "policy", "mapping", "source", "catalog", "resolver"):
        asset = applied_assets.get(key)
        if not isinstance(asset, dict):
            continue
        if asset.get("source") == "asset_registry" and not _asset_exists(
            session, asset.get("asset_id")
        ):
            applied_assets[key] = None

    def _sanitize_asset_list(key: str) -> List[Dict[str, Any]]:
        cleaned: List[Dict[str, Any]] = []
        seen: set[tuple[Any, Any]] = set()
        for entry in applied_assets.get(key) or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("source") == "asset_registry" and entry.get("asset_id"):
                if not _asset_exists(session, entry.get("asset_id")):
                    continue
            dedupe_key = (entry.get("name"), entry.get("version"))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            cleaned.append(entry)
        return cleaned

    applied_assets["prompts"] = _sanitize_asset_list("prompts")
    applied_assets["policies"] = _sanitize_asset_list("policies")
    applied_assets["mappings"] = _sanitize_asset_list("mappings")

    if not isinstance(applied_assets.get("policy"), dict) and applied_assets["policies"]:
        applied_assets["policy"] = applied_assets["policies"][-1]
    if not isinstance(applied_assets.get("mapping"), dict) and applied_assets["mappings"]:
        applied_assets["mapping"] = applied_assets["mappings"][-1]

    plan_alias_map = _extract_plan_alias_tool_types(trace)
    sanitized_tools: List[Dict[str, Any]] = []
    for tool in applied_assets.get("tools") or []:
        if not isinstance(tool, dict):
            continue
        tool_name = tool.get("name") or tool.get("tool_name")
        if tool.get("source") == "tool_execution":
            resolved = _normalize_tool_name_with_plan(
                str(tool_name) if tool_name is not None else None, plan_alias_map
            )
            if not resolved:
                continue
            tool = {
                **tool,
                "name": resolved,
                "tool_name": resolved,
            }
        if tool.get("source") == "asset_registry" and tool.get("asset_id"):
            if not _asset_exists(session, tool.get("asset_id")):
                continue
        sanitized_tools.append(tool)

    applied_assets["tools"] = sanitized_tools

    normalized_stage_inputs: List[Dict[str, Any]] = []
    for stage_input in data.get("stage_inputs") or []:
        if not isinstance(stage_input, dict):
            continue
        stage_name = str(stage_input.get("stage") or "")
        stage_applied = stage_input.get("applied_assets")
        stage_applied_map = stage_applied if isinstance(stage_applied, dict) else {}

        # Hide deprecated per-stage keys if they exist in legacy traces.
        filtered: Dict[str, Any] = {}
        for key, value in stage_applied_map.items():
            if key in {"query", "queries", "screen", "screens"}:
                continue
            filtered[key] = value

        stage_input["applied_assets"] = filtered

        normalized_stage_inputs.append(stage_input)

    # Legacy bridge:
    # Older traces may miss route_plan prompt in stage_inputs even when it was tracked
    # globally in applied_assets.prompts. Only fill this specific case with evidence.
    planner_prompt: Dict[str, Any] | None = None
    for entry in applied_assets.get("prompts") or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        lowered = name.lower()
        if (
            "planner" in lowered
            or "route" in lowered
            or "output_parser" in lowered
        ):
            planner_prompt = entry
            break

    if planner_prompt:
        for stage_input in normalized_stage_inputs:
            if str(stage_input.get("stage") or "") != "route_plan":
                continue
            stage_applied = stage_input.get("applied_assets")
            stage_applied_map = stage_applied if isinstance(stage_applied, dict) else {}
            if "prompt" not in stage_applied_map:
                stage_applied_map["prompt"] = planner_prompt
                stage_input["applied_assets"] = stage_applied_map
            break

    has_budget_policy = any(
        isinstance(entry, dict)
        and "budget" in str(entry.get("name") or entry.get("policy_type") or "").lower()
        for entry in (applied_assets.get("policies") or [])
    )
    budget_policy: Dict[str, Any] | None = None
    if has_budget_policy:
        for entry in applied_assets.get("policies") or []:
            if not isinstance(entry, dict):
                continue
            policy_name = str(entry.get("name") or entry.get("policy_type") or "").lower()
            if "plan_budget" in policy_name or "budget" in policy_name:
                budget_policy = entry
                break
    elif isinstance(applied_assets.get("policy"), dict):
        policy_name = str(
            applied_assets["policy"].get("name")
            or applied_assets["policy"].get("policy_type")
            or ""
        ).lower()
        if "plan_budget" in policy_name or "budget" in policy_name:
            budget_policy = applied_assets["policy"]

    graph_relation_mapping: Dict[str, Any] | None = None
    for entry in applied_assets.get("mappings") or []:
        if not isinstance(entry, dict):
            continue
        mapping_name = str(entry.get("name") or entry.get("mapping_type") or "").lower()
        if "graph_relation" in mapping_name:
            graph_relation_mapping = entry
            break
    if graph_relation_mapping is None and isinstance(applied_assets.get("mapping"), dict):
        mapping_name = str(
            applied_assets["mapping"].get("name")
            or applied_assets["mapping"].get("mapping_type")
            or ""
        ).lower()
        if "graph_relation" in mapping_name:
            graph_relation_mapping = applied_assets["mapping"]

    def _append_prompt_if_missing(prompt: Dict[str, Any]) -> None:
        if not isinstance(prompt, dict):
            return
        prompt_name = prompt.get("name")
        prompt_version = prompt.get("version")
        existing = applied_assets.get("prompts") or []
        if any(
            isinstance(entry, dict)
            and entry.get("name") == prompt_name
            and entry.get("version") == prompt_version
            for entry in existing
        ):
            return
        applied_assets["prompts"] = [*existing, prompt]

    def _append_policy_if_missing(policy: Dict[str, Any]) -> None:
        if not isinstance(policy, dict):
            return
        policy_name = policy.get("name") or policy.get("policy_type")
        policy_version = policy.get("version")
        existing = applied_assets.get("policies") or []
        if any(
            isinstance(entry, dict)
            and (entry.get("name") or entry.get("policy_type")) == policy_name
            and entry.get("version") == policy_version
            for entry in existing
        ):
            return
        applied_assets["policies"] = [*existing, policy]

    # Evidence-based legacy backfill:
    # Some traces were persisted with empty per-stage applied_assets even though
    # execution evidence exists in stage_outputs / plan metadata.
    has_stage_inputs = len(normalized_stage_inputs) > 0
    all_stage_assets_empty = has_stage_inputs and all(
        not (entry.get("applied_assets") or {}) for entry in normalized_stage_inputs
    )
    if all_stage_assets_empty:
        tool_names = _extract_tool_names(trace)

        # Backfill global tool list from execution evidence when missing.
        if not applied_assets.get("tools") and tool_names:
            applied_assets["tools"] = [
                {
                    "asset_id": None,
                    "name": name,
                    "tool_name": name,
                    "version": None,
                    "source": "tool_execution",
                }
                for name in tool_names
            ]

        global_prompt = (
            applied_assets.get("prompt") if isinstance(applied_assets.get("prompt"), dict) else None
        )
        compose_prompt = None
        if isinstance(global_prompt, dict):
            global_prompt_name = str(global_prompt.get("name") or "").lower()
            if "compose" in global_prompt_name or "summary" in global_prompt_name:
                compose_prompt = global_prompt

        inferred_planner_prompt = planner_prompt or {
            "asset_id": None,
            "name": "ops_planner_output_parser",
            "version": None,
            "source": "inferred",
        }
        _append_prompt_if_missing(inferred_planner_prompt)

        # Legacy traces often lose validator policy details.
        if not has_budget_policy:
            inferred_budget_policy = {
                "asset_id": None,
                "name": "plan_budget",
                "policy_type": "plan_budget",
                "version": None,
                "source": "inferred",
            }
            _append_policy_if_missing(inferred_budget_policy)
            budget_policy = inferred_budget_policy

        for stage_input in normalized_stage_inputs:
            stage_name = str(stage_input.get("stage") or "")
            if not stage_name:
                continue
            staged: Dict[str, Any] = {}

            if stage_name == "route_plan":
                staged["prompt"] = inferred_planner_prompt
            elif stage_name == "validate":
                validate_policy = budget_policy
                if not validate_policy and isinstance(applied_assets.get("policy"), dict):
                    validate_policy = applied_assets["policy"]
                if validate_policy:
                    staged["policy"] = validate_policy
            elif stage_name == "execute":
                if isinstance(applied_assets.get("source"), dict):
                    staged["source"] = applied_assets["source"]
                if isinstance(applied_assets.get("catalog"), dict):
                    staged["catalog"] = applied_assets["catalog"]
                if graph_relation_mapping:
                    staged["mapping"] = graph_relation_mapping
                for name in tool_names:
                    staged[f"tool:{name}"] = name
            elif stage_name == "compose":
                if compose_prompt:
                    staged["prompt"] = compose_prompt
                if isinstance(applied_assets.get("mapping"), dict):
                    staged["mapping"] = applied_assets["mapping"]
                if isinstance(applied_assets.get("resolver"), dict):
                    staged["resolver"] = applied_assets["resolver"]

            stage_input["applied_assets"] = staged

    # Partial legacy stage snapshots: backfill only missing slots per stage.
    if has_stage_inputs:
        tool_names = _extract_tool_names(trace)
        inferred_planner_prompt = planner_prompt or {
            "asset_id": None,
            "name": "ops_planner_output_parser",
            "version": None,
            "source": "inferred",
        }
        _append_prompt_if_missing(inferred_planner_prompt)
        if budget_policy is None:
            budget_policy = {
                "asset_id": None,
                "name": "plan_budget",
                "policy_type": "plan_budget",
                "version": None,
                "source": "inferred",
            }
            _append_policy_if_missing(budget_policy)

        for stage_input in normalized_stage_inputs:
            stage_name = str(stage_input.get("stage") or "")
            if not stage_name:
                continue
            stage_applied = stage_input.get("applied_assets")
            stage_applied_map = stage_applied if isinstance(stage_applied, dict) else {}

            if stage_name == "route_plan" and "prompt" not in stage_applied_map:
                stage_applied_map["prompt"] = inferred_planner_prompt
            if stage_name == "validate" and "policy" not in stage_applied_map and budget_policy:
                stage_applied_map["policy"] = budget_policy
            if stage_name == "execute":
                if (
                    graph_relation_mapping
                    and "mapping" not in stage_applied_map
                ):
                    stage_applied_map["mapping"] = graph_relation_mapping
                has_tool = any(str(key).startswith("tool:") for key in stage_applied_map.keys())
                if not has_tool and tool_names:
                    for name in tool_names:
                        stage_applied_map[f"tool:{name}"] = name

            stage_input["applied_assets"] = stage_applied_map

    data["applied_assets"] = applied_assets
    data["stage_inputs"] = normalized_stage_inputs
    return data


def persist_execution_trace(
    session: Session,
    *,
    trace_id: str,
    parent_trace_id: str | None,
    feature: str,
    endpoint: str,
    method: str,
    ops_mode: str,
    question: str,
    status: str,
    duration_ms: int,
    request_payload: Dict[str, Any],
    plan_raw: Dict[str, Any] | None,
    plan_validated: Dict[str, Any] | None,
    trace_payload: Dict[str, Any],
    answer_meta: Dict[str, Any] | None,
    blocks: List[Dict[str, Any]] | None,
    flow_spans: List[Dict[str, Any]] | None = None,
) -> TbExecutionTrace:
    from core.logging import get_logger
    logger = get_logger(__name__)

    assets = get_tracked_assets()
    applied_assets = _build_applied_assets(assets)
    asset_versions = _compute_asset_versions(assets)
    fallbacks = _compute_fallbacks(assets)
    tool_calls = trace_payload.get("tool_calls") or []
    execution_steps = _build_execution_steps(tool_calls)
    references = trace_payload.get("references")
    answer_data: Dict[str, Any] = {
        "envelope_meta": answer_meta,
        "blocks": [
            block
            if isinstance(block, dict)
            else getattr(block, "dict", lambda: block)()
            for block in (blocks or [])
        ],
    }

    stage_inputs = trace_payload.get("stage_inputs", [])
    stage_outputs = trace_payload.get("stage_outputs", [])
    logger.info(
        f"Persisting trace {trace_id}: route={trace_payload.get('route', 'orch')}, "
        f"stage_inputs={len(stage_inputs)}, stage_outputs={len(stage_outputs)}"
    )

    def _json_safe(value: Any) -> Any:
        if value is None:
            return None
        return jsonable_encoder(value)

    safe_request_payload = _json_safe(request_payload)
    safe_plan_raw = _json_safe(plan_raw)
    safe_plan_validated = _json_safe(plan_validated)
    safe_execution_steps = _json_safe(execution_steps)
    safe_references = _json_safe(references)
    safe_answer_data = _json_safe(answer_data)
    safe_flow_spans = _json_safe(flow_spans)
    safe_stage_inputs = _json_safe(stage_inputs)
    safe_stage_outputs = _json_safe(stage_outputs)
    safe_replan_events = _json_safe(trace_payload.get("replan_events", []))

    trace_entry = TbExecutionTrace(
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        feature=feature,
        endpoint=endpoint,
        method=method,
        ops_mode=ops_mode,
        question=question,
        status=status,
        duration_ms=duration_ms,
        request_payload=safe_request_payload,
        applied_assets=applied_assets,
        asset_versions=asset_versions or None,
        fallbacks=fallbacks,
        plan_raw=safe_plan_raw,
        plan_validated=safe_plan_validated,
        execution_steps=safe_execution_steps,
        references=safe_references,
        answer=safe_answer_data,
        ui_render=None,
        audit_links={"related_audit_log_ids": []},
        flow_spans=safe_flow_spans,
        # New orchestration fields
        route=trace_payload.get("route", "orch"),
        stage_inputs=safe_stage_inputs or [],
        stage_outputs=safe_stage_outputs or [],
        replan_events=safe_replan_events or [],
    )
    return create_execution_trace(session, trace_entry)
