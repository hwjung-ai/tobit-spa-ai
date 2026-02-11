from __future__ import annotations

from typing import Any

_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "ml": {
        "model_name": "sim-surrogate-v1",
        "model_type": "ensemble_surrogate",
        "version": "ml-v1",
        "features": ["traffic_change_pct", "cpu_change_pct", "memory_change_pct"],
    },
    "dl": {
        "model_name": "sim-lstm-surrogate-v1",
        "model_type": "lstm_surrogate",
        "version": "dl-v1",
        "features": ["traffic_change_pct", "cpu_change_pct", "memory_change_pct", "horizon"],
    },
}


def get_model_metadata(strategy: str) -> dict[str, Any]:
    return dict(_MODEL_REGISTRY.get(strategy, {}))
