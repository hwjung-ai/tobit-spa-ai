from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from fastapi import HTTPException

from app.modules.cep_builder.crud import get_rule, record_exec_log
from app.modules.cep_builder.executor import evaluate_trigger
from core.db import get_session_context
from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
    ToolType,
)

try:
    import yaml  # type: ignore[import]
except ImportError:
    yaml = None

CI_KEYS = [
    "ci_id",
    "ci_code",
    "ci_type",
    "ci_subtype",
    "ci_category",
    "status",
    "location",
    "owner",
]
TAG_ALLOWLIST = {"system", "role", "runs_on", "host_server", "ci_subtype", "connected_servers"}
ATTR_ALLOWLIST = {"engine", "version", "zone", "ip", "cpu_cores", "memory_gb"}
MAX_PAYLOAD_BYTES = 16 * 1024
STRING_TRUNCATE = 200
DEFAULT_ALLOWED_PARAM_MAP = {
    "ci_id": "ci.ci_id",
    "ci_code": "ci.ci_code",
    "system": "ci.tags.system",
    "host_server": "ci.tags.host_server",
    "runs_on": "ci.tags.runs_on",
    "location": "ci.location",
    "owner": "ci.owner",
    "ci_type": "ci.ci_type",
    "ci_subtype": "ci.ci_subtype",
}
DEFAULT_BLOCKED_PARAM_KEYS = {"token", "authorization", "api_key", "password", "secret"}
DEFAULT_PARAM_MAX_BYTES = 2048
PARAM_MAPPING_PATH = Path(__file__).resolve().parents[1] / "cep" / "param_mapping.yaml"


def _load_param_policy() -> Tuple[Dict[str, str], set[str], int, str]:
    allowed = DEFAULT_ALLOWED_PARAM_MAP.copy()
    blocked = {key.lower() for key in DEFAULT_BLOCKED_PARAM_KEYS}
    max_bytes = DEFAULT_PARAM_MAX_BYTES
    policy_source = "fallback"
    if yaml and PARAM_MAPPING_PATH.exists():
        try:
            raw = yaml.safe_load(PARAM_MAPPING_PATH.read_text(encoding="utf-8")) or {}
            incoming_allowed = raw.get("allowed_params")
            if isinstance(incoming_allowed, dict) and incoming_allowed:
                allowed = {str(k): str(v) for k, v in incoming_allowed.items()}
            incoming_blocked = raw.get("blocked_params")
            if isinstance(incoming_blocked, list) and incoming_blocked:
                blocked = blocked.union({str(value).lower() for value in incoming_blocked if isinstance(value, str)})
            limits = raw.get("limits") or {}
            max_bytes = int(limits.get("max_param_bytes", max_bytes))
            policy_source = "yaml"
        except Exception:
            policy_source = "fallback"
    return allowed, blocked, max_bytes, policy_source


ALLOWED_PARAM_MAP, BLOCKED_PARAM_KEYS, PARAM_MAX_BYTES, PARAM_POLICY_SOURCE = _load_param_policy()


def _truncate_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= STRING_TRUNCATE else value[:STRING_TRUNCATE]
    if isinstance(value, dict):
        return {k: _truncate_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate_value(item) for item in value]
    return value


def _limit_history_recent(history: Dict[str, Any], max_entries: int) -> None:
    recent = history.get("recent") or []
    history["recent"] = recent[:max_entries]


def _shrink_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    shrunk = payload.copy()
    history = shrunk.get("history")
    if history:
        _limit_history_recent(history, 1)
    ci = shrunk.get("ci", {})
    ci.pop("tags", None)
    ci.pop("attributes", None)
    return shrunk


def _mask_params(params: Dict[str, Any] | None) -> tuple[Dict[str, Any] | None, bool]:
    if not params:
        return None, False
    masked = {}
    masked_flag = False
    for key, value in params.items():
        if isinstance(value, str) and any(token in key.lower() for token in ["token", "secret", "password", "key"]):
            masked[key] = "***"
            masked_flag = True
        else:
            masked[key] = value
    return masked, masked_flag


