"""Anomaly detection and baseline calculation for CEP Builder."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from fastapi import HTTPException

from .metric_executor import fetch_runtime_value
from .rule_executor import get_path_value


def _evaluate_anomaly_trigger(
    trigger_spec: Dict[str, Any],
    payload: Dict[str, Any] | None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluate anomaly detection trigger.

    trigger_spec should contain:
    {
        "anomaly_method": "zscore" | "iqr" | "ema",
        "anomaly_config": { ... method-specific config ... },
        "baseline_values": [1.0, 2.0, ...],
        "value_path": "metrics.cpu_usage",
        "endpoint": "/runtime/...",  # optional: fetch from runtime
        "source": "runtime" | "payload"
    }
    """
    from ..anomaly_detector import detect_anomaly

    spec = trigger_spec
    references: Dict[str, Any] = {"trigger_spec": spec}

    method = spec.get("anomaly_method", "zscore")
    config = spec.get("anomaly_config", {})
    baseline_values = spec.get("baseline_values", [])
    value_path = spec.get("value_path")

    if not value_path:
        raise HTTPException(
            status_code=400, detail="Anomaly trigger requires value_path"
        )

    # Get current value from payload or runtime
    source = spec.get("source", "payload")
    if source == "runtime" and payload is None:
        _, extracted_value = fetch_runtime_value(spec)
    else:
        extracted_value = get_path_value(payload or {}, value_path)

    references["extracted_value"] = extracted_value

    if extracted_value is None:
        references["condition_evaluated"] = False
        references["error_reason"] = "value_path did not resolve"
        return False, references

    try:
        current_value = float(extracted_value)
    except (TypeError, ValueError):
        references["condition_evaluated"] = False
        references["error_reason"] = "extracted value is not numeric"
        return False, references

    # Convert baseline values to floats
    numeric_baseline: list[float] = []
    for v in baseline_values:
        try:
            numeric_baseline.append(float(v))
        except (TypeError, ValueError):
            continue

    result = detect_anomaly(
        values=numeric_baseline,
        current=current_value,
        method=method,
        config=config,
    )

    references["condition_evaluated"] = True
    references["anomaly_result"] = {
        "is_anomaly": result.is_anomaly,
        "score": result.score,
        "method": result.method,
        "details": result.details,
    }

    return result.is_anomaly, references
