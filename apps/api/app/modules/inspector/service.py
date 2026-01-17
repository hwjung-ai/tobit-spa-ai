from __future__ import annotations

from typing import Any, Dict, List

from sqlmodel import Session

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
        "queries": [
            _summarize_asset(entry) for entry in state.get("queries", []) if entry
        ],
    }


def _compute_asset_versions(state: dict[str, Any]) -> List[str]:
    versions: List[str] = []
    for key in ("prompt", "policy", "mapping"):
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
    return versions


def _compute_fallbacks(state: dict[str, Any]) -> Dict[str, bool]:
    def _is_external(info: Dict[str, Any] | None) -> bool:
        if not info:
            return True
        return info.get("source") != "asset_registry"

    return {
        "prompt": _is_external(state.get("prompt")),
        "policy": _is_external(state.get("policy")),
        "mapping": _is_external(state.get("mapping")),
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
) -> TbExecutionTrace:
    assets = get_tracked_assets()
    applied_assets = _build_applied_assets(assets)
    asset_versions = _compute_asset_versions(assets)
    fallbacks = _compute_fallbacks(assets)
    tool_calls = trace_payload.get("tool_calls") or []
    execution_steps = _build_execution_steps(tool_calls)
    references = trace_payload.get("references")
    answer_data: Dict[str, Any] = {
        "envelope_meta": answer_meta,
        "blocks": [block if isinstance(block, dict) else getattr(block, "dict", lambda: block)() for block in (blocks or [])],
    }
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
        request_payload=request_payload,
        applied_assets=applied_assets,
        asset_versions=asset_versions or None,
        fallbacks=fallbacks,
        plan_raw=plan_raw,
        plan_validated=plan_validated,
        execution_steps=execution_steps,
        references=references,
        answer=answer_data,
        ui_render=None,
        audit_links={"related_audit_log_ids": []},
    )
    return create_execution_trace(session, trace_entry)
