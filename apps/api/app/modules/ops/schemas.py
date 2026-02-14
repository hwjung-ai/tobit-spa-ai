from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

OpsMode = Literal["config", "history", "relation", "metric", "all", "hist", "graph", "document"]

from app.modules.ops.services.orchestration.planner.plan_schema import Plan, View


class OpsQueryRequest(BaseModel):
    mode: OpsMode
    question: str


# CI Rerun schemas
# View is imported from plan_schema


class RerunGraphPatch(BaseModel):
    depth: int | None = None
    limits: Dict[str, int] | None = None
    view: View | None = None


class RerunAggregatePatch(BaseModel):
    group_by: List[str] | None = None
    top_n: int | None = None


class RerunOutputPatch(BaseModel):
    primary: str | None = None
    blocks: List[str] | None = None


class RerunMetricPatch(BaseModel):
    time_range: str | None = None
    agg: Literal["count", "max", "min", "avg"] | None = None
    mode: Literal["aggregate", "series"] | None = None


class RerunHistoryPatch(BaseModel):
    time_range: Literal["last_24h", "last_7d", "last_30d"] | None = None
    limit: int | None = None


class RerunListPatch(BaseModel):
    offset: int | None = None
    limit: int | None = None


class RerunAutoPathPatch(BaseModel):
    source_ci_code: str | None = None
    target_ci_code: str | None = None


class RerunAutoGraphScopePatch(BaseModel):
    include_metric: bool | None = None
    include_history: bool | None = None


class RerunAutoPatch(BaseModel):
    path: RerunAutoPathPatch | None = None
    graph_scope: RerunAutoGraphScopePatch | None = None


class RerunPatch(BaseModel):
    view: View | None = None
    graph: RerunGraphPatch | None = None
    aggregate: RerunAggregatePatch | None = None
    output: RerunOutputPatch | None = None
    metric: RerunMetricPatch | None = None
    history: RerunHistoryPatch | None = None
    auto: RerunAutoPatch | None = None
    list: RerunListPatch | None = None


class RerunContext(BaseModel):
    selected_ci_id: str | None = None
    selected_secondary_ci_id: str | None = None


class RerunRequest(BaseModel):
    base_plan: Plan
    selected_ci_id: str | None = None
    selected_secondary_ci_id: str | None = None
    patch: RerunPatch | None = None


class CiAskRequest(BaseModel):
    question: str
    rerun: RerunRequest | None = None
    asset_overrides: Dict[str, str] | None = None
    source_asset: str | None = None
    schema_asset: str | None = None
    resolver_asset: str | None = None


class CiAskResponse(BaseModel):
    answer: str
    blocks: List[Dict[str, Any]]
    trace: Dict[str, Any]
    next_actions: List[Dict[str, Any]]
    meta: Dict[str, Any] | None


# UI Actions schemas
class UIActionRequest(BaseModel):
    """Request for UI action execution"""

    trace_id: str | None = None
    action_id: str
    inputs: Dict[str, Any] = {}
    context: Dict[str, Any] = {}


class UIActionResponse(BaseModel):
    """Response from UI action execution"""

    trace_id: str
    status: Literal["ok", "error"]
    blocks: List[Dict[str, Any]] = []
    references: List[Dict[str, Any]] = []
    state_patch: Dict[str, Any] | None = None
    error: Dict[str, Any] | None = None


class UIEditorPresenceHeartbeatRequest(BaseModel):
    """Heartbeat payload for UI screen editor presence tracking."""

    screen_id: str
    session_id: str
    tab_name: str | None = None


# Regression Watch schemas
class GoldenQueryCreate(BaseModel):
    """Create a new golden query"""

    name: str
    query_text: str
    ops_type: OpsMode
    options: Dict[str, Any] | None = None


class GoldenQueryRead(BaseModel):
    """Golden query read response"""

    id: str
    name: str
    query_text: str
    ops_type: OpsMode
    options: Dict[str, Any] | None
    enabled: bool
    created_at: str


class GoldenQueryUpdate(BaseModel):
    """Update golden query"""

    name: str | None = None
    query_text: str | None = None
    enabled: bool | None = None
    options: Dict[str, Any] | None = None


class RegressionBaseline(BaseModel):
    """Regression baseline info"""

    id: str
    golden_query_id: str
    baseline_trace_id: str
    baseline_status: str
    asset_versions: List[str] | None
    created_by: str | None
    created_at: str


class RegressionRunRequest(BaseModel):
    """Request to run regression check"""

    golden_query_id: str
    trigger_by: Literal["manual", "asset_change", "schedule"] = "manual"
    trigger_info: Dict[str, Any] | None = None


