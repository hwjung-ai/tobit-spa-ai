from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PlanOutputKind(str, Enum):
    DIRECT = "direct"
    PLAN = "plan"
    REJECT = "reject"


class DirectAnswerPayload(BaseModel):
    """Payload for direct answer response"""

    answer: str
    confidence: float = 1.0
    reasoning: Optional[str] = None
    references: List[Dict[str, Any]] = Field(default_factory=list)


class RejectPayload(BaseModel):
    """Payload for reject response"""

    reason: str
    policy: Optional[str] = None
    confidence: float = 1.0
    reasoning: Optional[str] = None


class Intent(str, Enum):
    LOOKUP = "LOOKUP"
    SEARCH = "SEARCH"
    LIST = "LIST"
    AGGREGATE = "AGGREGATE"
    EXPAND = "EXPAND"
    PATH = "PATH"
    DOCUMENT = "DOCUMENT"


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
    keywords: List[str] = Field(default_factory=lambda: [])
    filters: List[FilterSpec] = Field(default_factory=lambda: [])
    limit: int = 5
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for primary query execution"
    )


class SecondarySpec(BaseModel):
    keywords: List[str] = Field(default_factory=lambda: [])
    filters: List[FilterSpec] = Field(default_factory=lambda: [])
    limit: int = 5
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for secondary query execution"
    )


class AggregateSpec(BaseModel):
    group_by: List[str] = Field(default_factory=lambda: [])
    metrics: List[str] = Field(default_factory=lambda: [])
    filters: List[FilterSpec] = Field(default_factory=lambda: [])
    scope: Literal["s1", "ci", "graph", "event"] = "s1"
    top_n: int = 10
    tool_type: str = Field(
        default="ci_aggregate",
        description="Tool to use for aggregate query execution"
    )


class GraphLimits(BaseModel):
    max_nodes: int = 200
    max_edges: int = 400
    max_paths: int = 25


class GraphSpec(BaseModel):
    depth: int = 2
    user_requested_depth: int | None = None  # 사용자가 질의에서 명시한 depth
    limits: GraphLimits = Field(default_factory=lambda: GraphLimits())
    view: View | None = None
    tool_type: str = Field(
        default="ci_graph",
        description="Tool to use for graph analysis execution"
    )


class OutputSpec(BaseModel):
    blocks: List[str] = Field(default_factory=lambda: ["text", "table"])
    primary: Literal[
        "text", "table", "network", "path", "number", "markdown", "chart"
    ] = "table"


class MetricSpec(BaseModel):
    metric_name: str
    agg: Literal["count", "max", "min", "avg"]
    time_range: str
    mode: Literal["aggregate", "series"] = "aggregate"
    scope: Literal["s1", "ci", "graph"] = "s1"
    tool_type: str = Field(
        default="metric",
        description="Tool to use for metric query execution"
    )


class HistorySpec(BaseModel):
    enabled: bool = False
    source: Literal["event_log", "work_history", "maintenance_history", "work_and_maintenance"] = "work_and_maintenance"
    scope: Literal["s1", "ci", "graph"] = "s1"
    mode: Literal["recent"] = "recent"
    time_range: Literal["last_24h", "last_7d", "last_30d", "all_time"] = "last_7d"
    limit: int = 50
    tool_type: str = Field(
        default="history",
        description="Tool to use for history query execution"
    )


class ListSpec(BaseModel):
    enabled: bool = False
    limit: int = 50
    offset: int = 0


class CepSpec(BaseModel):
    mode: Literal["simulate"] = "simulate"
    rule_id: str | None = None
    dry_run: bool = True
    tool_type: str = Field(
        default="cep_query",
        description="Tool to use for CEP query execution"
    )


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
    path: AutoPathSpec = Field(default_factory=lambda: AutoPathSpec())
    graph_scope: AutoGraphScopeSpec = Field(
        default_factory=lambda: AutoGraphScopeSpec()
    )
    tool_type: str = Field(
        default="auto_analyzer",
        description="Tool to use for auto analysis execution"
    )


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


