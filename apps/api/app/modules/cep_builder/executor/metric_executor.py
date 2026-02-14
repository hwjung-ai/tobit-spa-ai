"""Metric polling and aggregation logic for CEP Builder."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import httpx
from core.config import get_settings
from fastapi import HTTPException

from .rule_executor import get_path_value


def _runtime_base_url() -> str:
    """Get base URL for runtime API."""
    settings = get_settings()
    port = settings.api_port or 8000
    return f"http://127.0.0.1:{port}"


def _resolve_metric_request(
    trigger_spec: Dict[str, Any],
) -> Tuple[str, str, Dict[str, Any]]:
    """Resolve metric request details from trigger spec."""
    endpoint = trigger_spec.get("endpoint")
    if not endpoint:
        raise HTTPException(
            status_code=400, detail="Metric trigger endpoint is required"
        )
    method = str(trigger_spec.get("method", "GET")).upper()
    if method not in {"GET", "POST"}:
        raise HTTPException(
            status_code=400, detail="Metric trigger method must be GET or POST"
        )
    params = trigger_spec.get("params") or {}
    if not isinstance(params, dict):
        raise HTTPException(
            status_code=400, detail="Metric trigger params must be an object"
        )
    url = (
        endpoint if endpoint.startswith("http") else f"{_runtime_base_url()}{endpoint}"
    )
    return url, method, params.copy()


def fetch_runtime_value(
    trigger_spec: Dict[str, Any],
) -> Tuple[Dict[str, Any], Any | None]:
    """Fetch metric value from runtime endpoint."""
    settings = get_settings()
    timeout = settings.cep_metric_http_timeout_seconds
    url, method, params = _resolve_metric_request(trigger_spec)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = (
                client.get(url, params=params)
                if method == "GET"
                else client.post(url, json=params)
            )
            response.raise_for_status()
            raw_payload = response.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502, detail=f"Runtime request failed: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Runtime response error: {exc.response.status_code}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="Runtime response is not valid JSON"
        ) from exc
    value_path = trigger_spec.get("value_path")
    extracted_value = get_path_value(raw_payload, value_path)
    return raw_payload, extracted_value


METRIC_OPERATORS = {">", "<", ">=", "<=", "=="}


def _evaluate_metric_trigger(
    trigger_spec: Dict[str, Any],
    payload: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    """Evaluate metric trigger."""
    spec = trigger_spec
    references: Dict[str, Any] = {"trigger_spec": spec}
    source = spec.get("source", "runtime")
    if source != "runtime":
        raise HTTPException(
            status_code=400, detail=f"Unsupported metric source: {source}"
        )

    value_path = spec.get("value_path")
    if not value_path or not isinstance(value_path, str):
        raise HTTPException(
            status_code=400, detail="Metric trigger value_path is required"
        )
    op = str(spec.get("op", "==")).strip()
    if op not in METRIC_OPERATORS:
        raise HTTPException(status_code=400, detail=f"Unsupported operator: {op}")

    threshold_raw = spec.get("threshold")
    if threshold_raw is None:
        raise HTTPException(
            status_code=400, detail="Metric trigger threshold is required"
        )
    try:
        threshold_value = float(threshold_raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400, detail="Metric trigger threshold must be numeric"
        )

    url, method, params = _resolve_metric_request(spec)
    references.update(
        {
            "runtime_endpoint": url,
            "method": method,
            "params": params,
            "value_path": value_path,
            "op": op,
            "threshold": threshold_value,
            "used_test_payload": payload is not None,
        }
    )

    if payload is None:
        _, extracted_value = fetch_runtime_value(spec)
    else:
        extracted_value = get_path_value(payload, value_path)
    references["extracted_value"] = extracted_value

    if extracted_value is None:
        references["condition_evaluated"] = False
        references["error_reason"] = "value_path did not resolve"
        return False, references

    try:
        actual_value = float(extracted_value)
    except (TypeError, ValueError):
        references["condition_evaluated"] = False
        references["error_reason"] = "extracted value is not numeric"
        return False, references

    comparisons = {
        ">": actual_value > threshold_value,
        "<": actual_value < threshold_value,
        ">=": actual_value >= threshold_value,
        "<=": actual_value <= threshold_value,
        "==": actual_value == threshold_value,
    }
    matched = comparisons.get(op)
    references["condition_evaluated"] = True
    references["actual_value"] = actual_value

    # Aggregation support
    aggregation_spec = spec.get("aggregation")
    if aggregation_spec:
        references["aggregation_spec"] = aggregation_spec
        references["note"] = "Aggregation spec present; full windowing support requires Redis or state storage"

    return matched, references


def _apply_aggregation(
    values: list[Any],
    agg_type: str,
    percentile_value: float | None = None,
) -> float | None:
    """Apply aggregation function to values."""
    if not values:
        return None

    numeric_values = [v for v in values if isinstance(v, (int, float)) and v is not None]

    if not numeric_values:
        return None

    agg_type = agg_type.lower() if agg_type else "count"

    try:
        if agg_type == "count":
            return float(len(numeric_values))
        elif agg_type == "sum":
            return float(sum(numeric_values))
        elif agg_type == "avg" or agg_type == "average":
            return float(sum(numeric_values)) / len(numeric_values)
        elif agg_type == "min":
            return float(min(numeric_values))
        elif agg_type == "max":
            return float(max(numeric_values))
        elif agg_type == "std" or agg_type == "stddev":
            if len(numeric_values) < 2:
                return 0.0
            mean = sum(numeric_values) / len(numeric_values)
            variance = sum((x - mean) ** 2 for x in numeric_values) / (
                len(numeric_values) - 1
            )
            return float(variance**0.5)
        elif agg_type == "percentile":
            if percentile_value is None or not (0 <= percentile_value <= 100):
                return None
            sorted_values = sorted(numeric_values)
            index = (percentile_value / 100.0) * (len(sorted_values) - 1)
            lower = int(index)
            upper = lower + 1
            if upper >= len(sorted_values):
                return float(sorted_values[lower])
            weight = index - lower
            return float(
                sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
            )
        else:
            return None
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def evaluate_aggregation(
    window_events: list[Dict[str, Any]],
    aggregation_spec: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Evaluate aggregation over a window of events."""
    if not window_events or not aggregation_spec:
        return False, {"reason": "No events or aggregation spec"}

    agg_type = aggregation_spec.get("type", "count")
    field = aggregation_spec.get("field")
    threshold = aggregation_spec.get("threshold")

    # Extract field values from window events
    if field:
        values = []
        for event in window_events:
            payload = event.get("data", event)
            value = get_path_value(payload, field)
            if value is not None:
                values.append(value)
    else:
        values = [1] * len(window_events)
        agg_type = "count"

    # Apply aggregation
    percentile_value = aggregation_spec.get("percentile_value")
    aggregated_value = _apply_aggregation(values, agg_type, percentile_value)

    if aggregated_value is None:
        return False, {"reason": f"Cannot compute {agg_type} aggregation"}

    # Evaluate condition if threshold provided
    if threshold is not None:
        op = aggregation_spec.get("op", ">")
        matched = False

        if op == ">":
            matched = aggregated_value > threshold
        elif op == ">=":
            matched = aggregated_value >= threshold
        elif op == "<":
            matched = aggregated_value < threshold
        elif op == "<=":
            matched = aggregated_value <= threshold
        elif op == "==":
            matched = aggregated_value == threshold
        elif op == "!=":
            matched = aggregated_value != threshold

        return matched, {
            "aggregation_type": agg_type,
            "field": field,
            "aggregated_value": aggregated_value,
            "threshold": threshold,
            "operator": op,
            "matched": matched,
            "event_count": len(window_events),
        }
    else:
        return True, {
            "aggregation_type": agg_type,
            "field": field,
            "aggregated_value": aggregated_value,
            "event_count": len(window_events),
        }


def apply_window_aggregation(
    trigger_spec: Dict[str, Any],
    window_events: list[Dict[str, Any]],
) -> Tuple[bool, Dict[str, Any]]:
    """Apply windowing and aggregation to events."""
    aggregation_spec = trigger_spec.get("aggregation")

    if not aggregation_spec:
        return False, {"reason": "No aggregation spec provided"}

    matched, details = evaluate_aggregation(window_events, aggregation_spec)

    details["window_size"] = len(window_events)
    details["window_config"] = trigger_spec.get("window_config", {})

    return matched, details
