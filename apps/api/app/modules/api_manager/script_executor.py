"""Orchestrates Python script execution for API Manager."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException
from sqlmodel import Session

from core.config import get_settings
from .crud import record_exec_log
from .schemas import ApiScriptExecuteResult

SCRIPT_RUNNER = Path(__file__).resolve().parent / "script_executor_runner.py"
DEFAULT_SCRIPT_TIMEOUT_MS = 5000
DEFAULT_OUTPUT_BYTES = 1_048_576


def _dict_or_empty(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _runtime_base_url() -> str:
    settings = get_settings()
    port = settings.api_port or 8000
    return f"http://127.0.0.1:{port}"


def execute_script_api(
    session: Session,
    api_id: str,
    logic_body: str,
    params: Dict[str, Any] | None,
    input_payload: Any | None,
    executed_by: str,
    runtime_policy: Dict[str, Any] | None,
) -> ApiScriptExecuteResult:
    runtime_policy = _dict_or_empty(runtime_policy or {})
    if not runtime_policy.get("allow_runtime"):
        raise HTTPException(status_code=400, detail="Script execution is disabled for this API")
    script_policy = _dict_or_empty(runtime_policy.get("script"))
    timeout_ms = int(script_policy.get("timeout_ms") or DEFAULT_SCRIPT_TIMEOUT_MS)
    max_bytes = int(script_policy.get("max_response_bytes") or DEFAULT_OUTPUT_BYTES)
    payload = {
        "script": logic_body,
        "params": params or {},
        "input": input_payload,
        "policy": script_policy,
        "base_url": _runtime_base_url(),
        "executed_by": executed_by,
        "timeout_ms": timeout_ms,
        "max_response_bytes": max_bytes,
    }
    status = "success"
    error_message: str | None = None
    duration_ms = 0
    references: Dict[str, Any] = {}
    logs: list[str] = []
    output: Dict[str, Any] = {}
    try:
        try:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_RUNNER)],
                input=json.dumps(payload).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=(timeout_ms / 1000) + 1,
            )
        except subprocess.TimeoutExpired as exc:
            status = "fail"
            error_message = "Script execution timed out"
            raise HTTPException(status_code=500, detail=error_message) from exc
        stdout = proc.stdout.decode("utf-8", errors="ignore").strip()
        stderr = proc.stderr.decode("utf-8", errors="ignore").strip()
        if proc.returncode != 0:
            status = "fail"
            error_message = stderr or stdout or "Script runner failed"
            raise HTTPException(status_code=500, detail=error_message)
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError as exc:
            status = "fail"
            error_message = "Invalid JSON from script runner"
            raise HTTPException(status_code=500, detail=error_message) from exc
        if result.get("status") != "success":
            status = "fail"
            error_message = result.get("error") or "Script runner failed"
            raise HTTPException(status_code=500, detail=error_message)
        duration_ms = int(result.get("duration_ms") or 0)
        references = result.get("references", {})
        logs = result.get("logs", [])
        output = result.get("output", {})
        return ApiScriptExecuteResult(
            output=output,
            params=params or {},
            input=input_payload,
            duration_ms=duration_ms,
            references=references,
            logs=logs,
        )
    finally:
        record_exec_log(
            session=session,
            api_id=api_id,
            status=status,
            duration_ms=duration_ms,
            row_count=0,
            params=params or {},
            executed_by=executed_by,
            error_message=error_message,
        )
