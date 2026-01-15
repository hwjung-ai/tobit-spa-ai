from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


class Intent(str, Enum):
    LOOKUP = "LOOKUP"
    SEARCH = "SEARCH"
    LIST = "LIST"
    AGGREGATE = "AGGREGATE"
    EXPAND = "EXPAND"
    PATH = "PATH"


class View(str, Enum):
    SUMMARY = "SUMMARY"
    COMPOSITION = "COMPOSITION"
    DEPENDENCY = "DEPENDENCY"
    IMPACT = "IMPACT"
    PATH = "PATH"
    NEIGHBORS = "NEIGHBORS"


class FilterSpec(BaseModel):
    field: str
    op: Literal["=", "!=", "ILIKE"] = "="
    value: str


class PrimarySpec(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    filters: List[FilterSpec] = Field(default_factory=list)
    limit: int = 5


class SecondarySpec(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    filters: List[FilterSpec] = Field(default_factory=list)
    limit: int = 5


class AggregateSpec(BaseModel):
    group_by: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    filters: List[FilterSpec] = Field(default_factory=list)
    scope: Literal["ci", "graph"] = "ci"
    top_n: int = 10


class GraphLimits(BaseModel):
    max_nodes: int = 200
    max_edges: int = 400
    max_paths: int = 25


class GraphSpec(BaseModel):
    depth: int = 2
    limits: GraphLimits = Field(default_factory=GraphLimits)
    view: View | None = None


class OutputSpec(BaseModel):
    blocks: List[str] = Field(default_factory=lambda: ["text", "table"])
    primary: Literal["text", "table", "network", "path", "number", "markdown", "chart"] = "table"


class MetricSpec(BaseModel):
    metric_name: str
    agg: Literal["count", "max", "min", "avg"]
    time_range: str
    mode: Literal["aggregate", "series"] = "aggregate"
    scope: Literal["ci", "graph"] = "ci"


class HistorySpec(BaseModel):
    enabled: bool = False
    source: Literal["event_log"] = "event_log"
    scope: Literal["ci", "graph"] = "ci"
    mode: Literal["recent"] = "recent"
    time_range: Literal["last_24h", "last_7d", "last_30d"] = "last_7d"
    limit: int = 50


class ListSpec(BaseModel):
    enabled: bool = False
    limit: int = 50
    offset: int = 0


class CepSpec(BaseModel):
    mode: Literal["simulate"] = "simulate"
    rule_id: str | None = None
    dry_run: bool = True


class AutoPathSpec(BaseModel):
    source_ci_code: str | None = None
    target_ci_code: str | None = None


class AutoGraphScopeSpec(BaseModel):
    include_metric: bool = False
    include_history: bool = False


class AutoSpec(BaseModel):
    views: List[View] = Field(default_factory=lambda: [View.NEIGHBORS])
    depth_hint: int | None = None
    include_metric: bool = False
    metric_mode: Literal["aggregate", "series"] = "aggregate"
    include_history: bool = False
    include_cep: bool = False
    path: AutoPathSpec = Field(default_factory=AutoPathSpec)
    graph_scope: AutoGraphScopeSpec = Field(default_factory=AutoGraphScopeSpec)

class PlanMode(str, Enum):
    CI = "ci"
    AUTO = "auto"


class BudgetSpec(BaseModel):
    """Budget constraints for plan execution"""
    max_steps: int = 10
    max_depth: int = 5
    max_branches: int = 3
    max_iterations: int = 100
    timeout_seconds: int | None = None


class StepCondition(BaseModel):
    """Condition to determine step execution or branching"""
    field: str
    operator: Literal["==", "!=", "<", ">", "<=", ">=", "contains", "matches"]
    value: str | int | float | bool


class PlanStep(BaseModel):
    """Individual step in a multi-step plan"""
    step_id: str
    name: str
    description: str | None = None
    intent: Intent
    view: View | None = None
    mode: PlanMode = PlanMode.CI
    primary: PrimarySpec = Field(default_factory=PrimarySpec)
    secondary: SecondarySpec = Field(default_factory=SecondarySpec)
    aggregate: AggregateSpec = Field(default_factory=AggregateSpec)
    graph: GraphSpec = Field(default_factory=GraphSpec)
    output: OutputSpec = Field(default_factory=OutputSpec)
    metric: MetricSpec | None = None
    history: HistorySpec = Field(default_factory=lambda: HistorySpec())
    cep: CepSpec | None = None
    auto: AutoSpec = Field(default_factory=AutoSpec)
    list: ListSpec = Field(default_factory=ListSpec)
    condition: StepCondition | None = None
    next_step_id: str | None = None
    error_next_step_id: str | None = None


class PlanBranch(BaseModel):
    """Conditional branch in a plan"""
    branch_id: str
    name: str
    condition: StepCondition
    steps: List[PlanStep] = Field(default_factory=list)
    merge_step_id: str | None = None


class PlanLoop(BaseModel):
    """Loop construct in a plan"""
    loop_id: str
    name: str
    max_iterations: int = 10
    break_condition: StepCondition | None = None
    steps: List[PlanStep] = Field(default_factory=list)
    next_step_id: str | None = None


class Plan(BaseModel):
    intent: Intent = Intent.LOOKUP
    view: View | None = View.SUMMARY
    mode: PlanMode = PlanMode.CI
    primary: PrimarySpec = Field(default_factory=PrimarySpec)
    secondary: SecondarySpec = Field(default_factory=SecondarySpec)
    aggregate: AggregateSpec = Field(default_factory=AggregateSpec)
    graph: GraphSpec = Field(default_factory=GraphSpec)
    output: OutputSpec = Field(default_factory=OutputSpec)
    metric: MetricSpec | None = None
    history: HistorySpec = Field(default_factory=lambda: HistorySpec())
    cep: CepSpec | None = None
    auto: AutoSpec = Field(default_factory=AutoSpec)
    list: ListSpec = Field(default_factory=ListSpec)
    normalized_from: str | None = None
    normalized_to: str | None = None
    # Multi-step execution support
    steps: List[PlanStep] = Field(default_factory=list)
    branches: List[PlanBranch] = Field(default_factory=list)
    loops: List[PlanLoop] = Field(default_factory=list)
    budget: BudgetSpec = Field(default_factory=BudgetSpec)
    enable_multistep: bool = False

    @validator("view", pre=True, always=True)
    def normalize_view(cls, value: View | str | None) -> View | None:
        if isinstance(value, str):
            return View(value.upper())
        return value

    @validator("mode", pre=True, always=True)
    def normalize_mode(cls, value: PlanMode | str | None) -> PlanMode:
        if isinstance(value, PlanMode):
            return value
        if isinstance(value, str):
            try:
                return PlanMode(value.lower())
            except ValueError:
                pass
        return PlanMode.CI