class RegressionRunResult(BaseModel):
    """Regression run result"""

    id: str
    golden_query_id: str
    baseline_id: str
    candidate_trace_id: str
    baseline_trace_id: str
    judgment: Literal["PASS", "WARN", "FAIL"]
    verdict_reason: str | None
    diff_summary: Dict[str, Any] | None
    triggered_by: str
    execution_duration_ms: int | None
    created_at: str


# Stage schemas for orchestration
class StageInput(BaseModel):
    """Input for a stage in the orchestration pipeline"""

    stage: str  # "route_plan" | "validate" | "execute" | "compose" | "present"
    applied_assets: Dict[str, str]  # asset_type -> asset_id:version
    params: Dict[str, Any]
    prev_output: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


class StageDiagnostics(BaseModel):
    """Diagnostics information for stage execution"""

    status: str  # "ok" | "warning" | "error"
    warnings: List[str] = []
    errors: List[str] = []
    empty_flags: Dict[str, bool] = {}  # e.g., {"result_empty": True}
    counts: Dict[str, int] = {}  # e.g., {"rows": 0, "references": 5}


class StageOutput(BaseModel):
    """Output from a stage in the orchestration pipeline"""

    stage: str
    result: Dict[str, Any]
    diagnostics: StageDiagnostics
    references: List[Dict[str, Any]]
    duration_ms: int


# ReplanEvent schemas for orchestration
class ReplanPatchDiff(BaseModel):
    """Patch diff for replan events (P0-2)"""

    before: Dict[str, Any]
    after: Dict[str, Any]


class ReplanTrigger(BaseModel):
    """Replan trigger information with safe parsing (P0-1)"""

    trigger_type: str  # e.g., "manual", "error", "timeout", "policy_violation"
    stage_name: str  # e.g., "validate", "execute", "compose"
    severity: str = "low"  # "low", "medium", "high", "critical"
    reason: str
    timestamp: str
    metadata: Dict[str, Any] | None = None


def safe_parse_trigger(trigger_str: str) -> ReplanTrigger:
    """Safely parse trigger string to ReplanTrigger (P0-1)"""
    if not trigger_str:
        raise ValueError("Trigger string cannot be empty")

    # Try to parse as JSON first
    try:
        import json

        data = json.loads(trigger_str)
        return ReplanTrigger(**data)
    except (json.JSONDecodeError, TypeError):
        # If not JSON, parse as simple string format
        parts = trigger_str.split(maxsplit=2)
        if len(parts) >= 2:
            return ReplanTrigger(
                trigger_type=parts[0],
                stage_name=parts[1],
                reason=parts[2] if len(parts) > 2 else "Unknown",
                timestamp="now",
            )
        else:
            raise ValueError(f"Invalid trigger format: {trigger_str}")


class ReplanEvent(BaseModel):
    """Replan event for orchestration control loop (P0-2)"""

    event_type: str  # "replan_request", "replan_decision", "replan_execution"
    stage_name: str  # Internal/API/Trace: snake_case (P0-3)
    trigger: ReplanTrigger  # P0-1: Use safe_parse_trigger
    patch: ReplanPatchDiff  # P0-2: before/after structure
    timestamp: str
    decision_metadata: Dict[str, Any] | None = None
    execution_metadata: Dict[str, Any] | None = None


class ExecutionContext(BaseModel):
    """Execution context for orchestration pipeline with asset override support"""

    # Required fields
    tenant_id: str
    question: str
    trace_id: str

    # Optional user information
    user_id: Optional[str] = None

    # Test and rerun context
    rerun_context: Optional[Dict[str, Any]] = None
    test_mode: bool = False
    asset_overrides: Dict[str, str] = {}  # asset_type:asset_id mapping for overrides

    # Baseline comparison for testing
    baseline_trace_id: Optional[str] = None

    # Cumulative data across stages
    final_attributions: List[Dict[str, Any]] = []
    action_cards: List[Dict[str, Any]] = []

    # Cache information
    cache_hit: bool = False
    cache_key: Optional[str] = None


# Isolated Stage Test schemas
class IsolatedStageTestRequest(BaseModel):
    """Request for isolated stage testing"""

    stage: str  # "route_plan", "validate", "execute", "compose", "present"
    question: str
    tenant_id: str
    asset_overrides: Dict[str, str] = {}  # asset_type:asset_id mapping
    baseline_trace_id: Optional[str] = None
    test_plan: Optional[Dict[str, Any]] = None  # Pre-defined plan for testing


class StageTestResponse(BaseModel):
    """Response from isolated stage test"""

    stage: str
    result: Dict[str, Any]
    duration_ms: int
    references: List[Dict[str, Any]]
    asset_overrides_used: Dict[str, str]
    baseline_trace_id: Optional[str] = None
