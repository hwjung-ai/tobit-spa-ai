from __future__ import annotations

from app.modules.simulation.schemas import SimulationScenarioType, SimulationStrategy
from app.modules.simulation.services.simulation.schemas import SimulationPlan
from app.modules.simulation.services.simulation.validators import (
    validate_assumptions,
    validate_question,
)


def plan_simulation(
    *,
    question: str,
    strategy: SimulationStrategy,
    scenario_type: SimulationScenarioType,
    assumptions: dict[str, float | int],
    horizon: str,
    service: str = "api-gateway",
) -> SimulationPlan:
    return SimulationPlan(
        scenario_name=f"{scenario_type}:{service}",
        target_entities=[service],
        assumptions=validate_assumptions(assumptions),
        horizon=horizon,
        strategy=strategy,
        scenario_type=scenario_type,
        service=service,
        question=validate_question(question),
    )
