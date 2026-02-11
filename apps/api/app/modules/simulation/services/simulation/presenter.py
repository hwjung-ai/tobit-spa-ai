from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from schemas import (
    MarkdownBlock,
    ReferenceItem,
    ReferencesBlock,
    TableBlock,
    TimeSeriesBlock,
    TimeSeriesPoint,
    TimeSeriesSeries,
)

from app.modules.simulation.services.simulation.schemas import (
    SimulationPlan,
    SimulationResult,
)


def build_blocks(*, plan: SimulationPlan, result: SimulationResult, baseline_data: dict[str, float]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    baseline_time = (now - timedelta(days=1)).isoformat()
    scenario_time = now.isoformat()

    table_rows = [
        [k.kpi, f"{k.baseline:.3f}", f"{k.simulated:.3f}", f"{k.change_pct:+.2f}%", k.unit]
        for k in result.kpis
    ]

    blocks = [
        MarkdownBlock(
            type="markdown",
            title="SIM Summary",
            content=(
                f"Strategy: **{result.strategy.upper()}**  \n"
                f"Scenario: **{result.scenario_type}**  \n"
                f"Service: **{plan.service}**  \n"
                f"Baseline Window: **{plan.baseline_window}**  \n"
                f"Horizon: **{result.horizon}**  \n"
                f"Confidence: **{result.confidence:.2f}**"
            ),
        ),
        TableBlock(
            type="table",
            title="KPI Comparison",
            columns=["kpi", "baseline", "simulated", "change_pct", "unit"],
            rows=table_rows,
        ),
        TimeSeriesBlock(
            type="timeseries",
            title="Latency Baseline vs Simulated",
            series=[
                TimeSeriesSeries(
                    name="baseline",
                    data=[TimeSeriesPoint(timestamp=baseline_time, value=baseline_data["latency_ms"])],
                ),
                TimeSeriesSeries(
                    name="simulated",
                    data=[TimeSeriesPoint(timestamp=scenario_time, value=next(k.simulated for k in result.kpis if k.kpi == "latency_ms"))],
                ),
            ],
        ),
        ReferencesBlock(
            type="references",
            title="Simulation Evidence",
            items=[
                ReferenceItem(kind="row", title="assumptions", payload=result.assumptions),
                ReferenceItem(kind="row", title="model_info", payload=result.model_info),
                ReferenceItem(
                    kind="row",
                    title="baseline_data",
                    payload={"window": plan.baseline_window, "service": plan.service, "kpis": baseline_data},
                ),
            ],
        ),
    ]
    return [b.model_dump() for b in blocks]


def build_references(*, plan: SimulationPlan, result: SimulationResult, baseline_data: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"kind": "row", "title": "assumptions", "payload": result.assumptions},
        {"kind": "row", "title": "model_info", "payload": result.model_info},
        {"kind": "row", "title": "baseline_data", "payload": {"window": plan.baseline_window, "service": plan.service, "kpis": baseline_data}},
    ]
