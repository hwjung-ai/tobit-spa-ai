"""Executes workflow APIs by orchestrating SQL and script nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict

from fastapi import HTTPException
from sqlmodel import Session

from .crud import record_exec_log, record_exec_step
from .executor import execute_sql_api
from .models import TbApiDef
from .script_executor import execute_script_api
from .schemas import WorkflowExecuteResult, WorkflowStep

PLACEHOLDER_PATTERN = re.compile(r"{{\s*([^}\s]+)\s*}}")


@dataclass
class _WorkflowStepRecord:
    node_id: str
    node_type: str
    status: str
    duration_ms: int
    row_count: int
    columns: list[str] | None = None
    output: dict[str, Any] | None = None
    references: dict[str, Any] | None = None
    error_message: str | None = None


def execute_workflow_api(
    session: Session,
    workflow_api: TbApiDef,
    params: Dict[str, Any] | None,
    input_payload: Any | None,
    executed_by: str,
    limit: int | None,
) -> WorkflowExecuteResult:
    params = params or {}
    workflow_params = dict(params)
    if input_payload is not None:
        workflow_params["input"] = input_payload
    spec = workflow_api.logic_spec or {}
    if not isinstance(spec, dict):
        raise HTTPException(status_code=400, detail="Workflow spec must be a dictionary")
    version = spec.get("version", 1)
    if version != 1:
        raise HTTPException(status_code=400, detail="Unsupported workflow spec version")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise HTTPException(status_code=400, detail="Workflow spec must define at least one node")
    seen_ids: set[str] = set()
    for node in nodes:
        node_id = node.get("id")
        if not node_id or not isinstance(node_id, str):
            raise HTTPException(status_code=400, detail="Every workflow node requires an id")
        if node_id in seen_ids:
            raise HTTPException(status_code=400, detail=f"Duplicate node id '{node_id}'")
        seen_ids.add(node_id)

    steps_context: dict[str, dict[str, Any]] = {}
    step_records: list[_WorkflowStepRecord] = []
    references: list[dict[str, Any]] = []
    final_output: dict[str, Any] | None = None
    status = "success"
    error_message: str | None = None
    start = perf_counter()
    try:
        for node in nodes:
            node_id = node["id"]
            node_type = node.get("type")
            if node_type not in {"sql", "script"}:
                raise HTTPException(status_code=400, detail=f"Unsupported node type '{node_type}'")
            node_api_id = node.get("api_id")
            if not node_api_id:
                raise HTTPException(status_code=400, detail=f"Node '{node_id}' missing api_id")
            node_api = session.get(TbApiDef, node_api_id)
            if not node_api:
                raise HTTPException(status_code=404, detail=f"Node API '{node_api_id}' not found")
            node_params = _render_templates(node.get("params") or {}, workflow_params, steps_context)
            node_input = _render_templates(node.get("input"), workflow_params, steps_context) if node_type == "script" else None
            node_limit = _parse_node_limit(node.get("limit"), limit)
            step_result: _WorkflowStepRecord
            step_refs: dict[str, Any] | None = None
            step_rows: list[dict[str, Any]] = []
            step_columns: list[str] | None = None
            step_output: dict[str, Any] | None = None
            node_start = perf_counter()
            try:
                if node_type == "sql":
                    sql_result = execute_sql_api(
                        session=session,
                        api_id=str(node_api.api_id),
                        logic_body=node_api.logic_body,
                        params=node_params,
                        limit=node_limit,
                        executed_by=executed_by,
                    )
                    step_rows = sql_result.rows
                    step_columns = sql_result.columns
                    step_output = {"columns": sql_result.columns, "rows": sql_result.rows}
                    step_refs = {
                        "node_id": node_id,
                        "node_type": "sql",
                        "sql_template": node_api.logic_body,
                        "params": node_params,
                        "limit": node_limit,
                    }
                else:
                    script_result = execute_script_api(
                        session=session,
                        api_id=str(node_api.api_id),
                        logic_body=node_api.logic_body,
                        params=node_params,
                        input_payload=node_input,
                        executed_by=executed_by,
                        runtime_policy=node_api.runtime_policy,
                    )
                    step_output = script_result.output
                    step_rows = []
                    step_columns = None
                    step_refs = {
                        "node_id": node_id,
                        "node_type": "script",
                        "references": script_result.references,
                    }
            except HTTPException as exc:
                status = "fail"
                error_message = exc.detail if isinstance(exc.detail, str) else str(exc)
                duration_ms = int((perf_counter() - node_start) * 1000)
                step = _WorkflowStepRecord(
                    node_id=node_id,
                    node_type=node_type,
                    status="fail",
                    duration_ms=duration_ms,
                    row_count=len(step_rows),
                    columns=step_columns,
                    output=step_output,
                    references=step_refs,
                    error_message=error_message,
                )
                step_records.append(step)
                raise
            except Exception as exc:
                status = "fail"
                error_message = "Workflow node execution failed"
                duration_ms = int((perf_counter() - node_start) * 1000)
                step = _WorkflowStepRecord(
                    node_id=node_id,
                    node_type=node_type,
                    status="fail",
                    duration_ms=duration_ms,
                    row_count=len(step_rows),
                    columns=step_columns,
                    output=step_output,
                    references=step_refs,
                    error_message=str(exc),
                )
                step_records.append(step)
                raise HTTPException(status_code=500, detail=error_message) from exc
            duration_ms = int((perf_counter() - node_start) * 1000)
            step = _WorkflowStepRecord(
                node_id=node_id,
                node_type=node_type,
                status="success",
                duration_ms=duration_ms,
                row_count=len(step_rows),
                columns=step_columns,
                output=step_output,
                references=step_refs,
            )
            step_records.append(step)
            steps_context[node_id] = {
                "rows": step_rows,
                "output": step_output,
            }
            if step_refs:
                references.append(step_refs)
            final_output = step_output or {"rows": step_rows}
        return WorkflowExecuteResult(
            steps=[WorkflowStep(**step.__dict__) for step in step_records],
            final_output=final_output or {},
            references=references,
        )
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        exec_row_count = step_records[-1].row_count if step_records else 0
        log = record_exec_log(
            session=session,
            api_id=str(workflow_api.api_id),
            status=status,
            duration_ms=duration_ms,
            row_count=exec_row_count,
            params=workflow_params,
            executed_by=executed_by,
            error_message=error_message,
        )
        for step in step_records:
            record_exec_step(
                session=session,
                exec_id=str(log.exec_id),
                node_id=step.node_id,
                node_type=step.node_type,
                status=step.status,
                duration_ms=step.duration_ms,
                row_count=step.row_count,
                references=step.references,
                error_message=step.error_message,
            )


def _render_templates(value: Any, params: Dict[str, Any], steps: Dict[str, dict[str, Any]]) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {key: _render_templates(item, params, steps) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_templates(item, params, steps) for item in value]
    if isinstance(value, str):
        matches = list(PLACEHOLDER_PATTERN.finditer(value))
        if not matches:
            return value
        if len(matches) == 1 and matches[0].group(0).strip() == value.strip():
            return _evaluate_expression(matches[0].group(1), params, steps)
        def _replace(match: re.Match[str]) -> str:
            resolved = _evaluate_expression(match.group(1), params, steps)
            return str(resolved)
        return PLACEHOLDER_PATTERN.sub(_replace, value)
    return value


def _evaluate_expression(expression: str, params: Dict[str, Any], steps: Dict[str, dict[str, Any]]) -> Any:
    parts = expression.split(".")
    if not parts:
        raise HTTPException(status_code=400, detail=f"Invalid template expression '{expression}'")
    head, *rest = parts
    if head == "params":
        return _resolve_path(params, rest, f"missing param for '{expression}'")
    if head == "steps":
        if len(rest) < 2:
            raise HTTPException(status_code=400, detail=f"Workflow expression '{expression}' is malformed")
        node_id = rest[0]
        if node_id not in steps:
            raise HTTPException(status_code=400, detail=f"Unknown workflow step '{node_id}'")
        return _resolve_path(steps[node_id], rest[1:], f"Workflow step '{node_id}' missing data for '{expression}'")
    raise HTTPException(status_code=400, detail=f"Unsupported template root '{head}' in '{expression}'")


def _resolve_path(source: Any, keys: list[str], error_message: str) -> Any:
    current = source
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            raise HTTPException(status_code=400, detail=error_message)
    return current


def _parse_node_limit(node_limit: Any, default_limit: int | None) -> int | None:
    if node_limit is None:
        return default_limit
    try:
        return int(node_limit)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Workflow node limit must be an integer")
