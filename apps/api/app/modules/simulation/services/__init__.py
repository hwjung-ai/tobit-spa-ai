from __future__ import annotations

from typing import Any

from app.modules.simulation.schemas import SimulationRunRequest
from app.modules.simulation.services.simulation.scenario_templates import get_templates
from app.modules.simulation.services.simulation.simulation_executor import (
    run_simulation as _run_simulation,
)


def run_simulation(payload: SimulationRunRequest) -> dict[str, Any]:
    return _run_simulation(payload=payload, tenant_id="unknown", requested_by="unknown")


__all__ = ["get_templates", "run_simulation"]
