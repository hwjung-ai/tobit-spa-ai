from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field

from app.modules.simulation.schemas import SimulationScenarioType, SimulationStrategy


class SimulationPlan(BaseModel):
    scenario_id: str = Field(default_factory=lambda: str(uuid4()))
    scenario_name: str
    target_entities: list[str] = Field(default_factory=list)
    target_kpis: list[str] = Field(default_factory=lambda: ["latency_ms", "error_rate_pct", "throughput_rps", "cost_usd_hour"])
    assumptions: dict[str, float] = Field(default_factory=dict)
    baseline_window: str = "last_30d"
    horizon: str = "7d"
    strategy: SimulationStrategy = "rule"
    scenario_type: SimulationScenarioType = "what_if"
    service: str = "api-gateway"
    question: str


class KpiResult(BaseModel):
    kpi: str
    baseline: float
    simulated: float
    unit: str

    @computed_field
    @property
    def change_pct(self) -> float:
        if self.baseline == 0:
            return 0.0
        return round(((self.simulated - self.baseline) / self.baseline) * 100.0, 2)


class SimulationResult(BaseModel):
    scenario_id: str
    strategy: SimulationStrategy
    scenario_type: SimulationScenarioType
    question: str
    horizon: str
    assumptions: dict[str, float] = Field(default_factory=dict)
    kpis: list[KpiResult]
    confidence: float
    confidence_interval: tuple[float, float] | None = None
    error_bound: float | None = None
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    recommended_actions: list[str] = Field(default_factory=list)
    model_info: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
