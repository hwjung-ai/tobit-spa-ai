from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

SimulationStrategy = Literal["rule", "stat", "ml", "dl", "custom"]
SimulationScenarioType = Literal["what_if", "stress_test", "capacity"]


class SimulationCustomFunctionSpec(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    function_name: str = Field(default="simulate", min_length=1, max_length=120)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    code: str = Field(min_length=1, max_length=40000)
    runtime_policy: dict[str, Any] = Field(default_factory=dict)


class SimulationRunRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    scenario_type: SimulationScenarioType = "what_if"
    strategy: SimulationStrategy = "rule"
    assumptions: dict[str, float | int] = Field(default_factory=dict)
    horizon: str = "7d"
    service: str = "api-gateway"
    custom_input: dict[str, Any] = Field(default_factory=dict)
    custom_function: SimulationCustomFunctionSpec | None = None


class SimulationRealtimeSourceConfig(BaseModel):
    source: Literal["prometheus", "cloudwatch"] = "prometheus"
    prometheus_url: str | None = None
    cloudwatch_region: str | None = None
    query: str | dict[str, Any] | None = None


class SimulationRealtimeRunRequest(SimulationRunRequest):
    source_config: SimulationRealtimeSourceConfig


class SimulationQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    scenario_type: SimulationScenarioType = "what_if"
    strategy: SimulationStrategy = "rule"
    assumptions: dict[str, float | int] = Field(default_factory=dict)
    horizon: str = "7d"
    service: str = "api-gateway"
    custom_input: dict[str, Any] = Field(default_factory=dict)
    custom_function: SimulationCustomFunctionSpec | None = None


class KpiResult(BaseModel):
    kpi: str
    baseline: float
    simulated: float
    unit: str

    @property
    def change_pct(self) -> float:
        if self.baseline == 0:
            return 0.0
        return round(((self.simulated - self.baseline) / self.baseline) * 100.0, 2)


class SimulationResult(BaseModel):
    scenario_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy: SimulationStrategy
    scenario_type: SimulationScenarioType
    question: str
    horizon: str
    assumptions: dict[str, float | int] = Field(default_factory=dict)
    kpis: list[KpiResult]
    confidence: float
    confidence_interval: tuple[float, float] | None = None
    error_bound: float | None = None
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    recommended_actions: list[str] = Field(default_factory=list)
    model_info: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SimulationTemplate(BaseModel):
    id: str
    name: str
    description: str
    scenario_type: SimulationScenarioType
    default_strategy: SimulationStrategy
    assumptions: dict[str, float | int]
    question_example: str


class SimulationBacktestRequest(BaseModel):
    strategy: SimulationStrategy
    service: str = "api-gateway"
    horizon: str = "30d"
    assumptions: dict[str, float | int] = Field(default_factory=dict)


class SimulationFunctionValidateRequest(BaseModel):
    function: SimulationCustomFunctionSpec
    sample_params: dict[str, Any] = Field(default_factory=dict)
    sample_input: dict[str, Any] = Field(default_factory=dict)


class SimulationFunctionExecuteRequest(BaseModel):
    function: SimulationCustomFunctionSpec
    params: dict[str, Any] = Field(default_factory=dict)
    input_payload: dict[str, Any] = Field(default_factory=dict)
