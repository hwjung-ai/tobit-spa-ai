from __future__ import annotations

from typing import Any


def get_published_rule(service: str) -> dict[str, Any]:
    # Phase 1 rule registry: deterministic in-code catalog.
    return {
        "rule_id": "sim_rule_cpu_latency_v1",
        "name": f"{service} CPU/Traffic to KPI rule",
        "version": 1,
        "status": "published",
        "inputs": ["traffic_change_pct", "cpu_change_pct", "memory_change_pct"],
        "output": ["latency_ms", "error_rate_pct", "throughput_rps", "cost_usd_hour"],
        "formula": "impact=0.6*traffic+0.3*cpu+0.2*memory",
        "constraints": {
            "traffic_change_pct": {"min": -90, "max": 300},
            "cpu_change_pct": {"min": -90, "max": 300},
            "memory_change_pct": {"min": -90, "max": 300},
        },
    }
