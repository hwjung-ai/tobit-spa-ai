from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from app.modules.api_manager.schemas import ApiExecuteResponse, ApiScriptExecuteResult
from app.modules.api_manager.workflow_executor import (
    _render_templates,
    execute_workflow_api,
)
from fastapi import HTTPException
from sqlmodel import Session


def _workflow_api(spec: dict):
    return SimpleNamespace(api_id="wf-api", logic_spec=spec)


def _node_api(api_id: str, logic_body: str = "", runtime_policy: dict | None = None):
    return SimpleNamespace(
        api_id=api_id,
        logic_body=logic_body,
        runtime_policy=runtime_policy or {"allow_runtime": True},
    )


def test_render_templates_with_params_and_steps():
    rendered = _render_templates(
        {
            "name": "{{params.name}}",
            "rows": "{{steps.node1.output.rows}}",
            "line": "user={{params.name}}",
        },
        params={"name": "alice"},
        steps={"node1": {"output": {"rows": [{"id": 1}]}}},
    )
    assert rendered["name"] == "alice"
    assert rendered["rows"] == [{"id": 1}]
    assert rendered["line"] == "user=alice"


def test_execute_workflow_api_rejects_bad_spec():
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_workflow_api(
            session=session,
            workflow_api=_workflow_api({"version": 2, "nodes": []}),
            params={},
            input_payload=None,
            executed_by="tester",
            limit=10,
        )
    assert exc.value.status_code == 400
    assert "Unsupported workflow spec version" in str(exc.value.detail)


@patch("app.modules.api_manager.workflow_executor.record_exec_step")
@patch("app.modules.api_manager.workflow_executor.record_exec_log")
@patch("app.modules.api_manager.workflow_executor.execute_script_api")
@patch("app.modules.api_manager.workflow_executor.execute_sql_api")
def test_execute_workflow_api_success_two_nodes(
    mock_exec_sql: Mock,
    mock_exec_script: Mock,
    mock_log: Mock,
    mock_step_log: Mock,
):
    mock_exec_sql.return_value = ApiExecuteResponse(
        executed_sql="SELECT 1",
        params={"tenant": "t1"},
        columns=["id"],
        rows=[{"id": 1}],
        row_count=1,
        duration_ms=3,
    )
    mock_exec_script.return_value = ApiScriptExecuteResult(
        output={"done": True},
        params={"source_rows": [{"id": 1}]},
        input={"rows": [{"id": 1}]},
        duration_ms=5,
        references={},
        logs=[],
    )
    mock_log.return_value = SimpleNamespace(exec_id="exec-1")

    sql_api = _node_api("sql-node", "SELECT :tenant as id")
    script_api = _node_api(
        "script-node",
        "def main(params, input_payload): return {'done': True}",
        {"allow_runtime": True},
    )

    session = Mock(spec=Session)
    session.get.side_effect = lambda _model, api_id: {
        "sql-node": sql_api,
        "script-node": script_api,
    }.get(api_id)

    workflow_spec = {
        "version": 1,
        "nodes": [
            {"id": "node1", "type": "sql", "api_id": "sql-node", "params": {"tenant": "{{params.tenant}}"}},
            {
                "id": "node2",
                "type": "script",
                "api_id": "script-node",
                "params": {"source_rows": "{{steps.node1.output.rows}}"},
                "input": {"rows": "{{steps.node1.output.rows}}"},
            },
        ],
    }
    result = execute_workflow_api(
        session=session,
        workflow_api=_workflow_api(workflow_spec),
        params={"tenant": "t1"},
        input_payload=None,
        executed_by="tester",
        limit=20,
    )

    assert len(result.steps) == 2
    assert result.steps[0].status == "success"
    assert result.steps[1].status == "success"
    assert result.final_output == {"done": True}
    assert mock_exec_sql.call_count == 1
    assert mock_exec_script.call_count == 1
    assert mock_step_log.call_count == 2
    assert mock_log.call_count == 1


@patch("app.modules.api_manager.workflow_executor.record_exec_step")
@patch("app.modules.api_manager.workflow_executor.record_exec_log")
def test_execute_workflow_api_node_not_found_logs_failure(
    mock_log: Mock, mock_step_log: Mock
):
    mock_log.return_value = SimpleNamespace(exec_id="exec-1")
    session = Mock(spec=Session)
    session.get.return_value = None

    spec = {"version": 1, "nodes": [{"id": "node1", "type": "sql", "api_id": "missing"}]}
    with pytest.raises(HTTPException) as exc:
        execute_workflow_api(
            session=session,
            workflow_api=_workflow_api(spec),
            params={},
            input_payload=None,
            executed_by="tester",
            limit=10,
        )
    assert exc.value.status_code == 404
    assert "not found" in str(exc.value.detail)
    assert mock_log.call_count == 1
    assert mock_step_log.call_count == 0