def _build_evidence(
    trigger_refs: Dict[str, Any],
    error: str | None = None,
    runtime_params_meta: Dict[str, Any] | None = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    trigger = trigger_refs.get("trigger", {})
    endpoint = trigger.get("runtime_endpoint") or trigger.get("endpoint")
    method = trigger.get("method") or "GET"
    params, masked = _mask_params(trigger.get("params") or {})
    value_path = trigger.get("value_path") or trigger.get("valuePath")
    op = trigger.get("op")
    threshold = trigger.get("threshold") or trigger.get("expected")
    extracted = trigger.get("extracted_value") or trigger.get("actual_value")
    truncated = False
    extracted_serialized = extracted
    if isinstance(extracted, (dict, list)):
        extracted_serialized = json.dumps(extracted)
        if len(extracted_serialized) > STRING_TRUNCATE:
            extracted_serialized = extracted_serialized[:STRING_TRUNCATE]
            truncated = True
    evidence = {
        "runtime_endpoint": endpoint,
        "method": method,
        "params": params,
        "value_path": value_path,
        "op": op,
        "threshold": threshold,
        "extracted_value": extracted_serialized,
        "condition_evaluated": trigger_refs.get("condition_evaluated"),
        "fetch_status": "error" if error else "ok",
        "fetch_error": error,
    }
    evidence_meta = {
        "params_masked": masked,
        "extracted_value_truncated": truncated,
    }
    if runtime_params_meta:
        evidence_meta["runtime_params_meta"] = runtime_params_meta
        evidence_meta["runtime_params_keys"] = runtime_params_meta.get("final_keys", [])
        evidence_meta["runtime_params_policy_source"] = runtime_params_meta.get("policy_source")
    return evidence, evidence_meta


def _truncate_text(value: Any | None, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[:limit]


def _normalize_metric_context(metric_context: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not metric_context:
        return None
    metric_name = _truncate_text(metric_context.get("metric_name"), 100)
    agg = _truncate_text(metric_context.get("agg") or metric_context.get("aggregation"), 100)
    time_range = _truncate_text(metric_context.get("time_range"), 100)
    value = metric_context.get("value")
    numeric_value = value if isinstance(value, (int, float)) else None
    return {
        "metric_name": metric_name,
        "agg": agg,
        "time_range": time_range,
        "value": numeric_value,
    }


def _normalize_history_context(history_context: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not history_context:
        return None
    source = _truncate_text(history_context.get("source"), 100) or "event_log"
    time_range = _truncate_text(history_context.get("time_range"), 100)
    count = history_context.get("rows") or history_context.get("count")
    count = count if isinstance(count, int) else None
    recent = history_context.get("recent") or []
    normalized_recent = []
    for entry in recent[:3]:
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts") or entry.get("timestamp")
        summary = entry.get("summary") or entry.get("detail") or ""
        summary = _truncate_text(summary, 120) or ""
        normalized_recent.append({"ts": ts, "summary": summary})
    if count is None:
        count = len(normalized_recent)
    return {
        "source": source,
        "time_range": time_range,
        "count": count,
        "recent": normalized_recent,
    }


def _payload_sections(payload: Dict[str, Any]) -> List[str]:
    return [section for section in ("ci", "metric", "history") if section in payload]


def _condense_metric_history(payload: Dict[str, Any]) -> None:
    metric = payload.get("metric")
    if metric:
        metric["value"] = None
    history = payload.get("history")
    if history:
        history["recent"] = history.get("recent", [])[:1]
        history["count"] = None


def _attach_payload_metadata(payload: Dict[str, Any], evidence_meta: Dict[str, Any]) -> None:
    sections = _payload_sections(payload)
    evidence_meta["test_payload_sections"] = sections
    evidence_meta["test_payload_metric_keys_present"] = "metric" in payload
    evidence_meta["test_payload_history_keys_present"] = "history" in payload


def build_test_payload(
    ci_context: Dict[str, Any],
    metric_context: Dict[str, Any] | None,
    history_context: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ci_block: Dict[str, Any] = {
        key: ci_context.get(key) for key in CI_KEYS if ci_context.get(key) is not None
    }
    tags = ci_context.get("tags") or {}
    attrs = ci_context.get("attributes") or {}
    if tags:
        ci_block["tags"] = {k: _truncate_value(v) for k, v in tags.items() if k in TAG_ALLOWLIST}
    if attrs:
        ci_block["attributes"] = {
            k: _truncate_value(v) for k, v in attrs.items() if k in ATTR_ALLOWLIST
        }
    payload: Dict[str, Any] = {"ci": ci_block}
    metric_section = _normalize_metric_context(metric_context)
    if metric_section:
        payload["metric"] = metric_section
    history_section = _normalize_history_context(history_context)
    if history_section:
        payload["history"] = history_section

    payload = _truncate_value(payload)
    size_bytes = len(json.dumps(payload))
    truncated = False
    if size_bytes > MAX_PAYLOAD_BYTES:
        payload = _shrink_payload(payload)
        truncated = True
        size_bytes = len(json.dumps(payload))
    if size_bytes > MAX_PAYLOAD_BYTES:
        _condense_metric_history(payload)
        truncated = True
        size_bytes = len(json.dumps(payload))
    if size_bytes > MAX_PAYLOAD_BYTES:
        for section in ("metric", "history"):
            if section in payload:
                payload.pop(section, None)
        truncated = True
        size_bytes = len(json.dumps(payload))
    sections = _payload_sections(payload)
    meta = {
        "sources": sections,
        "sections": sections,
        "size_bytes": size_bytes,
        "truncated": truncated,
    }
    return payload, meta


def _extract_payload_value(payload: Dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    current: Any = payload
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, dict) and part.endswith("]"):
            key, idx_part = part[:-1].split("[", 1)
            current = current.get(key)
            if isinstance(current, list):
                try:
                    index = int(idx_part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
        else:
            return None
    if isinstance(current, (str, int, float)):
        return current
    return None


def build_runtime_params_if_missing(
    existing_params: Dict[str, Any] | None,
    test_payload: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    params: Dict[str, Any] = {}
    blocked_removed: List[str] = []
    if existing_params:
        for key, value in existing_params.items():
            if key.lower() in BLOCKED_PARAM_KEYS:
                blocked_removed.append(key)
                continue
            params[key] = value
    meta: Dict[str, Any] = {
        "built": False,
        "keys_added": [],
        "keys_skipped": [],
        "blocked_removed": blocked_removed,
        "size_bytes": 0,
        "truncated": False,
        "policy_source": PARAM_POLICY_SOURCE,
    }
    for key, path in ALLOWED_PARAM_MAP.items():
        if key in params:
            continue
        value = _extract_payload_value(test_payload, path)
        if value in (None, ""):
            meta["keys_skipped"].append(key)
            continue
        if isinstance(value, (dict, list)):
            meta["keys_skipped"].append(key)
            continue
        params[key] = value
        meta["keys_added"].append(key)
    serialized = json.dumps(params)
    meta["size_bytes"] = len(serialized.encode("utf-8"))
    if meta["size_bytes"] > PARAM_MAX_BYTES:
        truncated_keys = meta["keys_added"][len(meta["keys_added"]) // 2 :]
        for tk in truncated_keys:
            params.pop(tk, None)
            meta["keys_added"].remove(tk)
            meta["keys_skipped"].append(tk)
        meta["size_bytes"] = len(json.dumps(params).encode("utf-8"))
        meta["truncated"] = True
    meta["final_keys"] = list(params.keys())
    if meta["keys_added"]:
        meta["built"] = True
    return params, meta


def cep_simulate(
    tenant_id: str,
    rule_id: str,
    ci_context: Dict[str, Any],
    metric_context: Dict[str, Any] | None = None,
    history_context: Dict[str, Any] | None = None,
    test_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if not rule_id:
        return {"success": False, "error": "rule_id is required", "rule_id": None}

    simulation_id = str(uuid4())
    exec_log_id: str | None = None
    response: Dict[str, Any] | None = None
    with get_session_context() as session:
        rule = get_rule(session, rule_id)
        if not rule:
            return {"success": False, "error": f"Rule {rule_id} not found", "rule_id": rule_id}
        start = perf_counter()
        status = "dry_run"
        references: Dict[str, Any] = {}
        error_message: str | None = None
        test_meta: Dict[str, Any] = {
            "built": False,
            "size_bytes": 0,
            "sources": [],
            "truncated": False,
        }
        payload_to_send = test_payload
        if not payload_to_send:
            payload_to_send, meta = build_test_payload(ci_context, metric_context, history_context)
            test_meta.update({"built": True, **meta})
        else:
            test_meta.update(
                {
                    "size_bytes": len(json.dumps(payload_to_send)),
                    "sources": ["ci"],
                    "truncated": len(json.dumps(payload_to_send)) > MAX_PAYLOAD_BYTES,
                }
            )
        spec = dict(rule.trigger_spec or {})
        runtime_params, runtime_meta = build_runtime_params_if_missing(spec.get("params"), payload_to_send)
        if runtime_params:
            spec["params"] = runtime_params
        try:
            condition, trigger_refs = evaluate_trigger(rule.trigger_type, spec, payload_to_send)
            references = trigger_refs
            references["ci_context"] = ci_context
            simulation = {
                "rule_id": rule_id,
                "condition_evaluated": trigger_refs.get("condition_evaluated", False),
                "triggered": bool(condition),
                "condition": condition,
                "operator": trigger_refs.get("operator"),
                "threshold": trigger_refs.get("threshold"),
                "extracted_value": trigger_refs.get("extracted_value"),
                "references": trigger_refs,
            }
            evidence, evidence_meta = _build_evidence(trigger_refs, runtime_params_meta=runtime_meta)
            _attach_payload_metadata(payload_to_send, evidence_meta)
            response = {
                "success": True,
                "simulation": simulation,
                "rule_id": rule_id,
                "references": references,
                "test_payload": payload_to_send,
                "test_payload_meta": test_meta,
                "evidence": evidence,
                "evidence_meta": evidence_meta,
            }
        except HTTPException as exc:
            status = "fail"
            error_message = str(exc.detail or exc)
            evidence, evidence_meta = _build_evidence(
                trigger_refs, error=error_message, runtime_params_meta=runtime_meta
            )
            _attach_payload_metadata(payload_to_send, evidence_meta)
            response = {
                "success": False,
                "error": error_message,
                "rule_id": rule_id,
                "references": references,
                "test_payload": payload_to_send,
                "test_payload_meta": test_meta,
                "evidence": evidence,
                "evidence_meta": evidence_meta,
            }
        except Exception as exc:
            status = "fail"
            error_message = str(exc)
            evidence, evidence_meta = _build_evidence(
                references, error=error_message, runtime_params_meta=runtime_meta
            )
            _attach_payload_metadata(payload_to_send, evidence_meta)
            response = {
                "success": False,
                "error": error_message,
                "rule_id": rule_id,
                "references": references,
                "test_payload": payload_to_send,
                "test_payload_meta": test_meta,
                "evidence": evidence,
                "evidence_meta": evidence_meta,
            }
        finally:
            duration_ms = int((perf_counter() - start) * 1000)
            references["simulation_id"] = simulation_id
            exec_log = record_exec_log(
                session=session,
                rule_id=rule_id,
                status=status,
                duration_ms=duration_ms,
                references=references,
                executed_by="ops-ci-simulate",
                error_message=error_message,
            )
            exec_log_id = str(exec_log.exec_id)
    if response is None:
        response = {"success": False, "error": "Unexpected failure", "rule_id": rule_id}
    response["simulation_id"] = simulation_id
    if exec_log_id:
        response["exec_log_id"] = exec_log_id
        response["event_browser_ref"] = {"tenant_id": tenant_id, "exec_log_id": exec_log_id}
    else:
        response["event_browser_ref"] = {"tenant_id": tenant_id, "simulation_id": simulation_id}
    return response


# ==============================================================================
# Tool Interface Implementation
# ==============================================================================


class CEPTool(BaseTool):
    """
    Tool for Complex Event Processing (CEP) operations.

    Provides methods to simulate and test CEP rules against CI configuration and
    metric/history context data.
    """

    @property
    def tool_type(self) -> ToolType:
        """Return the CEP tool type."""
        return ToolType.CEP

    async def should_execute(self, context: ToolContext, params: Dict[str, Any]) -> bool:
        """
        Determine if this tool should execute for the given operation.

        CEP tool handles operations with these parameter keys:
        - operation: 'simulate'

        Args:
            context: Execution context
            params: Tool parameters

        Returns:
            True if this is a CEP operation, False otherwise
        """
        operation = params.get("operation", "")
        return operation == "simulate"

    async def execute(self, context: ToolContext, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a CEP operation.

        Currently supports rule simulation against test payloads.

        Parameters:
            operation (str): The operation to perform ('simulate')
            rule_id (str): ID of the CEP rule to simulate
            ci_context (dict): CI configuration item context
            metric_context (dict, optional): Metric data context
            history_context (dict, optional): History/event log context
            test_payload (dict, optional): Custom test payload

        Returns:
            ToolResult with success status and simulation results
        """
        try:
            operation = params.get("operation", "")
            tenant_id = context.tenant_id

            if operation == "simulate":
                result = cep_simulate(
                    tenant_id=tenant_id,
                    rule_id=params["rule_id"],
                    ci_context=params.get("ci_context", {}),
                    metric_context=params.get("metric_context"),
                    history_context=params.get("history_context"),
                    test_payload=params.get("test_payload"),
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown CEP operation: {operation}",
                )

            return ToolResult(success=True, data=result)

        except ValueError as e:
            return await self.format_error(context, e, params)
        except Exception as e:
            return await self.format_error(context, e, params)


# Create and register the CEP tool
_cep_tool = CEPTool()
