from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

import importlib
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.db import get_session
from core.logging import get_logger, get_request_context
from schemas import ResponseEnvelope
from sqlmodel import Session

from .schemas import (
    CiAskRequest,
    CiAskResponse,
    OpsQueryRequest,
    RerunContext,
    RerunRequest,
    RerunPatch,
    UIActionRequest,
    UIActionResponse,
)
from .services import handle_ops_query
from .services.ci.orchestrator.runner import CIOrchestratorRunner
from .services.ci.planner import planner_llm, validator
from .services.ci.planner.plan_schema import Plan
from app.modules.inspector.service import persist_execution_trace
from app.modules.inspector.span_tracker import (
    start_span,
    end_span,
    get_all_spans,
    clear_spans,
)
from .services.observability_service import collect_observability_metrics

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)

# --- Standard OPS Query ---

@router.post("/query", response_model=ResponseEnvelope)
def query_ops(payload: OpsQueryRequest) -> ResponseEnvelope:
    envelope = handle_ops_query(payload.mode, payload.question)
    return ResponseEnvelope.success(data={"answer": envelope.model_dump()})


@router.get("/observability/kpis", response_model=ResponseEnvelope)
def observability_kpis(session: Session = Depends(get_session)) -> ResponseEnvelope:
    try:
        payload = collect_observability_metrics(session)
        if not payload:
            logger.warning("Empty observability metrics returned")
            return ResponseEnvelope.error(code=500, message="Failed to collect metrics")
        return ResponseEnvelope.success(data={"kpis": payload})
    except Exception as e:
        logger.error(f"Observability metrics error: {e}", exc_info=True)
        return ResponseEnvelope.error(code=500, message=f"Observability service error: {str(e)}")


# --- RCA (Root Cause Analysis) ---

