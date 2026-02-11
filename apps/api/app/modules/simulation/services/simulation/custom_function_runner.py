from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.config import get_settings
from fastapi import HTTPException

from app.modules.simulation.schemas import SimulationCustomFunctionSpec

SCRIPT_RUNNER = (
    Path(__file__).resolve().parents[3]
    / "api_manager"
    / "script_executor_runner.py"
)
DEFAULT_TIMEOUT_MS = 5000
DEFAULT_MAX_RESPONSE_BYTES = 1_048_576


def _runtime_base_url() -> str:
    settings = get_settings()
    port = settings.api_port or 8000
    return f"http://127.0.0.1:{port}"


def _ensure_type(value: Any, expected: str, location: str) -> None:
    if expected == "object" and not isinstance(value, dict):
        raise HTTPException(status_code=400, detail=f"{location} must be object")
    if expected == "array" and not isinstance(value, list):
        raise HTTPException(status_code=400, detail=f"{location} must be array")
    if expected == "string" and not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{location} must be string")
    if expected == "number" and not isinstance(value, (int, float)):
        raise HTTPException(status_code=400, detail=f"{location} must be number")
    if expected == "boolean" and not isinstance(value, bool):
        raise HTTPException(status_code=400, detail=f"{location} must be boolean")


def _validate_schema(data: Any, schema: dict[str, Any], location: str) -> None:
    if not schema:
        return

    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        _ensure_type(data, schema_type, location)

    if isinstance(data, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in data:
                    raise HTTPException(status_code=400, detail=f"{location}.{key} is required")

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in data and isinstance(child_schema, dict):
                    _validate_schema(data[key], child_schema, f"{location}.{key}")

    if isinstance(data, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for idx, item in enumerate(data):
                _validate_schema(item, items, f"{location}[{idx}]")


def _build_script(function_name: str, body: str) -> str:
    return (
        f"{body}\n\n"
        "def main(params, input_payload, ctx):\n"
        f"    fn = globals().get({function_name!r})\n"
        "    if not callable(fn):\n"
        "        raise RuntimeError('Function not found: ' + str(" + repr(function_name) + "))\n"
        "    return fn(params, input_payload)\n"
    )


def execute_custom_function(
    *,
    function: SimulationCustomFunctionSpec,
    params: dict[str, Any],
    input_payload: dict[str, Any],
) -> dict[str, Any]:
    _validate_schema(input_payload, function.input_schema, "input")

    runtime_policy = function.runtime_policy or {}
    timeout_ms = int(runtime_policy.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
    max_bytes = int(runtime_policy.get("max_response_bytes") or DEFAULT_MAX_RESPONSE_BYTES)

    payload = {
        "script": _build_script(function.function_name, function.code),
        "params": params,
        "input": input_payload,
        "policy": {
            "allow_network": bool(runtime_policy.get("allow_network", False)),
            "allowed_hosts": runtime_policy.get("allowed_hosts", []),
            "blocked_private_ranges": bool(runtime_policy.get("blocked_private_ranges", True)),
            "max_response_bytes": max_bytes,
        },
        "base_url": _runtime_base_url(),
        "executed_by": "sim-custom-function",
        "timeout_ms": timeout_ms,
        "max_response_bytes": max_bytes,
    }

    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_RUNNER)],
            input=json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=(timeout_ms / 1000) + 1,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=500, detail="Custom function execution timed out") from exc

    stdout = proc.stdout.decode("utf-8", errors="ignore").strip()
    stderr = proc.stderr.decode("utf-8", errors="ignore").strip()
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=stderr or stdout or "Custom function runner failed")

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid JSON from custom function runner") from exc

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result.get("error") or "Custom function failed")

    output = result.get("output")
    _validate_schema(output, function.output_schema, "output")

    return {
        "output": output,
        "duration_ms": int(result.get("duration_ms") or 0),
        "logs": result.get("logs", []),
        "references": result.get("references", {}),
    }
