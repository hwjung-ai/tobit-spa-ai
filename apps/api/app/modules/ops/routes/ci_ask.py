"""
OPS Ask Route

Handles OPS orchestration asking/planning endpoints for
complex query analysis with plan generation and execution.

Endpoints:
    POST /ops/ask - Primary endpoint
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime
from typing import Any

from core.auth import get_current_user
from core.config import get_settings
from core.db import get_session_context
from core.logging import get_logger, get_request_context
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from models.history import QueryHistory
from schemas import ResponseEnvelope

from app.modules.asset_registry.loader import (
    load_catalog_asset,
    load_mapping_asset,
    load_policy_asset,
    load_resolver_asset,
    load_source_asset,
)
from app.modules.auth.models import TbUser
from app.modules.inspector.service import persist_execution_trace
from app.modules.inspector.span_tracker import (
    clear_spans,
    end_span,
    get_all_spans,
    start_span,
)
from app.modules.ops.schemas import (
    CiAskRequest,
    CiAskResponse,
    ReplanPatchDiff,
    ReplanTrigger,
    RerunContext,
)
from app.modules.ops.security import SecurityUtils
from app.modules.ops.services.orchestration.blocks import text_block
from app.modules.ops.services.orchestration.orchestrator.runner import OpsOrchestratorRunner
from app.modules.ops.services.orchestration.planner import planner_llm, validator
from app.modules.ops.services.orchestration.planner.plan_schema import (
    Intent,
    Plan,
    PlanOutput,
    PlanOutputKind,
    View,
)
from app.modules.ops.services.control_loop import evaluate_replan

from .utils import _tenant_id, apply_patch, generate_references_from_tool_calls

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.post("/ask")
def ask_ops(
    payload: CiAskRequest,
    request: Request,
    tenant_id: str = Depends(_tenant_id),
    current_user: TbUser = Depends(get_current_user),
):
    """Process OPS question with planning and execution.

    OPS orchestration flow:
    1. Question normalization with resolver rules
    2. Plan generation with LLM-driven tool selection
    3. Route determination (direct/reject/orchestration)
    4. Stage execution (validate, execute, compose, present)
    5. Fallback replanning on error
    6. Trace persistence and history update

    Args:
        payload: Ask request with question and optional rerun context
        request: HTTP request object
        tenant_id: Tenant ID from header

    Returns:
        CiAskResponse with answer, blocks, trace, and next actions
    """
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

    # Create history entry on request receipt
    user_id = str(current_user.id)
    history_entry = QueryHistory(
        tenant_id=tenant_id,
        user_id=user_id,
        feature="ops",
        question=payload.question,
        summary=None,
        status="processing",
        response=None,
        metadata_info={
            "uiMode": "all",
            "backendMode": "all",
        },
    )

    # Save history to DB and generate ID
    try:
        with get_session_context() as session:
            session.add(history_entry)
            session.commit()
            session.refresh(history_entry)
        history_id = history_entry.id
    except Exception as exc:
        logger.exception("ci.history.create_failed", exc_info=exc)
        history_id = None

    # 로깅을 위해 요청 데이터 마스킹
    masked_payload = SecurityUtils.mask_dict(payload.model_dump())
    logger.info(
        "ci.ask.start",
        extra={
            "query_len": len(payload.question),
            "has_patch": patched,
            "patch_keys": patch_keys,
            "has_trace_plan_validated": has_trace_plan_validated,
            "history_id": str(history_id) if history_id else None,
            "masked_payload": masked_payload,
        },
    )

    response_payload: ResponseEnvelope | None = None
    error_response: JSONResponse | None = None
    duration_ms: int | None = None
    trace_payload: dict[str, Any] = {}
    meta: dict[str, Any] | None = None
    envelope_blocks: list[dict[str, Any]] = []
    next_actions: list[dict[str, Any]] = []
    flow_spans: list[dict[str, Any]] = []
    active_trace_id: str | None = None
    parent_trace_id: str | None = None
    result: dict[str, Any] | None = None
    trace_status: str = "success"

    # Initialize span tracking
    clear_spans()

    # Set trace_id early before any errors
    context = get_request_context()
    active_trace_id = getattr(request.state, "trace_id", None) or context.get("trace_id")
    request_id = getattr(request.state, "request_id", None) or context.get("request_id")
    logger.info(
        f"ci.ask.context: trace_id={active_trace_id}, request_id={request_id}"
    )
    if not active_trace_id or active_trace_id == "-" or active_trace_id == "None":
        active_trace_id = str(uuid.uuid4())
        logger.info(f"ci.ask.new_trace_id: {active_trace_id}")
    parent_trace_id = context.get("parent_trace_id")
    if parent_trace_id == "-":
        parent_trace_id = None

    def _apply_resolver_rules(
        question: str, resolver_payload: dict[str, Any] | None
    ) -> tuple[str, list[str]]:
        """Apply resolver rules to normalize question."""
        if not resolver_payload:
            return question, []
        rules = resolver_payload.get("rules", [])
        applied: list[str] = []
        normalized = question
        for rule in rules:
            rule_type = rule.get("rule_type")
            rule_data = rule.get("rule_data", {})
            name = rule.get("name") or rule_data.get("name") or rule_type or "rule"
            if rule_type == "alias_mapping":
                source_entity = rule_data.get("source_entity")
                target_entity = rule_data.get("target_entity")
                if (
                    source_entity
                    and target_entity
                    and source_entity.lower() in normalized.lower()
                ):
                    normalized = normalized.replace(source_entity, target_entity)
                    applied.append(name)
            elif rule_type == "pattern_rule":
                pattern = rule_data.get("pattern")
                replacement = rule_data.get("replacement")
                if pattern and replacement is not None:
                    try:
                        normalized = re.sub(pattern, replacement, normalized)
                        applied.append(name)
                    except re.error:
                        logger.warning(
                            "resolver.rule.invalid_pattern", extra={"name": name}
                        )
            elif rule_type == "transformation":
                transform = rule_data.get("transformation_type")
                if transform == "lowercase":
                    normalized = normalized.lower()
                    applied.append(name)
                elif transform == "uppercase":
                    normalized = normalized.upper()
                    applied.append(name)
                elif transform == "strip":
                    normalized = normalized.strip()
                    applied.append(name)
        return normalized, applied

    def build_fallback_plan(source: Plan) -> Plan:
        """Build a fallback plan with reduced complexity."""
        history = source.history.model_copy(update={"enabled": False})
        graph = source.graph.model_copy(update={"depth": 0, "view": None})
        list_spec = source.list.model_copy(update={"enabled": False})
        output = source.output.model_copy(
            update={"blocks": ["text", "table"], "primary": "table"}
        )
        return source.model_copy(
            update={
                "intent": Intent.LOOKUP,
                "view": View.SUMMARY,
                "metric": None,
                "history": history,
                "graph": graph,
                "list": list_spec,
                "output": output,
            }
        )

    try:
        # Load assets
        settings = get_settings()
        resolver_asset_name = (
            payload.resolver_asset or settings.ops_default_resolver_asset
        )
        schema_asset_name = payload.schema_asset or settings.ops_default_schema_asset
        source_asset_name = payload.source_asset or settings.ops_default_source_asset

        resolver_payload = (
            load_resolver_asset(resolver_asset_name) if resolver_asset_name else None
        )
        schema_payload = (
            load_catalog_asset(schema_asset_name) if schema_asset_name else None
        )
        source_payload = (
            load_source_asset(source_asset_name) if source_asset_name else None
        )
        mapping_payload, _ = load_mapping_asset("graph_relation", scope="ops")
        _policy_payload = load_policy_asset("plan_budget", scope="ops")

        normalized_question, resolver_rules_applied = _apply_resolver_rules(
            payload.question, resolver_payload
        )

        # Plan generation
        rerun_ctx: RerunContext | None = None
        plan_output: PlanOutput | None = None
        plan_raw: Plan | None = None
        plan_validated: Plan | None = None
        plan_trace: dict[str, Any] = {
            "asset_context": {
                "source_asset": source_asset_name,
                "schema_asset": schema_asset_name,
                "resolver_asset": resolver_asset_name,
            },
            "resolver_rules_applied": resolver_rules_applied,
        }
        replan_events: list[dict[str, Any]] = []
        planner_elapsed_ms: int = 0

        if payload.rerun:
            # Handle rerun path (skip planner, go directly to validator)
            route_plan_start = time.perf_counter()
            logger.info("ci.runner.planner.skipped", extra={"reason": "rerun"})
            validator_span = start_span("validator", "stage")
            try:
                patched_plan = apply_patch(payload.rerun.base_plan, payload.rerun.patch)
                logger.info("ci.runner.validator.start", extra={"phase": "rerun"})
                plan_validated, plan_trace = validator.validate_plan(
                    patched_plan, resolver_payload=resolver_payload
                )
                logger.info("ci.runner.validator.done", extra={"phase": "rerun"})
                end_span(validator_span, links={"plan_path": "plan.validated"})
                planner_elapsed_ms = int((time.perf_counter() - route_plan_start) * 1000)
                logger.info(f"ci.runner.rerun.route_plan_time: {planner_elapsed_ms}ms")
            except Exception as e:
                end_span(
                    validator_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise
            plan_raw = payload.rerun.base_plan
            plan_output = PlanOutput(
                kind=PlanOutputKind.PLAN,
                plan=plan_validated,
                confidence=1.0,
                reasoning="Rerun execution",
                metadata={"route": "orch"},
            )
            rerun_ctx = RerunContext(
                selected_ci_id=payload.rerun.selected_ci_id,
                selected_secondary_ci_id=payload.rerun.selected_secondary_ci_id,
            )
            # Record rerun event
            timestamp = datetime.now(get_settings().timezone_offset).isoformat()
            replan_events.append(
                {
                    "event_type": "replan_execution",
                    "stage_name": "route_plan",
                    "trigger": {
                        "trigger_type": "manual",
                        "stage_name": "route_plan",
                        "severity": "low",
                        "reason": "rerun requested",
                        "timestamp": timestamp,
                        "metadata": {"patch_keys": patch_keys},
                    },
                    "timestamp": timestamp,
                }
            )
        else:
            # Handle normal path (planner -> validator)
            route_plan_start = time.perf_counter()
            planner_span = start_span("planner", "stage")
            try:
                logger.info(
                    "ci.runner.planner.start",
                    extra={
                        "llm_called": False,
                        "has_schema": bool(schema_payload),
                        "has_source": bool(source_payload),
                    },
                )
                plan_output = planner_llm.create_plan_output(
                    normalized_question,
                    schema_context=schema_payload,
                    source_context=source_payload,
                )
                planner_elapsed_ms = int((time.perf_counter() - route_plan_start) * 1000)
                logger.info(
                    "ci.runner.planner.done",
                    extra={"llm_called": False, "elapsed_ms": planner_elapsed_ms},
                )
                end_span(planner_span, links={"plan_path": "plan.raw"})
            except Exception as e:
                end_span(
                    planner_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise

            if plan_output.kind == PlanOutputKind.PLAN and plan_output.plan:
                plan_raw = plan_output.plan
                validator_span = start_span("validator", "stage")
                try:
                    logger.info("ci.runner.validator.start", extra={"phase": "initial"})
                    plan_validated, plan_trace = validator.validate_plan(
                        plan_raw, resolver_payload=resolver_payload
                    )
                    logger.info("ci.runner.validator.done", extra={"phase": "initial"})
                    end_span(validator_span, links={"plan_path": "plan.validated"})
                except Exception as e:
                    end_span(
                        validator_span,
                        status="error",
                        summary={
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                    )
                    raise
                plan_output = plan_output.model_copy(update={"plan": plan_validated})

        if plan_output is None:
            raise ValueError("Planner output missing")

        # Update history with trace_id
        if history_id:
            try:
                with get_session_context() as session:
                    history_entry = session.get(QueryHistory, history_id)
                    if history_entry:
                        history_entry.trace_id = active_trace_id
                        session.add(history_entry)
                        session.commit()
            except Exception as exc:
                logger.warning(f"Failed to update trace_id in history: {exc}")

        # Route determination and execution
        if plan_output.kind in (PlanOutputKind.DIRECT, PlanOutputKind.REJECT):
            # Handle direct/reject routes
            duration_ms = int((time.perf_counter() - start) * 1000)
            if plan_output.kind == PlanOutputKind.DIRECT and plan_output.direct_answer:
                answer = plan_output.direct_answer.answer
                blocks = [text_block(answer)]
                references = plan_output.direct_answer.references
                route_reason = plan_output.direct_answer.reasoning or "Direct answer"
            else:
                reject_reason = (
                    plan_output.reject_payload.reason if plan_output.reject_payload
                    else "Not supported"
                )
                answer = f"Query rejected: {reject_reason}"
                blocks = [text_block(answer)]
                references = []
                route_reason = plan_output.reasoning or "Rejected"

            trace_payload = {
                "route": plan_output.kind.value,
                "tool_calls": [],
                "references": references,
                "errors": [],
                "tenant_id": tenant_id,
                "trace_id": active_trace_id,
                "parent_trace_id": parent_trace_id,
            }
            meta = {
                "route": plan_output.kind.value,
                "route_reason": route_reason,
                "timing_ms": duration_ms,
                "summary": answer,
                "trace_id": active_trace_id,
                "parent_trace_id": parent_trace_id,
            }
            result = {
                "answer": answer,
                "blocks": blocks,
                "trace": trace_payload,
                "next_actions": [],
                "meta": meta,
            }
            envelope_blocks = blocks
            next_actions_count = 0
            trace_status = "success"
        else:
            # Handle orchestration route with OpsOrchestratorRunner
            runner_span = start_span("runner", "stage")
            try:
                runner = OpsOrchestratorRunner(
                    plan_validated,
                    plan_raw,
                    tenant_id,
                    normalized_question,
                    plan_trace,
                    rerun_context=rerun_ctx,
                    asset_overrides=payload.asset_overrides,
                )
                runner._flow_spans_enabled = True
                runner._runner_span_id = runner_span
                result = runner.run(plan_output)
                next_actions = result.get("next_actions") or []
                next_actions_count = len(next_actions)
                envelope_blocks = result.get("blocks") or []
                trace_payload = result.get("trace") or {}
                meta = result.get("meta") or {}

                # Generate references from tool calls if needed
                tool_calls = trace_payload.get("tool_calls") or result.get("tool_calls") or []
                if tool_calls and not trace_payload.get("references"):
                    trace_payload["references"] = generate_references_from_tool_calls(
                        tool_calls
                    )
                else:
                    trace_payload.setdefault("references", [])

                trace_payload.setdefault("route", "orch")
                meta["route"] = "orch"
                trace_status = "error" if trace_payload.get("errors") else "success"

                # Handle error replanning
                if trace_status == "error" and not payload.rerun:
                    trigger = ReplanTrigger(
                        trigger_type="error",
                        stage_name="execute",
                        severity="high",
                        reason="runner execution error",
                        timestamp=datetime.now(get_settings().timezone_offset).isoformat(),
                    )
                    fallback_plan = build_fallback_plan(plan_validated)
                    should_replan = evaluate_replan(
                        trigger,
                        ReplanPatchDiff(
                            before=plan_validated.model_dump(),
                            after=fallback_plan.model_dump(),
                        ),
                    )

                    if should_replan:
                        # Execute fallback plan
                        validator_span = start_span("validator", "stage")
                        try:
                            fallback_validated, fallback_trace = (
                                validator.validate_plan(
                                    fallback_plan, resolver_payload=resolver_payload
                                )
                            )
                            end_span(
                                validator_span, links={"plan_path": "plan.validated"}
                            )
                        except Exception as e:
                            end_span(
                                validator_span,
                                status="error",
                                summary={
                                    "error_type": type(e).__name__,
                                    "error_message": str(e),
                                },
                            )
                            raise

                        fallback_output = PlanOutput(
                            kind=PlanOutputKind.PLAN,
                            plan=fallback_validated,
                            confidence=plan_output.confidence,
                            reasoning="Auto replan fallback",
                            metadata={"route": "orch"},
                        )
                        runner = OpsOrchestratorRunner(
                            fallback_validated,
                            fallback_plan,
                            tenant_id,
                            normalized_question,
                            fallback_trace,
                            rerun_context=rerun_ctx,
                            asset_overrides=payload.asset_overrides,
                        )
                        runner._flow_spans_enabled = True
                        runner._runner_span_id = runner_span
                        result = runner.run(fallback_output)
                        next_actions = result.get("next_actions") or []
                        next_actions_count = len(next_actions)
                        envelope_blocks = result.get("blocks") or []
                        trace_payload = result.get("trace") or {}
                        meta = result.get("meta") or {}
                        trace_status = "error" if trace_payload.get("errors") else "success"

                end_span(runner_span)
            except Exception as e:
                end_span(
                    runner_span,
                    status="error",
                    summary={"error_type": type(e).__name__, "error_message": str(e)},
                )
                raise
            finally:
                duration_ms = int((time.perf_counter() - start) * 1000)

        # Inject trace_id into result
        if result and result.get("meta") is None:
            result["meta"] = {}
        if result:
            result["meta"]["trace_id"] = active_trace_id
            result["meta"]["parent_trace_id"] = parent_trace_id
        if result and result.get("trace") is None:
            result["trace"] = {}
        if result:
            result["trace"]["trace_id"] = active_trace_id
            result["trace"]["parent_trace_id"] = parent_trace_id

        response: CiAskResponse = CiAskResponse(**result)
        response_payload = ResponseEnvelope.success(data=response.model_dump())

    except Exception as exc:
        status = "error"
        logger.exception("ci.ask.error", exc_info=exc)
        error_body = ResponseEnvelope.error(message=str(exc)).model_dump(mode="json")
        error_response = JSONResponse(status_code=500, content=error_body)
        response_payload = None
        result = None

        # Update history on error
        if history_id:
            try:
                with get_session_context() as session:
                    history_entry = session.get(QueryHistory, history_id)
                    if history_entry:
                        history_entry.status = "error"
                        history_entry.response = error_body
                        history_entry.summary = f"Error: {str(exc)[:200]}"
                        session.add(history_entry)
                        session.commit()
            except Exception as hist_exc:
                logger.exception("ci.history.error_update_failed", exc_info=hist_exc)

    finally:
        elapsed_ms = (
            duration_ms
            if duration_ms is not None
            else int((time.perf_counter() - start) * 1000)
        )

        # Persist trace (always, even on error)
        request_payload = {
            "question": payload.question,
            "rerun": payload.rerun.dict(exclude_none=True) if payload.rerun else None,
        }
        flow_spans = get_all_spans()

        try:
            with get_session_context() as session:
                persist_execution_trace(
                    session=session,
                    trace_id=active_trace_id,
                    parent_trace_id=parent_trace_id,
                    feature="ops",
                    endpoint="/ops/ask",
                    method="POST",
                    ops_mode=get_settings().ops_mode,
                    question=payload.question,
                    status=trace_status,
                    duration_ms=elapsed_ms,
                    request_payload=request_payload,
                    plan_raw=trace_payload.get("plan_raw") if trace_payload else None,
                    plan_validated=trace_payload.get("plan_validated") if trace_payload else None,
                    trace_payload=trace_payload if trace_payload else {},
                    answer_meta=meta if meta else None,
                    blocks=envelope_blocks if envelope_blocks else None,
                    flow_spans=flow_spans if flow_spans else None,
                )
                logger.info(f"Trace persisted: {active_trace_id}")
        except Exception as exc:
            logger.exception("ops.trace.persist_failed", exc_info=exc)

        # Update history with final status
        if history_id:
            try:
                with get_session_context() as session:
                    history_entry = session.get(QueryHistory, history_id)
                    if history_entry:
                        history_entry.status = status
                        history_entry.response = (
                            jsonable_encoder(response_payload.model_dump())
                            if response_payload
                            else None
                        )
                        if result:
                            history_entry.summary = (
                                result.get("meta", {}).get("summary")
                                or result.get("meta", {}).get("answer", "")[:200]
                            )
                            history_entry.metadata_info = jsonable_encoder(
                                {
                                    "uiMode": "all",
                                    "backendMode": "all",
                                    "trace": trace_payload,
                                    "nextActions": next_actions,
                                }
                            )
                        session.add(history_entry)
                        session.commit()
            except Exception as exc:
                logger.exception("ci.history.update_failed", exc_info=exc)

        logger.info(
            "ops.ask.done",
            extra={
                "status": status,
                "elapsed_ms": elapsed_ms,
                "blocks_count": len(envelope_blocks or []),
                "next_actions_count": next_actions_count,
            },
        )

    assert response_payload or error_response
    return response_payload or error_response
