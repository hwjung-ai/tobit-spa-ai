from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel
from schemas import AnswerEnvelope, ResponseEnvelope

OpsMode = Literal["config", "history", "relation", "metric", "all", "hist", "graph"]

from app.modules.ops.services.ci.planner.plan_schema import Plan, View

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

class CiAskResponse(BaseModel):
    answer: str
    blocks: List[Dict[str, Any]]
    trace: Dict[str, Any]
    next_actions: List[Dict[str, Any]]
    meta: Dict[str, Any] | None
