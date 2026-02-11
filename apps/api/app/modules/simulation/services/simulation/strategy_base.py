from __future__ import annotations

from typing import Any, Protocol

from app.modules.simulation.services.simulation.schemas import (
    KpiResult,
    SimulationPlan,
)


class SimulationStrategyExecutor(Protocol):
    name: str

    def run(self, *, plan: SimulationPlan, baseline_data: dict[str, float], tenant_id: str) -> tuple[list[KpiResult], float, dict[str, Any]]:
        ...
