from __future__ import annotations

from datetime import datetime
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
        "policy": _summarize_asset(state.get("policy")),
        "mapping": _summarize_asset(state.get("mapping")),
        "source": _summarize_asset(state.get("source")),
        "schema": _summarize_asset(state.get("schema")),
        "resolver": _summarize_asset(state.get("resolver")),
        "queries": [
            _summarize_asset(entry) for entry in state.get("queries", []) if entry
        ],
        "screens": [entry for entry in state.get("screens", []) if entry],
    }


def _compute_asset_versions(state: dict[str, Any]) -> List[str]:
    versions: List[str] = []
    for key in ("prompt", "policy", "mapping", "source", "schema", "resolver"):
        info = state.get(key)
        if info:
            asset_id = info.get("asset_id")
            if asset_id:
                versions.append(asset_id)
            else:
                versions.append(f"{info.get('name')}@{info.get('source')}")
    for entry in state.get("queries", []):
        if not entry:
            continue
        asset_id = entry.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(f"{entry.get('name')}@{entry.get('source')}")
    for entry in state.get("screens", []):
        if not entry:
            continue
        asset_id = entry.get("asset_id")
        if asset_id:
            versions.append(asset_id)
        else:
            versions.append(f"{entry.get('screen_id')}@{entry.get('status')}")
    return versions


def _resolve_screen_assets(
    session: Session, blocks: List[Dict[str, Any]] | None
) -> List[Dict[str, Any]]:
    if not blocks:
        return []
    screen_blocks = [
        b for b in blocks if isinstance(b, dict) and b.get("type") == "ui_screen"
    ]
    if not screen_blocks:
        return []

    screen_ids = list({b.get("screen_id") for b in screen_blocks if b.get("screen_id")})
    if not screen_ids:
        return []

    assets = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "screen")
        .where(TbAssetRegistry.screen_id.in_(screen_ids))
        .where(TbAssetRegistry.status == "published")
    ).all()
    assets_by_screen = {asset.screen_id: asset for asset in assets}

    resolved: List[Dict[str, Any]] = []
    for block in screen_blocks:
        screen_id = block.get("screen_id")
        asset = assets_by_screen.get(screen_id)
        resolved.append(
            {
                "asset_id": str(asset.asset_id) if asset else None,
                "screen_id": screen_id,
                "version": asset.version if asset else None,
                "status": asset.status if asset else "missing",
                "applied_at": datetime.utcnow().isoformat(),
                "block_id": block.get("id"),
                "source": "asset_registry" if asset else "unknown",
            }
        )
    return resolved


def _compute_fallbacks(state: dict[str, Any]) -> Dict[str, bool]:
    def _is_external(info: Dict[str, Any] | None) -> bool:
        if not info:
            return True
        return info.get("source") != "asset_registry"

    return {
        "prompt": _is_external(state.get("prompt")),
        "policy": _is_external(state.get("policy")),
        "mapping": _is_external(state.get("mapping")),
        "source": _is_external(state.get("source")),
        "schema": _is_external(state.get("schema")),
        "resolver": _is_external(state.get("resolver")),
        "query": any(
            entry.get("source") != "asset_registry"
            for entry in state.get("queries", [])
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
    resolved_screens = _resolve_screen_assets(session, blocks)
    if resolved_screens:
        assets["screens"] = resolved_screens
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
