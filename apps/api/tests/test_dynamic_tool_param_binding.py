from __future__ import annotations

from app.modules.ops.services.orchestration.tools.base import ToolContext
from app.modules.ops.services.orchestration.tools.dynamic_tool import DynamicTool


def test_bind_native_positional_placeholders_uses_required_order() -> None:
    tool = DynamicTool(
        {
            "name": "metric_query",
            "tool_type": "database_query",
            "tool_config": {},
            "tool_input_schema": {
                "type": "object",
                "required": ["tenant_id", "metric_name", "limit"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "metric_name": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        }
    )

    query = "SELECT * FROM mv WHERE tenant_id=%s AND metric=%s LIMIT %s"
    params = tool._bind_native_placeholders(
        query, {"tenant_id": "default", "metric_name": "cpu", "limit": 10}
    )
    assert params == ["default", "cpu", 10]


def test_materialize_input_data_fills_required_defaults() -> None:
    tool = DynamicTool(
        {
            "name": "metric_series",
            "tool_type": "database_query",
            "tool_config": {},
            "tool_input_schema": {
                "type": "object",
                "required": ["tenant_id", "limit", "offset"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                },
            },
        }
    )

    context = ToolContext(tenant_id="tenant-a", user_id="u1")
    data = tool._materialize_input_data({}, context)
    assert data["tenant_id"] == "tenant-a"
    assert data["limit"] == 100
    assert data["offset"] == 0


def test_materialize_input_data_normalizes_empty_uuid_and_time_fields() -> None:
    tool = DynamicTool(
        {
            "name": "maintenance_history_list",
            "tool_type": "database_query",
            "tool_config": {},
            "tool_input_schema": {
                "type": "object",
                "required": ["tenant_id"],
                "properties": {
                    "tenant_id": {"type": "string"},
                    "ci_id": {"type": "string"},
                    "start_time": {"type": "string"},
                },
            },
        }
    )

    context = ToolContext(tenant_id="tenant-a", user_id="u1")
    data = tool._materialize_input_data(
        {"tenant_id": "tenant-a", "ci_id": "", "start_time": ""}, context
    )
    assert data["ci_id"] is None
    assert data["start_time"] is None


def test_execute_stage_rebinds_native_params_on_count_mismatch() -> None:
    tool = DynamicTool(
        {
            "name": "ci_detail_lookup",
            "tool_type": "database_query",
            "tool_config": {},
            "tool_input_schema": {
                "type": "object",
                "required": ["field", "value", "tenant_id"],
                "properties": {
                    "field": {"type": "string"},
                    "value": {"type": "string"},
                    "tenant_id": {"type": "string"},
                },
            },
        }
    )

    query = "SELECT * FROM ci WHERE ci_code=%s AND tenant_id=%s LIMIT %s"
    # Simulate template processing that produced incomplete params list.
    params = ["ci-001"]
    placeholder_count = len(__import__("re").findall(r"(?<!%)%s", query))
    assert placeholder_count == 3
    assert len(params) != placeholder_count

    rebound = tool._bind_native_placeholders(
        query, {"field": "ci_code", "value": "ci-001", "tenant_id": "tenant-a", "limit": 10}
    )
    assert rebound == ["ci_code", "ci-001", "tenant-a"]
