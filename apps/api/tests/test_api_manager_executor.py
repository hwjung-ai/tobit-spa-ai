"""Current API Manager executor and router dispatch tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from app.modules.api_manager.executor import (
    _render_http_templates,
    execute_http_api,
    normalize_limit,
    validate_select_sql,
)
from app.modules.api_manager.router import (
    ExecuteApiRequest,
    execute_api,
    get_logs,
    get_versions,
    list_discovered_endpoints,
)
from app.modules.api_manager.schemas import ApiExecuteResponse
from fastapi import HTTPException
from sqlmodel import Session


def _api_stub(mode: str, logic: str = "SELECT 1", runtime_policy: dict | None = None):
    return SimpleNamespace(
        id="api-1",
        deleted_at=None,
        logic=logic,
        mode=SimpleNamespace(value=mode),
        runtime_policy=runtime_policy or {},
    )


def test_validate_select_sql_valid_select_and_with():
    validate_select_sql("SELECT id FROM users")
    validate_select_sql("WITH t AS (SELECT 1) SELECT * FROM t")


@pytest.mark.parametrize(
    "sql, expected",
    [
        ("SELECT 1; SELECT 2", "Semicolons"),
        ("INSERT INTO x VALUES (1)", "Only SELECT/WITH"),
        ("SELECT * FROM x WHERE name = 'a' UPDATE x SET y=1", "Forbidden keyword"),
    ],
)
def test_validate_select_sql_rejects_unsafe(sql: str, expected: str):
    with pytest.raises(HTTPException) as exc:
        validate_select_sql(sql)
    assert exc.value.status_code == 400
    assert expected in str(exc.value.detail)


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, 200),
        (0, 1),
        (-10, 1),
        (100, 100),
        (9999, 1000),
    ],
)
def test_normalize_limit(value: int | None, expected: int):
    assert normalize_limit(value) == expected


def test_render_http_templates_nested_success():
    spec = {
        "url": "https://example.com/items/{{params.item_id}}",
        "headers": {"x-tenant-id": "{{params.tenant.id}}"},
        "body": {"raw": "{{params.tenant}}", "tag": "prefix-{{params.item_id}}"},
    }
    params = {"item_id": 42, "tenant": {"id": "t1"}}

    rendered = _render_http_templates(spec, params)

    assert rendered["url"] == "https://example.com/items/42"
    assert rendered["headers"]["x-tenant-id"] == "t1"
    assert rendered["body"]["raw"] == {"id": "t1"}
    assert rendered["body"]["tag"] == "prefix-42"


def test_render_http_templates_missing_param_raises():
    with pytest.raises(HTTPException) as exc:
        _render_http_templates({"url": "{{params.missing}}"}, {})
    assert exc.value.status_code == 400


@patch("app.modules.api_manager.executor.record_exec_log")
@patch("app.modules.api_manager.executor.httpx.request")
def test_execute_http_api_success(mock_request: Mock, mock_log: Mock):
    response = Mock()
    response.json.return_value = {"ok": True, "count": 1}
    mock_request.return_value = response

    session = Mock(spec=Session)
    logic_body = json.dumps(
        {
            "method": "POST",
            "url": "https://api.example.com/items/{{params.item_id}}",
            "headers": {"X-Tenant-ID": "{{params.tenant_id}}"},
            "body": {"value": "{{params.value}}"},
        }
    )

    result = execute_http_api(
        session=session,
        api_id="api-1",
        logic_body=logic_body,
        params={"item_id": 7, "tenant_id": "t1", "value": "A"},
        executed_by="tester",
    )

    assert isinstance(result, ApiExecuteResponse)
    assert result.rows == [{"ok": True, "count": 1}]
    assert result.columns == ["count", "ok"]
    assert result.row_count == 1
    mock_request.assert_called_once()
    _, called_url = mock_request.call_args.args[0], mock_request.call_args.args[1]
    assert called_url == "https://api.example.com/items/7"
    assert mock_log.call_count == 1


@patch("app.modules.api_manager.executor.record_exec_log")
def test_execute_http_api_invalid_json(mock_log: Mock):
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_http_api(
            session=session,
            api_id="api-1",
            logic_body="{bad json",
            params={},
            executed_by="tester",
        )
    assert exc.value.status_code == 400
    assert "Invalid HTTP logic body" in str(exc.value.detail)
    mock_log.assert_not_called()


@patch("app.modules.api_manager.executor.record_exec_log")
@patch("app.modules.api_manager.executor.httpx.request")
def test_execute_http_api_transport_error(mock_request: Mock, mock_log: Mock):
    mock_request.side_effect = RuntimeError("network down")
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_http_api(
            session=session,
            api_id="api-1",
            logic_body=json.dumps({"method": "GET", "url": "https://api.example.com"}),
            params={},
            executed_by="tester",
        )
    assert exc.value.status_code == 502
    assert "External HTTP request failed" in str(exc.value.detail)
    assert mock_log.call_count == 1
    assert mock_log.call_args.kwargs["status"] == "fail"


@pytest.mark.asyncio
@patch("app.modules.api_manager.router.execute_sql_api")
async def test_router_execute_api_sql_dispatch(mock_exec: Mock):
    mock_exec.return_value = ApiExecuteResponse(
        executed_sql="SELECT 1",
        params={},
        columns=["value"],
        rows=[{"value": 1}],
        row_count=1,
        duration_ms=1,
    )
    session = Mock(spec=Session)
    session.get.return_value = _api_stub("sql", "SELECT 1")

    envelope = await execute_api(
        api_id="api-1",
        request=ExecuteApiRequest(params={}),
        session=session,
        current_user=SimpleNamespace(id="u1"),
    )

    assert envelope.code == 0
    assert envelope.data["result"]["row_count"] == 1
    mock_exec.assert_called_once()


@pytest.mark.asyncio
@patch("app.modules.api_manager.router.execute_http_api")
async def test_router_execute_api_http_dispatch(mock_exec: Mock):
    mock_exec.return_value = ApiExecuteResponse(
        executed_sql="HTTP GET https://api.example.com",
        params={},
        columns=["ok"],
        rows=[{"ok": True}],
        row_count=1,
        duration_ms=1,
    )
    session = Mock(spec=Session)
    session.get.return_value = _api_stub(
        "http", json.dumps({"method": "GET", "url": "https://api.example.com"})
    )

    envelope = await execute_api(
        api_id="api-1",
        request=ExecuteApiRequest(params={}),
        session=session,
        current_user=SimpleNamespace(id="u1"),
    )

    assert envelope.code == 0
    assert envelope.data["result"]["rows"][0]["ok"] is True
    mock_exec.assert_called_once()


@pytest.mark.asyncio
@patch("app.modules.api_manager.router.execute_script_api")
async def test_router_execute_api_script_dispatch(mock_exec: Mock):
    mock_exec.return_value = SimpleNamespace(
        model_dump=lambda: {
            "output": {"ok": True},
            "params": {},
            "input": None,
            "duration_ms": 1,
            "references": {},
            "logs": [],
        }
    )
    session = Mock(spec=Session)
    session.get.return_value = _api_stub(
        "script",
        "def main(params, input_payload):\n    return {'ok': True}",
        {"allow_runtime": True},
    )

    envelope = await execute_api(
        api_id="api-1",
        request=ExecuteApiRequest(params={}),
        session=session,
        current_user=SimpleNamespace(id="u1"),
    )

    assert envelope.code == 0
    assert envelope.data["result"]["output"]["ok"] is True
    mock_exec.assert_called_once()


@pytest.mark.asyncio
@patch("app.modules.api_manager.router.execute_workflow_api")
async def test_router_execute_api_workflow_dispatch(mock_exec: Mock):
    mock_exec.return_value = SimpleNamespace(
        model_dump=lambda: {"steps": [], "final_output": {"ok": True}, "references": []}
    )
    session = Mock(spec=Session)
    session.get.return_value = _api_stub("workflow", '{"version":1,"nodes":[]}')

    envelope = await execute_api(
        api_id="api-1",
        request=ExecuteApiRequest(params={}),
        session=session,
        current_user=SimpleNamespace(id="u1"),
    )

    assert envelope.code == 0
    assert envelope.data["result"]["final_output"]["ok"] is True
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_router_execute_api_unsupported_mode():
    session = Mock(spec=Session)
    session.get.return_value = _api_stub("unsupported", "SELECT 1")

    with pytest.raises(HTTPException) as exc:
        await execute_api(
            api_id="api-1",
            request=ExecuteApiRequest(params={}),
            session=session,
            current_user=SimpleNamespace(id="u1"),
        )
    assert exc.value.status_code == 400
    assert "Unsupported API mode" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_router_get_versions_success():
    session = Mock(spec=Session)
    session.get.return_value = SimpleNamespace(id="api-1", deleted_at=None)
    session.exec.return_value.all.return_value = [
        SimpleNamespace(
            version=2,
            change_type="update",
            change_summary="changed logic",
            created_by="tester",
            created_at=None,
            snapshot={"mode": "sql"},
        ),
        SimpleNamespace(
            version=1,
            change_type="create",
            change_summary=None,
            created_by="tester",
            created_at=None,
            snapshot={"mode": "sql"},
        ),
    ]

    envelope = await get_versions(api_id="api-1", session=session)

    assert envelope.code == 0
    assert envelope.data["api_id"] == "api-1"
    assert len(envelope.data["versions"]) == 2
    assert envelope.data["versions"][0]["is_current"] is True
    assert envelope.data["versions"][1]["is_current"] is False


@pytest.mark.asyncio
@patch("app.modules.api_manager.router.list_exec_logs")
async def test_router_get_logs_success(mock_list_logs: Mock):
    mock_list_logs.return_value = [
        SimpleNamespace(
            exec_id="e1",
            api_id="api-1",
            executed_at=None,
            executed_by="tester",
            status="success",
            duration_ms=8,
            row_count=1,
            request_params={"x": 1},
            error_message=None,
        )
    ]
    session = Mock(spec=Session)

    envelope = await get_logs(api_id="api-1", limit=20, session=session)

    assert envelope.code == 0
    assert envelope.data["api_id"] == "api-1"
    assert envelope.data["logs"][0]["status"] == "success"
    mock_list_logs.assert_called_once_with(session, "api-1", 20)


@pytest.mark.asyncio
async def test_router_list_discovered_endpoints_from_openapi():
    app = SimpleNamespace(
        openapi=lambda: {
            "paths": {
                "/health": {
                    "get": {
                        "operationId": "health_check",
                        "summary": "Health check",
                        "description": "returns health",
                        "tags": ["system"],
                        "parameters": [],
                        "responses": {"200": {"description": "ok"}},
                    }
                },
                "/api-manager/apis": {
                    "post": {
                        "operationId": "create_api",
                        "summary": "Create API",
                        "tags": ["api-manager"],
                        "parameters": [],
                        "responses": {"200": {"description": "ok"}},
                    }
                },
            }
        },
        routes=[],
    )
    request = SimpleNamespace(app=app)

    envelope = await list_discovered_endpoints(request=request)

    assert envelope.code == 0
    assert envelope.data["count"] == 2
    methods = {(item["method"], item["path"]) for item in envelope.data["endpoints"]}
    assert ("GET", "/health") in methods
    assert ("POST", "/api-manager/apis") in methods
    assert all(item["source"] == "openapi" for item in envelope.data["endpoints"])