# NEW: Orchestration support classes
class ExecutionStrategy(str, Enum):
    """Execution strategy for orchestration"""
    SERIAL = "serial"      # Execute tools sequentially
    PARALLEL = "parallel"  # Execute independent tools in parallel
    DAG = "dag"            # Execute based on dependency graph


class ToolDependency(BaseModel):
    """Tool dependency specification for orchestration"""
    tool_id: str
    depends_on: List[str] = Field(default_factory=list)
    output_mapping: Dict[str, str] = Field(default_factory=dict)
    condition: Optional[str] = None


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
    primary: PrimarySpec = Field(default_factory=lambda: PrimarySpec())
    secondary: SecondarySpec = Field(default_factory=lambda: SecondarySpec())
    aggregate: AggregateSpec = Field(default_factory=lambda: AggregateSpec())
    graph: GraphSpec = Field(default_factory=lambda: GraphSpec())
    output: OutputSpec = Field(default_factory=lambda: OutputSpec())
    metric: MetricSpec | None = None
    history: HistorySpec = Field(default_factory=lambda: HistorySpec())
    cep: CepSpec | None = None
    auto: AutoSpec = Field(default_factory=lambda: AutoSpec())
    list: ListSpec = Field(default_factory=lambda: ListSpec())
    condition: StepCondition | None = None
    next_step_id: str | None = None
    error_next_step_id: str | None = None


class PlanBranch(BaseModel):
    """Conditional branch in a plan"""

    branch_id: str
    name: str
    condition: StepCondition
    steps: List[PlanStep] = Field(default_factory=lambda: [])
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
    primary: PrimarySpec = Field(default_factory=lambda: PrimarySpec())
    secondary: SecondarySpec = Field(default_factory=lambda: SecondarySpec())
    aggregate: AggregateSpec = Field(default_factory=lambda: AggregateSpec())
    graph: GraphSpec = Field(default_factory=lambda: GraphSpec())
    output: OutputSpec = Field(default_factory=lambda: OutputSpec())
    metric: MetricSpec | None = None
    history: HistorySpec = Field(default_factory=lambda: HistorySpec())
    cep: CepSpec | None = None
    auto: AutoSpec = Field(default_factory=lambda: AutoSpec())
    list: ListSpec = Field(default_factory=lambda: ListSpec())
    document: Dict[str, Any] | None = Field(
        default=None,
        description="Document search specification (query, search_type, top_k, min_relevance, tool_type)"
    )
    normalized_from: str | None = None
    normalized_to: str | None = None
    # Multi-step execution support
    steps: List[PlanStep] = Field(default_factory=lambda: [])
    branches: List[PlanBranch] = Field(default_factory=lambda: [])
    loops: List[PlanLoop] = Field(default_factory=lambda: [])
    budget: BudgetSpec = Field(default_factory=lambda: BudgetSpec())
    enable_multistep: bool = False
    # NEW: Orchestration fields
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SERIAL
    tool_dependencies: List[ToolDependency] = []
    enable_intermediate_llm: bool = False
    # Mode hint for tool selection filtering
    mode_hint: str | None = Field(
        default=None,
        description="Mode hint to guide tool selection (config, metric, graph, history, document, all)"
    )

    @field_validator("view", mode="before")
    @classmethod
    def normalize_view(cls, value: Any) -> View | None:
        if isinstance(value, str):
            return View(value.upper())
        return value

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, value: Any) -> PlanMode:
        if isinstance(value, PlanMode):
            return value
        if isinstance(value, str):
            try:
                return PlanMode(value.lower())
            except ValueError:
                pass
        return PlanMode.CI


class PlanOutput(BaseModel):
    """Unified output for planner with three possible kinds"""

    kind: PlanOutputKind
    # kind=direct일 때
    direct_answer: Optional[DirectAnswerPayload] = None
    # kind=plan일 때
    plan: Optional[Plan] = None
    # kind=reject일 때
    reject_payload: Optional[RejectPayload] = None
    # 공통
    confidence: float = 1.0
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