@router.post("/rca/analyze-trace", response_model=ResponseEnvelope)
def rca_analyze_trace(
    trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run RCA on a single trace.

    Returns list of RCA hypotheses with:
    - rank, title, confidence
    - evidence (with inspector jump links)
    - checks (verification steps)
    - recommended_actions
    """
    from app.modules.inspector.crud import get_execution_trace
    from app.modules.ops.services.rca_engine import RCAEngine

    trace = get_execution_trace(session, trace_id)
    if not trace:
        return ResponseEnvelope.error(code=404, message=f"Trace {trace_id} not found")

    try:
        engine = RCAEngine()
        hypotheses = engine.analyze_single_trace(trace.answer or {})

        # Convert hypotheses to dict format with inspector links
        result = {
            "trace_id": trace_id,
            "status": trace.status,
            "hypotheses": [
                {
                    "rank": h.rank,
                    "title": h.title,
                    "confidence": h.confidence,
                    "evidence": [
                        {
                            "path": ev.path,
                            "snippet": ev.snippet,
                            "display": ev.display,
                            # Inspector jump link
                            "inspector_link": f"/admin/inspector?trace_id={trace_id}&focus={ev.path}",
                        }
                        for ev in h.evidence
                    ],
                    "checks": h.checks,
                    "recommended_actions": h.recommended_actions,
                    "description": h.description,
                }
                for h in hypotheses
            ],
        }
        return ResponseEnvelope.success(data=result)
    except Exception as e:
        logger.error(f"RCA analysis failed for trace {trace_id}: {e}")
        return ResponseEnvelope.error(code=500, message=f"RCA analysis failed: {str(e)}")


@router.post("/rca/analyze-regression", response_model=ResponseEnvelope)
def rca_analyze_regression(
    baseline_trace_id: str,
    candidate_trace_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run RCA on a regression (baseline vs candidate).

    Identifies differences and root causes.
    """
    from app.modules.inspector.crud import get_execution_trace
    from app.modules.ops.services.rca_engine import RCAEngine

    baseline_trace = get_execution_trace(session, baseline_trace_id)
    candidate_trace = get_execution_trace(session, candidate_trace_id)

    if not baseline_trace:
        return ResponseEnvelope.error(code=404, message=f"Baseline trace {baseline_trace_id} not found")
    if not candidate_trace:
        return ResponseEnvelope.error(code=404, message=f"Candidate trace {candidate_trace_id} not found")

    try:
        engine = RCAEngine()
        hypotheses = engine.analyze_diff(
            baseline_trace.answer or {},
            candidate_trace.answer or {},
        )

        # Convert with inspector links
        result = {
            "baseline_trace_id": baseline_trace_id,
            "candidate_trace_id": candidate_trace_id,
            "hypotheses": [
                {
                    "rank": h.rank,
                    "title": h.title,
                    "confidence": h.confidence,
                    "evidence": [
                        {
                            "path": ev.path,
                            "snippet": ev.snippet,
                            "display": ev.display,
                            # Inspector comparison link
                            "inspector_link": f"/admin/inspector?baseline={baseline_trace_id}&candidate={candidate_trace_id}&focus={ev.path}",
                        }
                        for ev in h.evidence
                    ],
                    "checks": h.checks,
                    "recommended_actions": h.recommended_actions,
                    "description": h.description,
                }
                for h in hypotheses
            ],
        }
        return ResponseEnvelope.success(data=result)
    except Exception as e:
        logger.error(f"RCA regression analysis failed: {e}")
        return ResponseEnvelope.error(code=500, message=f"RCA analysis failed: {str(e)}")


# --- CI OPS (Ask CI) ---

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


@router.post("/ci/ask")
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
    response_payload: ResponseEnvelope | None = None
    error_response: JSONResponse | None = None
    duration_ms: int | None = None
    trace_payload: dict[str, Any] | None = None
    flow_spans: list[Dict[str, Any]] = []

    # Initialize span tracking for this trace
    clear_spans()

    try:
        rerun_ctx: RerunContext | None = None
        if payload.rerun:
            logger.info("ci.runner.planner.skipped", extra={"reason": "rerun"})
            validator_span = start_span("validator", "stage")
            try:
                patched_plan = _apply_patch(payload.rerun.base_plan, payload.rerun.patch)
                logger.info("ci.runner.validator.start", extra={"phase": "rerun"})
                plan_validated, plan_trace = validator.validate_plan(patched_plan)
                logger.info("ci.runner.validator.done", extra={"phase": "rerun"})
                end_span(validator_span, links={"plan_path": "plan.validated"})
            except Exception as e:
                end_span(validator_span, status="error", summary={"error_type": type(e).__name__, "error_message": str(e)})
                raise
            plan_raw = payload.rerun.base_plan
            rerun_ctx = RerunContext(
                selected_ci_id=payload.rerun.selected_ci_id,
                selected_secondary_ci_id=payload.rerun.selected_secondary_ci_id,
            )
        else:
            planner_span = start_span("planner", "stage")
            try:
                planner_start = time.perf_counter()
                logger.info("ci.runner.planner.start", extra={"llm_called": False})
                plan_raw = planner_llm.create_plan(payload.question)
                elapsed_ms = int((time.perf_counter() - planner_start) * 1000)
                logger.info("ci.runner.planner.done", extra={"llm_called": False, "elapsed_ms": elapsed_ms})
                end_span(planner_span, links={"plan_path": "plan.raw"})
            except Exception as e:
                end_span(planner_span, status="error", summary={"error_type": type(e).__name__, "error_message": str(e)})
                raise

            validator_span = start_span("validator", "stage")
            try:
                logger.info("ci.runner.validator.start", extra={"phase": "initial"})
                plan_validated, plan_trace = validator.validate_plan(plan_raw)
                logger.info("ci.runner.validator.done", extra={"phase": "initial"})
                end_span(validator_span, links={"plan_path": "plan.validated"})
            except Exception as e:
                end_span(validator_span, status="error", summary={"error_type": type(e).__name__, "error_message": str(e)})
                raise

        runner_span = start_span("runner", "stage")
        try:
            runner_module = importlib.import_module(CIOrchestratorRunner.__module__)
            logger.info("ci.endpoint.entry", extra={"runner_file": runner_module.__file__})
            runner = CIOrchestratorRunner(
                plan_validated,
                plan_raw,
                tenant_id,
                payload.question,
                plan_trace,
                rerun_context=rerun_ctx,
            )
            runner._flow_spans_enabled = True
            runner._runner_span_id = runner_span
            result = runner.run()
            next_actions = result.get("next_actions") or []
            next_actions_count = len(next_actions)
            envelope_blocks = result.get("blocks") or []
            trace_payload = result.get("trace") or {}
            meta = result.get("meta")
            trace_status = "error" if trace_payload.get("errors") else "success"
            end_span(runner_span)
        except Exception as e:
            end_span(runner_span, status="error", summary={"error_type": type(e).__name__, "error_message": str(e)})
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
        context = get_request_context()
        active_trace_id = context.get("trace_id")
        if not active_trace_id or active_trace_id == "-":
            active_trace_id = context.get("request_id") or str(uuid.uuid4())
        parent_trace_id = context.get("parent_trace_id")
        if parent_trace_id == "-":
            parent_trace_id = None
        request_payload = {
            "question": payload.question,
            "rerun": payload.rerun.dict(exclude_none=True) if payload.rerun else None,
        }
        # Capture flow spans before trace persistence
        flow_spans = get_all_spans()

        try:
            with get_session() as session:
                persist_execution_trace(
                    session=session,
                    trace_id=active_trace_id,
                    parent_trace_id=parent_trace_id,
                    feature="ci",
                    endpoint="/ops/ci/ask",
                    method="POST",
                    ops_mode=get_settings().ops_mode,
                    question=payload.question,
                    status=trace_status,
                    duration_ms=duration_ms,
                    request_payload=request_payload,
                    plan_raw=trace_payload.get("plan_raw"),
                    plan_validated=trace_payload.get("plan_validated"),
                    trace_payload=trace_payload,
                    answer_meta=meta,
                    blocks=envelope_blocks,
                    flow_spans=flow_spans if flow_spans else None,
                )
        except Exception as exc:
            logger.exception("ci.trace.persist_failed", exc_info=exc)
        status = "error" if trace_status == "error" else "ok"
        response: CiAskResponse = CiAskResponse(**result)
        response_payload = ResponseEnvelope.success(data=response.dict())
    except Exception as exc: 
        status = "error"
        logger.exception("ci.ask.error", exc_info=exc)
        error_body = ResponseEnvelope.error(message=str(exc)).model_dump(mode="json")
        error_response = JSONResponse(status_code=500, content=error_body)
    finally:
        elapsed_ms = duration_ms if duration_ms is not None else int((time.perf_counter() - start) * 1000)
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
    assert response_payload or error_response  # ensure we always have a response
    return response_payload or error_response


# --- UI Actions (Deterministic Interactive UI) ---

@router.post("/ui-actions", response_model=ResponseEnvelope)
async def execute_ui_action(
    payload: UIActionRequest,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
) -> ResponseEnvelope:
    """
    Execute deterministic UI action based on action_id.

    Flow:
    1. Validate action_id and inputs
    2. Generate new trace_id with parent_trace_id = payload.trace_id
    3. Route to deterministic executor based on action_id
    4. Execute using existing OPS executors (no LLM)
    5. Persist execution trace
    6. Return blocks as UIActionResponse
    """
    from .services.ui_actions import execute_action_deterministic, mask_sensitive_inputs

    # Setup
    tenant_id = x_tenant_id or "t1"
    trace_id = str(uuid.uuid4())
    parent_trace_id = payload.trace_id
    settings = get_settings()

    ts_start = time.time()

    # Start span tracking
    clear_spans()
    action_span = start_span(f"ui_action:{payload.action_id}", "ui_action")

    try:
        # Validate OPS_MODE (no mock in real mode)
        mode = payload.context.get("mode", "real")
        if mode == "mock" and settings.OPS_MODE == "real":
            raise ValueError("Mock mode not allowed in OPS_MODE=real")

        # Execute action deterministically
        with get_session() as session:
            executor_result = await execute_action_deterministic(
                action_id=payload.action_id,
                inputs=payload.inputs,
                context=payload.context,
                session=session,
            )

        # End span
        end_span(action_span, status="ok")

        # Persist trace
        duration_ms = int((time.time() - ts_start) * 1000)
        all_spans = get_all_spans()

        with get_session() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature="ui_action",
                endpoint="/ops/ui-actions",
                method="POST",
                ops_mode=mode,
                question=f"UI Action: {payload.action_id}",
                status="success",
                duration_ms=duration_ms,
                request_payload={
                    "trace_id": payload.trace_id,
                    "action_id": payload.action_id,
                    "inputs": mask_sensitive_inputs(payload.inputs),
                    "context": payload.context,
                },
                applied_assets=None,
                plan_raw=None,
                plan_validated=None,
                tool_calls=executor_result.get("tool_calls", []),
                references=executor_result.get("references", []),
                answer_envelope={
                    "meta": {
                        "route": payload.action_id,
                        "route_reason": "UI action execution",
                        "timing_ms": duration_ms,
                        "trace_id": trace_id,
                        "parent_trace_id": parent_trace_id,
                    },
                    "blocks": executor_result["blocks"],
                },
                flow_spans=all_spans,
            )

        logger.info(
            "ui_action.success",
            extra={
                "action_id": payload.action_id,
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "duration_ms": duration_ms,
                "blocks_count": len(executor_result.get("blocks", [])),
            },
        )

        return ResponseEnvelope.success(
            data={
                "trace_id": trace_id,
                "status": "ok",
                "blocks": executor_result["blocks"],
                "references": executor_result.get("references", []),
                "state_patch": executor_result.get("state_patch", {}),
            }
        )

    except Exception as exc:
        # Error handling
        end_span(action_span, status="error", summary={"error_type": type(exc).__name__, "error_message": str(exc)})

        duration_ms = int((time.time() - ts_start) * 1000)
        all_spans = get_all_spans()

        # Error blocks
        error_blocks = [
            {
                "type": "markdown",
                "content": f"## ❌ UI Action 실행 실패\n\n**Action**: {payload.action_id}\n\n**Error**: {str(exc)}",
            }
        ]

        with get_session() as session:
            persist_execution_trace(
                session=session,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                feature="ui_action",
                endpoint="/ops/ui-actions",
                method="POST",
                ops_mode=payload.context.get("mode", "real"),
                question=f"UI Action: {payload.action_id}",
                status="error",
                duration_ms=duration_ms,
                request_payload={
                    "trace_id": payload.trace_id,
                    "action_id": payload.action_id,
                    "inputs": mask_sensitive_inputs(payload.inputs),
                    "context": payload.context,
                },
                applied_assets=None,
                plan_raw=None,
                plan_validated=None,
                tool_calls=[],
                references=[],
                answer_envelope={
                    "meta": {
                        "route": payload.action_id,
                        "route_reason": "UI action execution",
                        "timing_ms": duration_ms,
                        "trace_id": trace_id,
                        "parent_trace_id": parent_trace_id,
                        "error": str(exc),
                    },
                    "blocks": error_blocks,
                },
                flow_spans=all_spans,
            )

        logger.error(
            "ui_action.error",
            extra={
                "action_id": payload.action_id,
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "error": str(exc),
                "duration_ms": duration_ms,
            },
        )

        return ResponseEnvelope.success(
            data={
                "trace_id": trace_id,
                "status": "error",
                "blocks": error_blocks,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        )


# --- Regression Watch (Step 5) ---


@router.get("/golden-queries")
def list_golden_queries(session: Any = Depends(get_session)) -> ResponseEnvelope:
    """List all golden queries"""
    from app.modules.inspector.crud import list_golden_queries

    queries = list_golden_queries(session)
    return ResponseEnvelope.success(
        data={
            "queries": [
                {
                    "id": q.id,
                    "name": q.name,
                    "query_text": q.query_text,
                    "ops_type": q.ops_type,
                    "enabled": q.enabled,
                    "created_at": q.created_at.isoformat(),
                }
                for q in queries
            ]
        }
    )


@router.post("/golden-queries")
def create_golden_query(
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """Create a new golden query"""
    from app.modules.inspector.crud import create_golden_query as crud_create

    try:
        query = crud_create(
            session,
            name=payload.get("name"),
            query_text=payload.get("query_text"),
            ops_type=payload.get("ops_type"),
            options=payload.get("options"),
        )
        return ResponseEnvelope.success(
            data={
                "id": query.id,
                "name": query.name,
                "query_text": query.query_text,
                "ops_type": query.ops_type,
                "created_at": query.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to create golden query: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.put("/golden-queries/{query_id}")
def update_golden_query(
    query_id: str,
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """Update golden query"""
    from app.modules.inspector.crud import update_golden_query as crud_update

    try:
        query = crud_update(
            session,
            query_id,
            name=payload.get("name"),
            query_text=payload.get("query_text"),
            enabled=payload.get("enabled"),
            options=payload.get("options"),
        )
        if not query:
            return ResponseEnvelope.error(message="Golden query not found")
        return ResponseEnvelope.success(
            data={
                "id": query.id,
                "name": query.name,
                "query_text": query.query_text,
                "ops_type": query.ops_type,
                "enabled": query.enabled,
                "created_at": query.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to update golden query: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.delete("/golden-queries/{query_id}")
def delete_golden_query(
    query_id: str,
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """Delete golden query"""
    from app.modules.inspector.crud import delete_golden_query as crud_delete

    try:
        success = crud_delete(session, query_id)
        if not success:
            return ResponseEnvelope.error(message="Golden query not found")
        return ResponseEnvelope.success(data={"deleted": True})
    except Exception as e:
        logger.error(f"Failed to delete golden query: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.post("/golden-queries/{query_id}/set-baseline")
def set_baseline(
    query_id: str,
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """Set baseline trace for a golden query"""
    from app.modules.inspector.crud import (
        get_golden_query,
        get_execution_trace,
        create_regression_baseline,
    )

    try:
        # Verify golden query exists
        query = get_golden_query(session, query_id)
        if not query:
            return ResponseEnvelope.error(message="Golden query not found")

        # Verify baseline trace exists
        baseline_trace_id = payload.get("trace_id")
        baseline_trace = get_execution_trace(session, baseline_trace_id)
        if not baseline_trace:
            return ResponseEnvelope.error(message="Baseline trace not found")

        # Create baseline record
        baseline = create_regression_baseline(
            session,
            golden_query_id=query_id,
            baseline_trace_id=baseline_trace_id,
            baseline_status=baseline_trace.status,
            asset_versions=baseline_trace.asset_versions,
            created_by=payload.get("created_by"),
        )

        return ResponseEnvelope.success(
            data={
                "id": baseline.id,
                "baseline_trace_id": baseline.baseline_trace_id,
                "baseline_status": baseline.baseline_status,
                "created_at": baseline.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to set baseline: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.post("/golden-queries/{query_id}/run-regression")
def run_regression(
    query_id: str,
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run regression check for a golden query.

    Executes the golden query and compares result against baseline.
    """
    from app.modules.inspector.crud import (
        get_golden_query,
        get_execution_trace,
        get_latest_regression_baseline,
        create_regression_run,
    )
    from app.modules.ops.services.regression_executor import (
        compute_regression_diff,
        determine_judgment,
    )

    try:
        # Verify golden query exists
        query = get_golden_query(session, query_id)
        if not query:
            return ResponseEnvelope.error(message="Golden query not found")

        # Get baseline
        baseline = get_latest_regression_baseline(session, query_id)
        if not baseline:
            return ResponseEnvelope.error(message="No baseline set for this golden query")

        # Get baseline trace for comparison
        baseline_trace = get_execution_trace(session, baseline.baseline_trace_id)
        if not baseline_trace:
            return ResponseEnvelope.error(message="Baseline trace not found")

        # Execute golden query (use existing OPS handler)
        ts_start = time.time()
        clear_spans()

        try:
            # Use handle_ops_query to execute the golden query
            answer_envelope = handle_ops_query(query.ops_type, query.query_text)
            duration_ms = int((time.time() - ts_start) * 1000)

            # Create execution trace for candidate
            candidate_trace_id = str(uuid.uuid4())
            all_spans = get_all_spans()

            # Build candidate trace dict for comparison
            candidate_trace = {
                "status": "success",
                "asset_versions": [],  # Will be populated by OPS execution
                "plan_validated": answer_envelope.meta.__dict__ if answer_envelope.meta else None,
                "execution_steps": [],
                "answer": answer_envelope.model_dump() if answer_envelope else {},
                "references": answer_envelope.blocks if answer_envelope and answer_envelope.blocks else [],
                "ui_render": {"error_count": 0},
            }

            # Compute regression diff
            diff = compute_regression_diff(
                baseline_trace.model_dump(),
                candidate_trace,
            )

            # Determine judgment
            judgment, verdict_reason = determine_judgment(diff)

            # Create regression run record
            run = create_regression_run(
                session,
                golden_query_id=query_id,
                baseline_id=baseline.id,
                candidate_trace_id=candidate_trace_id,
                baseline_trace_id=baseline.baseline_trace_id,
                judgment=judgment,
                triggered_by=payload.get("triggered_by", "manual"),
                verdict_reason=verdict_reason,
                diff_summary={
                    "assets_changed": diff.assets_changed,
                    "plan_intent_changed": diff.plan_intent_changed,
                    "plan_output_changed": diff.plan_output_changed,
                    "tool_calls_added": diff.tool_calls_added,
                    "tool_calls_removed": diff.tool_calls_removed,
                    "tool_calls_failed": diff.tool_calls_failed,
                    "blocks_structure_changed": diff.blocks_structure_changed,
                    "references_variance": diff.references_variance,
                    "status_changed": diff.status_changed,
                    "ui_errors_increase": diff.ui_errors_increase,
                },
                trigger_info=payload.get("trigger_info"),
                execution_duration_ms=duration_ms,
            )

            return ResponseEnvelope.success(
                data={
                    "id": run.id,
                    "candidate_trace_id": candidate_trace_id,
                    "baseline_trace_id": baseline.baseline_trace_id,
                    "judgment": judgment,
                    "verdict_reason": verdict_reason,
                    "diff_summary": run.diff_summary,
                    "execution_duration_ms": duration_ms,
                    "created_at": run.created_at.isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Regression execution failed: {e}")
            return ResponseEnvelope.error(
                message=f"Regression execution failed: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Failed to run regression: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.get("/regression-runs")
def list_regression_runs(
    golden_query_id: str | None = None,
    limit: int = 50,
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """List regression runs"""
    from app.modules.inspector.crud import list_regression_runs

    try:
        runs = list_regression_runs(session, golden_query_id=golden_query_id, limit=limit)
        return ResponseEnvelope.success(
            data={
                "runs": [
                    {
                        "id": r.id,
                        "golden_query_id": r.golden_query_id,
                        "baseline_id": r.baseline_id,
                        "candidate_trace_id": r.candidate_trace_id,
                        "baseline_trace_id": r.baseline_trace_id,
                        "judgment": r.judgment,
                        "verdict_reason": r.verdict_reason,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in runs
                ]
            }
        )
    except Exception as e:
        logger.error(f"Failed to list regression runs: {e}")
        return ResponseEnvelope.error(message=str(e))


@router.get("/regression-runs/{run_id}")
def get_regression_run(
    run_id: str,
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """Get regression run details"""
    from app.modules.inspector.crud import get_regression_run

    try:
        run = get_regression_run(session, run_id)
        if not run:
            return ResponseEnvelope.error(message="Regression run not found")

        return ResponseEnvelope.success(
            data={
                "id": run.id,
                "golden_query_id": run.golden_query_id,
                "baseline_id": run.baseline_id,
                "candidate_trace_id": run.candidate_trace_id,
                "baseline_trace_id": run.baseline_trace_id,
                "judgment": run.judgment,
                "verdict_reason": run.verdict_reason,
                "diff_summary": run.diff_summary,
                "triggered_by": run.triggered_by,
                "execution_duration_ms": run.execution_duration_ms,
                "created_at": run.created_at.isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to get regression run: {e}")
        return ResponseEnvelope.error(message=str(e))


# --- RCA Assist (Step 6) ---


@router.post("/rca")
def run_rca(
    payload: Dict[str, Any],
    session: Any = Depends(get_session),
) -> ResponseEnvelope:
    """
    Run Root Cause Analysis on a trace or trace diff.

    Mode 1: Single trace analysis (failure/issue diagnosis)
    {
      "mode": "single",
      "trace_id": "abc-123",
      "options": { "max_hypotheses": 5, "include_snippets": true, "use_llm": true }
    }

    Mode 2: Diff analysis (regression/change analysis)
    {
      "mode": "diff",
      "baseline_trace_id": "base-123",
      "candidate_trace_id": "cand-456",
      "options": { "max_hypotheses": 7, "include_snippets": true, "use_llm": true }
    }

    Returns RCA trace with hypotheses as blocks.
    """
    from app.modules.inspector.crud import (
        get_execution_trace,
        create_execution_trace,
    )
    from app.modules.ops.services.rca_engine import RCAEngine
    from app.modules.llm.rca_summarizer import summarize_rca_results

    try:
        mode = payload.get("mode")
        options = payload.get("options", {})
        max_hypotheses = options.get("max_hypotheses", 5)
        use_llm = options.get("use_llm", True)
        include_snippets = options.get("include_snippets", True)

        ts_start = time.time()
        rca_engine = RCAEngine()

        # ===== Single Trace Mode =====
        if mode == "single":
            trace_id = payload.get("trace_id")
            if not trace_id:
                return ResponseEnvelope.error(message="trace_id required for single mode")

            # Fetch trace
            trace = get_execution_trace(session, trace_id)
            if not trace:
                return ResponseEnvelope.error(message=f"Trace {trace_id} not found")

            # Generate hypotheses
            hypotheses_list = rca_engine.analyze_single_trace(
                trace.model_dump(),
                max_hypotheses=max_hypotheses,
            )

            source_traces = [trace_id]
            question = f"RCA: Analyze failure in trace {trace_id[:8]}..."

        # ===== Diff Mode =====
        elif mode == "diff":
            baseline_trace_id = payload.get("baseline_trace_id")
            candidate_trace_id = payload.get("candidate_trace_id")

            if not baseline_trace_id or not candidate_trace_id:
                return ResponseEnvelope.error(
                    message="baseline_trace_id and candidate_trace_id required for diff mode"
                )

            # Fetch traces
            baseline = get_execution_trace(session, baseline_trace_id)
            candidate = get_execution_trace(session, candidate_trace_id)

            if not baseline:
                return ResponseEnvelope.error(message=f"Baseline trace {baseline_trace_id} not found")
            if not candidate:
                return ResponseEnvelope.error(message=f"Candidate trace {candidate_trace_id} not found")

            # Generate hypotheses
            try:
                hypotheses_list = rca_engine.analyze_diff(
                    baseline.model_dump(),
                    candidate.model_dump(),
                    max_hypotheses=max_hypotheses,
                )
            except Exception as diff_err:
                logger.error(f"Diff analysis error: {diff_err}", exc_info=True)
                raise

            source_traces = [baseline_trace_id, candidate_trace_id]
            question = f"RCA: Analyze regression/change between {baseline_trace_id[:8]}... and {candidate_trace_id[:8]}..."

        else:
            return ResponseEnvelope.error(message="mode must be 'single' or 'diff'")

        # ===== Convert to dict and summarize =====
        rca_data = rca_engine.to_dict()
        hypotheses = rca_data.get("hypotheses", [])

        # Add LLM descriptions if enabled
        if use_llm and hypotheses:
            try:
                hypotheses = summarize_rca_results(
                    hypotheses,
                    use_llm=True,
                    language="korean",
                )
                logger.info(f"RCA summarization completed for {len(hypotheses)} hypotheses")
            except Exception as e:
                logger.warning(f"RCA summarization failed (using fallback): {e}")
                for hyp in hypotheses:
                    hyp["description"] = ""

        # ===== Create RCA trace =====
        rca_trace_id = str(uuid.uuid4())
        duration_ms = int((time.time() - ts_start) * 1000)

        # Build RCA answer blocks
        rca_blocks = []

        # Block 1: Summary
        rca_blocks.append({
            "type": "markdown",
            "title": "RCA Analysis Summary",
            "content": f"**Mode:** {mode}\n**Traces Analyzed:** {', '.join(source_traces[:2])}\n**Hypotheses Found:** {len(hypotheses)}",
        })

        # Block 2: Hypotheses list (one hypothesis per block)
        for hyp in hypotheses:
            hyp_content = f"""**Rank {hyp['rank']}: {hyp['title']}**

**Confidence:** {hyp['confidence'].upper()}

**Description:** {hyp.get('description', 'N/A')}

**Evidence:**
"""
            for evidence in hyp.get("evidence", []):
                hyp_content += f"- `{evidence['path']}`: {evidence['snippet']}\n"

            hyp_content += f"\n**Verification Checks:**\n"
            for check in hyp.get("checks", [])[:3]:
                hyp_content += f"- {check}\n"

            hyp_content += f"\n**Recommended Actions:**\n"
            for action in hyp.get("recommended_actions", [])[:3]:
                hyp_content += f"- {action}\n"

            rca_blocks.append({
                "type": "markdown",
                "title": f"Hypothesis {hyp['rank']}",
                "content": hyp_content,
            })

        # Create execution trace for RCA run
        from app.modules.inspector.models import TbExecutionTrace

        rca_trace_obj = TbExecutionTrace(
            trace_id=rca_trace_id,
            parent_trace_id=None,  # RCA is top-level
            feature="rca",
            endpoint="/ops/rca",
            method="POST",
            ops_mode="real",
            question=question,
            status="success" if hypotheses else "warning",
            duration_ms=duration_ms,
            request_payload={
                "mode": mode,
                "source_traces": source_traces,
                "options": options,
            },
            applied_assets=None,
            asset_versions=None,
            fallbacks=None,
            plan_raw=None,
            plan_validated=None,
            execution_steps=None,
            references=None,
            answer={
                "meta": {
                    "route": "rca",
                    "summary": f"RCA: {len(hypotheses)} hypotheses generated",
                },
                "blocks": rca_blocks,
            },
            ui_render=None,
            audit_links=None,
            flow_spans=None,
        )
        try:
            rca_trace = create_execution_trace(session, rca_trace_obj)
            logger.info(f"RCA trace created successfully: {rca_trace_id}")
        except Exception as trace_err:
            logger.error(f"Failed to create RCA trace: {trace_err}", exc_info=True)
            return ResponseEnvelope.error(message=f"Failed to persist RCA results: {str(trace_err)}")

        # ===== Return response =====
        logger.info(f"Returning RCA response with trace_id: {rca_trace_id}")
        return ResponseEnvelope.success(
            data={
                "trace_id": rca_trace_id,
                "status": "ok",
                "blocks": rca_blocks,
                "rca": {
                    "mode": mode,
                    "source_traces": source_traces,
                    "hypotheses": hypotheses,
                    "total_hypotheses": len(hypotheses),
                    "analysis_duration_ms": duration_ms,
                },
            }
        )

    except Exception as e:
        logger.error(f"RCA analysis failed: {e}", exc_info=True)
        return ResponseEnvelope.error(message=f"RCA analysis failed: {str(e)}")
