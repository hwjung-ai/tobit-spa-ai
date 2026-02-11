from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.simulation.schemas import SimulationCustomFunctionSpec
from app.modules.simulation.services.simulation.custom_function_runner import (
    execute_custom_function,
)


def _spec(**kwargs) -> SimulationCustomFunctionSpec:
    data = {
        "name": "custom_sim",
        "function_name": "simulate",
        "input_schema": {"type": "object", "required": ["x"]},
        "output_schema": {"type": "object", "required": ["kpis"]},
        "code": "def simulate(params, input_payload):\n    return {'kpis': []}",
        "runtime_policy": {"timeout_ms": 1000},
    }
    data.update(kwargs)
    return SimulationCustomFunctionSpec(**data)


def test_execute_custom_function_success(monkeypatch):
    output = {
        "status": "success",
        "output": {"kpis": []},
        "duration_ms": 4,
        "logs": ["ok"],
        "references": {"source": "unit"},
    }

    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.custom_function_runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(output).encode("utf-8"),
            stderr=b"",
        ),
    )

    result = execute_custom_function(
        function=_spec(),
        params={"tenant_id": "t1"},
        input_payload={"x": 1},
    )

    assert result["output"] == {"kpis": []}
    assert result["duration_ms"] == 4


def test_execute_custom_function_rejects_schema_mismatch(monkeypatch):
    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.custom_function_runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b"{}", stderr=b""),
    )

    with pytest.raises(HTTPException) as exc:
        execute_custom_function(
            function=_spec(),
            params={},
            input_payload={},
        )
    assert exc.value.status_code == 400


def test_execute_custom_function_runner_error(monkeypatch):
    monkeypatch.setattr(
        "app.modules.simulation.services.simulation.custom_function_runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=b"", stderr=b"boom"),
    )

    with pytest.raises(HTTPException) as exc:
        execute_custom_function(
            function=_spec(input_schema={"type": "object"}),
            params={},
            input_payload={},
        )
    assert exc.value.status_code == 500
