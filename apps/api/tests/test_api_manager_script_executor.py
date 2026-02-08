from __future__ import annotations

import json
import subprocess
from unittest.mock import Mock, patch

import pytest
from app.modules.api_manager.script_executor import execute_script_api
from fastapi import HTTPException
from sqlmodel import Session


@patch("app.modules.api_manager.script_executor.record_exec_log")
def test_execute_script_api_requires_allow_runtime(mock_log: Mock):
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_script_api(
            session=session,
            api_id="api-1",
            logic_body="def main(params, input_payload): return {}",
            params={},
            input_payload=None,
            executed_by="tester",
            runtime_policy={},
        )
    assert exc.value.status_code == 400
    assert "disabled" in str(exc.value.detail)
    mock_log.assert_not_called()


@patch("app.modules.api_manager.script_executor.record_exec_log")
@patch("app.modules.api_manager.script_executor.subprocess.run")
def test_execute_script_api_success(mock_run: Mock, mock_log: Mock):
    payload = {
        "status": "success",
        "duration_ms": 12,
        "output": {"answer": 42},
        "references": {"sql": "SELECT 1"},
        "logs": ["ok"],
    }
    mock_run.return_value = SimpleNamespaceLike(
        returncode=0,
        stdout=json.dumps(payload).encode("utf-8"),
        stderr=b"",
    )

    session = Mock(spec=Session)
    result = execute_script_api(
        session=session,
        api_id="api-1",
        logic_body="def main(params, input_payload): return {'answer': 42}",
        params={"x": 1},
        input_payload={"y": 2},
        executed_by="tester",
        runtime_policy={"allow_runtime": True},
    )

    assert result.output == {"answer": 42}
    assert result.references == {"sql": "SELECT 1"}
    assert result.logs == ["ok"]
    assert mock_log.call_count == 1
    assert mock_log.call_args.kwargs["status"] == "success"


@patch("app.modules.api_manager.script_executor.record_exec_log")
@patch("app.modules.api_manager.script_executor.subprocess.run")
def test_execute_script_api_runner_timeout(mock_run: Mock, mock_log: Mock):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["python"], timeout=1)
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_script_api(
            session=session,
            api_id="api-1",
            logic_body="def main(params, input_payload): return {}",
            params={},
            input_payload=None,
            executed_by="tester",
            runtime_policy={"allow_runtime": True, "script": {"timeout_ms": 100}},
        )
    assert exc.value.status_code == 500
    assert "timed out" in str(exc.value.detail)
    assert mock_log.call_count == 1
    assert mock_log.call_args.kwargs["status"] == "fail"


@patch("app.modules.api_manager.script_executor.record_exec_log")
@patch("app.modules.api_manager.script_executor.subprocess.run")
def test_execute_script_api_runner_returns_nonzero(mock_run: Mock, mock_log: Mock):
    mock_run.return_value = SimpleNamespaceLike(
        returncode=1,
        stdout=b"",
        stderr=b"runner failed",
    )
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_script_api(
            session=session,
            api_id="api-1",
            logic_body="def main(params, input_payload): return {}",
            params={},
            input_payload=None,
            executed_by="tester",
            runtime_policy={"allow_runtime": True},
        )
    assert exc.value.status_code == 500
    assert "runner failed" in str(exc.value.detail)
    assert mock_log.call_count == 1
    assert mock_log.call_args.kwargs["status"] == "fail"


@patch("app.modules.api_manager.script_executor.record_exec_log")
@patch("app.modules.api_manager.script_executor.subprocess.run")
def test_execute_script_api_invalid_runner_json(mock_run: Mock, mock_log: Mock):
    mock_run.return_value = SimpleNamespaceLike(
        returncode=0,
        stdout=b"{not-json",
        stderr=b"",
    )
    session = Mock(spec=Session)
    with pytest.raises(HTTPException) as exc:
        execute_script_api(
            session=session,
            api_id="api-1",
            logic_body="def main(params, input_payload): return {}",
            params={},
            input_payload=None,
            executed_by="tester",
            runtime_policy={"allow_runtime": True},
        )
    assert exc.value.status_code == 500
    assert "Invalid JSON" in str(exc.value.detail)
    assert mock_log.call_count == 1
    assert mock_log.call_args.kwargs["status"] == "fail"


class SimpleNamespaceLike:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
