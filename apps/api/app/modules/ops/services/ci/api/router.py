from __future__ import annotations

import time
from typing import Any, Dict, List, Literal, Optional

from core.logging import get_logger
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from schemas import ResponseEnvelope

from app.modules.ops.services.ci.orchestrator.runner import (
    CIOrchestratorRunner,
    RerunContext,
)
from app.modules.ops.services.ci.planner import planner_llm, validator
from app.modules.ops.services.ci.planner.plan_schema import Plan, View

router = APIRouter(prefix="/ops/ci", tags=["ops-ci"])

logger = get_logger(__name__)


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


def _tenant_id(x_tenant_id: str | None = Header(None, alias="X-Tenant-Id")) -> str:
    return x_tenant_id or "t1"


def _apply_patch(plan: Plan, patch: Optional[RerunPatch]) -> Plan:
    if not patch:
        return plan
    updates: dict[str, Any] = {}
    if patch.view:
        updates["view"] = patch.view
    if patch.graph:
        graph_updates: dict[str, Any] = {}
        if patch.graph.depth is not None:
            graph_updates["depth"] = patch.graph.depth
        if patch.graph.limits:
            graph_updates["limits"] = patch.graph.limits
        if patch.graph.view:
            graph_updates["view"] = patch.graph.view
        updates["graph"] = plan.graph.copy(update=graph_updates)
    if patch.aggregate:
        agg_updates: dict[str, Any] = {}
        if patch.aggregate.group_by:
            agg_updates["group_by"] = patch.aggregate.group_by
        if patch.aggregate.top_n is not None:
            agg_updates["top_n"] = patch.aggregate.top_n
        updates["aggregate"] = plan.aggregate.copy(update=agg_updates)
    if patch.output:
        out_updates: dict[str, Any] = {}
        if patch.output.primary:
            out_updates["primary"] = patch.output.primary
        if patch.output.blocks:
            out_updates["blocks"] = patch.output.blocks
        updates["output"] = plan.output.copy(update=out_updates)
    if patch.metric and plan.metric:
        metric_updates: dict[str, Any] = {}
        if patch.metric.time_range:
            metric_updates["time_range"] = patch.metric.time_range
        if patch.metric.agg:
            metric_updates["agg"] = patch.metric.agg
        if patch.metric.mode:
            metric_updates["mode"] = patch.metric.mode
        if metric_updates:
            updates["metric"] = plan.metric.copy(update=metric_updates)
    if patch.history and plan.history:
        history_updates: dict[str, Any] = {}
        if patch.history.time_range:
            history_updates["time_range"] = patch.history.time_range
        if patch.history.limit is not None:
            history_updates["limit"] = patch.history.limit
        if history_updates:
            updates["history"] = plan.history.copy(update=history_updates)
    if patch.list and plan.list:
        list_updates: dict[str, Any] = {}
        if patch.list.offset is not None:
            list_updates["offset"] = patch.list.offset
        if patch.list.limit is not None:
            list_updates["limit"] = patch.list.limit
        if list_updates:
            updates["list"] = plan.list.copy(update=list_updates)
    if patch.auto:
        auto_updates: dict[str, Any] = {}
        if patch.auto.path:
            path_updates: dict[str, Any] = {}
            if patch.auto.path.source_ci_code is not None:
                path_updates["source_ci_code"] = patch.auto.path.source_ci_code
            if patch.auto.path.target_ci_code is not None:
                path_updates["target_ci_code"] = patch.auto.path.target_ci_code
            if path_updates:
                auto_updates["path"] = plan.auto.path.copy(update=path_updates)
        if patch.auto.graph_scope:
            graph_updates: dict[str, Any] = {}
            if patch.auto.graph_scope.include_metric is not None:
                graph_updates["include_metric"] = patch.auto.graph_scope.include_metric
            if patch.auto.graph_scope.include_history is not None:
                graph_updates["include_history"] = patch.auto.graph_scope.include_history
            if graph_updates:
                auto_updates["graph_scope"] = plan.auto.graph_scope.copy(update=graph_updates)
        if auto_updates:
            updates["auto"] = plan.auto.copy(update=auto_updates)
    return plan.copy(update=updates) if updates else plan


@router.post("/ask")
def ask_ci(payload: CiAskRequest, tenant_id: str = Depends(_tenant_id)):
    start = time.perf_counter()
    status = "ok"
    envelope_blocks: list[dict[str, Any]] | None = None
    next_actions_count = 0
    patched = bool(payload.rerun)
    patch_keys: list[str] = []
    has_trace_plan_validated = False
    if payload.rerun:
        has_trace_plan_validated = bool(payload.rerun.base_plan)
        if payload.rerun.patch:
            patch_keys = list(payload.rerun.patch.dict(exclude_none=True).keys())
    logger.info(
        "ci.ask.start",
        extra={
            "query_len": len(payload.question),
            "has_patch": patched,
            "patch_keys": patch_keys,
            "has_trace_plan_validated": has_trace_plan_validated,
        },
    )
    try:
        rerun_context: RerunContext | None = None
        if payload.rerun:
            logger.info("ci.runner.planner.skipped", extra={"reason": "rerun"})
            patched_plan = _apply_patch(payload.rerun.base_plan, payload.rerun.patch)
            logger.info("ci.runner.validator.start", extra={"phase": "rerun"})
            plan_validated, plan_trace = validator.validate_plan(patched_plan)
            logger.info("ci.runner.validator.done", extra={"phase": "rerun"})
            plan_raw = payload.rerun.base_plan
            rerun_context = RerunContext(
                selected_ci_id=payload.rerun.selected_ci_id,
                selected_secondary_ci_id=payload.rerun.selected_secondary_ci_id,
            )
        else:
            planner_start = time.perf_counter()
            logger.info("ci.runner.planner.start", extra={"llm_called": False})
            plan_raw = planner_llm.create_plan(payload.question)
            elapsed_ms = int((time.perf_counter() - planner_start) * 1000)
            logger.info("ci.runner.planner.done", extra={"llm_called": False, "elapsed_ms": elapsed_ms})
            logger.info("ci.runner.validator.start", extra={"phase": "initial"})
            plan_validated, plan_trace = validator.validate_plan(plan_raw)
            logger.info("ci.runner.validator.done", extra={"phase": "initial"})
        runner = CIOrchestratorRunner(
            plan_validated,
            plan_raw,
            tenant_id,
            payload.question,
            plan_trace,
            rerun_context=rerun_context,
        )
        result = runner.run()
        next_actions = result.get("next_actions") or []
        next_actions_count = len(next_actions)
        envelope_blocks = result.get("blocks") or []
        response: CiAskResponse = CiAskResponse(**result)
        return ResponseEnvelope.success(data=response.dict())
    except Exception as exc:  # pragma: no cover - surface run-time failures
        status = "error"
        logger.exception("ci.ask.error", exc_info=exc)
        error_body = ResponseEnvelope.error(message=str(exc)).model_dump(mode="json")
        return JSONResponse(status_code=500, content=error_body)
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        block_types: list[str] = []
        if envelope_blocks:
            for block in envelope_blocks:
                if isinstance(block, dict):
                    block_type = block.get("type")
                else:
                    block_type = getattr(block, "type", None)
                if block_type:
                    block_types.append(block_type)
        logger.info(
            "ci.ask.done",
            extra={
                "status": status,
                "elapsed_ms": elapsed_ms,
                "blocks_count": len(envelope_blocks or []),
                "block_types": block_types,
                "next_actions_count": next_actions_count,
                "has_patch": patched,
                "has_trace_plan_validated": has_trace_plan_validated,
            },
        )
