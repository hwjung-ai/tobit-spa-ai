from __future__ import annotations

from app.modules.inspector.models import TbExecutionTrace
from app.modules.inspector.service import (
    _build_applied_assets,
    _compute_fallbacks,
    normalize_trace_for_inspector,
)
from sqlmodel import Session


def test_build_applied_assets_keeps_catalog_only() -> None:
    state = {
        "catalog": {
            "asset_id": "catalog-asset-1",
            "name": "main_catalog",
            "version": 3,
            "source": "asset_registry",
        }
    }

    applied_assets = _build_applied_assets(state)

    assert applied_assets["catalog"] is not None
    assert applied_assets["catalog"]["asset_id"] == "catalog-asset-1"
    assert applied_assets["catalog"]["name"] == "main_catalog"
    assert "schema" not in applied_assets


def test_compute_fallbacks_keeps_catalog_only() -> None:
    state = {
        "catalog": {
            "asset_id": "catalog-asset-1",
            "name": "main_catalog",
            "version": 3,
            "source": "asset_registry",
        }
    }

    fallbacks = _compute_fallbacks(state)

    assert fallbacks["catalog"] is False
    assert "schema" not in fallbacks


def test_normalize_trace_for_inspector_keeps_missing_assets_as_missing(
    session: Session,
) -> None:
    trace = TbExecutionTrace(
        trace_id="trace-normalize-1",
        parent_trace_id=None,
        feature="ops",
        endpoint="/ops/ask",
        method="POST",
        ops_mode="real",
        question="tool status",
        status="success",
        duration_ms=120,
        request_payload={},
        applied_assets={
            "prompt": {
                "asset_id": None,
                "name": "ops_compose_summary",
                "version": 1,
                "source": "inline",
            },
            "queries": [
                {
                    "asset_id": "00000000-0000-0000-0000-000000000999",
                    "name": "deleted_query_asset",
                    "version": 1,
                    "source": "asset_registry",
                }
            ],
        },
        asset_versions=[],
        fallbacks={},
        plan_raw={},
        plan_validated={},
        execution_steps=[
            {
                "step_id": "s1",
                "tool_name": "metric_aggregate",
                "status": "success",
                "duration_ms": 10,
                "request": None,
                "response": None,
                "error": None,
            }
        ],
        references=[],
        answer={},
        ui_render={},
        audit_links={},
        flow_spans=[],
        route="orch",
        stage_inputs=[
            {"stage": "route_plan", "applied_assets": {}},
            {"stage": "execute", "applied_assets": {}},
        ],
        stage_outputs=[
            {
                "stage": "execute",
                "result": {
                    "execution_results": [
                        {"tool_name": "metric_aggregate", "success": True}
                    ]
                },
                "diagnostics": {"status": "ok", "warnings": [], "errors": []},
                "references": [],
                "duration_ms": 10,
            }
        ],
        replan_events=[],
    )

    normalized = normalize_trace_for_inspector(session, trace)
    applied_assets = normalized["applied_assets"]
    stage_inputs = normalized["stage_inputs"]

    assert "queries" not in applied_assets
    assert "screens" not in applied_assets
    tool_names = [tool.get("name") for tool in applied_assets["tools"]]
    assert tool_names == ["metric_aggregate"]

    execute_stage = next(
        stage for stage in stage_inputs if stage.get("stage") == "execute"
    )
    execute_assets = execute_stage.get("applied_assets", {})
    assert isinstance(execute_assets, dict)
    assert execute_assets.get("tool:metric_aggregate") == "metric_aggregate"

    route_stage = next(stage for stage in stage_inputs if stage.get("stage") == "route_plan")
    route_assets = route_stage.get("applied_assets", {})
    assert isinstance(route_assets, dict)
    route_prompt = route_assets.get("prompt")
    assert isinstance(route_prompt, dict)
    assert route_prompt.get("name") == "ops_planner_output_parser"


def test_normalize_trace_filters_internal_tool_execution_aliases(
    session: Session,
) -> None:
    trace = TbExecutionTrace(
        trace_id="trace-normalize-2",
        parent_trace_id=None,
        feature="ops",
        endpoint="/ops/ask",
        method="POST",
        ops_mode="real",
        question="show tools",
        status="success",
        duration_ms=50,
        request_payload={},
        applied_assets={"tools": []},
        asset_versions=[],
        fallbacks={},
        plan_raw={},
        plan_validated={
            "primary": {"tool_type": "ci_lookup"},
            "aggregate": {"tool_type": "metric"},
        },
        execution_steps=[],
        references=[],
        answer={},
        ui_render={},
        audit_links={},
        flow_spans=[],
        route="orch",
        stage_inputs=[{"stage": "execute", "applied_assets": {}}],
        stage_outputs=[
            {
                "stage": "execute",
                "result": {
                    "execution_results": [
                        {"tool_name": "primary", "success": True},
                        {"tool_name": "metric.aggregate", "success": True},
                    ]
                },
                "diagnostics": {"status": "ok", "warnings": [], "errors": []},
                "references": [],
                "duration_ms": 5,
            }
        ],
        replan_events=[],
    )

    normalized = normalize_trace_for_inspector(session, trace)
    tools = normalized["applied_assets"]["tools"]
    assert [tool.get("name") for tool in tools] == ["ci_lookup", "metric.aggregate"]

    execute_stage = next(
        stage for stage in normalized["stage_inputs"] if stage.get("stage") == "execute"
    )
    execute_assets = execute_stage.get("applied_assets", {})
    assert isinstance(execute_assets, dict)
    assert execute_assets.get("tool:ci_lookup") == "ci_lookup"
    assert execute_assets.get("tool:metric.aggregate") == "metric.aggregate"


def test_normalize_trace_does_not_infer_planner_prompt_for_legacy_traces(
    session: Session,
) -> None:
    trace = TbExecutionTrace(
        trace_id="trace-normalize-3",
        parent_trace_id=None,
        feature="ops",
        endpoint="/ops/ask",
        method="POST",
        ops_mode="real",
        question="planner prompt check",
        status="success",
        duration_ms=20,
        request_payload={},
        applied_assets={
            "prompt": {
                "asset_id": None,
                "name": "ops_compose_summary",
                "version": 1,
                "source": "inline",
            }
        },
        asset_versions=[],
        fallbacks={},
        plan_raw={},
        plan_validated={"primary": {"tool_type": "ci_lookup"}},
        execution_steps=[],
        references=[],
        answer={},
        ui_render={},
        audit_links={},
        flow_spans=[],
        route="orch",
        stage_inputs=[],
        stage_outputs=[],
        replan_events=[],
    )

    normalized = normalize_trace_for_inspector(session, trace)
    prompts = normalized["applied_assets"].get("prompts") or []
    names = [
        p.get("name")
        for p in prompts
        if isinstance(p, dict) and isinstance(p.get("name"), str)
    ]
    assert "ops_planner_output_parser" not in names
    assert "ops_compose_summary" in names
