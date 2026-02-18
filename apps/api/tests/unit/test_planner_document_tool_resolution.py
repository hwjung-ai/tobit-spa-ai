"""Unit tests for document tool resolution in planner."""

from app.modules.ops.services.orchestration.planner.plan_schema import (
    GraphLimits,
    GraphSpec,
    HistorySpec,
    Intent,
    MetricSpec,
    Plan,
    PrimarySpec,
    View,
)
from app.modules.ops.services.orchestration.planner.planner_llm import (
    _activate_all_specs_for_all_mode,
    _resolve_document_tool_name,
)


def test_resolve_document_tool_name_prefers_capability() -> None:
    tools_info = [
        {
            "name": "generic_http",
            "type": "generic_http",
            "tags": {"capabilities": ["ci_search"]},
        },
        {
            "name": "document_search",
            "type": "document_search",
            "tags": {"capabilities": ["document_search"]},
        },
    ]
    valid_tool_types = {t["type"] for t in tools_info}

    resolved = _resolve_document_tool_name(tools_info, valid_tool_types)
    assert resolved == "document_search"


def test_resolve_document_tool_name_falls_back_by_name() -> None:
    tools_info = [
        {
            "name": "my_document_http",
            "type": "my_document_http",
            "tags": {},
        }
    ]
    valid_tool_types = {t["type"] for t in tools_info}

    resolved = _resolve_document_tool_name(tools_info, valid_tool_types)
    assert resolved == "my_document_http"


def test_activate_all_mode_uses_resolved_document_tool() -> None:
    # Pre-populate non-document specs to isolate document activation branch.
    plan = Plan(
        intent=Intent.LOOKUP,
        primary=PrimarySpec(keywords=["test"], tool_type="ci_lookup"),
        metric=MetricSpec(metric_name="cpu_usage", agg="avg", time_range="last_24h", tool_type="metric_query"),
        history=HistorySpec(enabled=True, source="event_log", scope="ci", mode="recent", time_range="last_24h", limit=50, tool_type="history_search"),
        graph=GraphSpec(depth=2, view=View.DEPENDENCY, limits=GraphLimits(rows=100, nodes=100, relationships=200), user_requested_depth=2, tool_type="graph_expand"),
    )
    tools_info = [
        {
            "name": "document_search",
            "type": "document_search",
            "tags": {"capabilities": ["document_search"]},
        },
        {"name": "ci_lookup", "type": "ci_lookup", "tags": {}},
    ]
    valid_tool_types = {t["type"] for t in tools_info}

    _activate_all_specs_for_all_mode(
        plan,
        "문서 검색 테스트",
        valid_tool_types,
        tools_info=tools_info,
    )

    assert plan.document is not None
    assert plan.document["tool_type"] == "document_search"
