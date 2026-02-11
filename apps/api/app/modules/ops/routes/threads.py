"""
OPS Threads Routes

Handles execution flow endpoints for isolated stage testing, stage comparison,
and execution trace operations.

Endpoints:
    POST /ops/stage-test - Execute isolated stage test
    POST /ops/stage-compare - Compare stages between traces
    POST /ops/rca - Run root cause analysis on traces
"""

from __future__ import annotations

import uuid
from typing import Any

from core.config import get_settings
from core.db import get_session
from core.logging import get_logger
from fastapi import APIRouter, Depends, Header
from schemas import ResponseEnvelope
from sqlmodel import Session

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.post("/stage-test", response_model=ResponseEnvelope)
async def execute_isolated_stage_test(
    payload: dict[str, Any],
    x_tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
) -> ResponseEnvelope:
    """Execute a single stage in isolation for testing and validation.

    Allows testing individual OPS stages with asset overrides and baseline
    comparison for regression testing.

    Payload structure:
        {
            "stage": "route_plan|validate|execute|compose|present",
            "question": "test question",
            "test_plan": {...},
            "asset_overrides": [...],
            "baseline_trace_id": "optional_trace_id"
        }

    Args:
        payload: Isolated stage test request
        x_tenant_id: Tenant ID from header

    Returns:
        ResponseEnvelope with stage execution result and diagnostics
    """
    import time

    from app.modules.ops.schemas import (
        ExecutionContext,
        StageInput,
    )
    from app.modules.ops.services.ci.orchestrator.stage_executor import StageExecutor

    logger_inst = get_logger(__name__)
    get_settings()

    # Setup
    if not x_tenant_id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400, detail="X-Tenant-Id header is required"
        )
    tenant_id = x_tenant_id
    trace_id = str(uuid.uuid4())

    # Validate stage
    valid_stages = ["route_plan", "validate", "execute", "compose", "present"]
    if payload.get("stage") not in valid_stages:
        return ResponseEnvelope.error(
            message=f"Invalid stage: {payload.get('stage')}. Must be one of {valid_stages}"
        )

    # Create execution context
    context = ExecutionContext(
        tenant_id=tenant_id,
        question=payload.get("question", ""),
        trace_id=trace_id,
        test_mode=True,
        asset_overrides=payload.get("asset_overrides", []),
        baseline_trace_id=payload.get("baseline_trace_id"),
    )

    logger_inst.info(
        f"Starting isolated stage test: {payload.get('stage')}",
        extra={
            "tenant_id": tenant_id,
            "stage": payload.get("stage"),
            "test_mode": True,
            "asset_overrides_count": len(payload.get("asset_overrides", [])),
        },
    )

    try:
        # Create stage executor
        stage_executor = StageExecutor(context)

        # Build stage input
        stage_input = StageInput(
            stage=payload.get("stage"),
            applied_assets=payload.get("asset_overrides", []),
            params=payload.get("test_plan", {}),
            prev_output=None,
        )

        # Execute stage
        start_time = time.time()
        stage_output = await stage_executor.execute_stage(stage_input)
        duration_ms = int((time.time() - start_time) * 1000)

        logger_inst.info(
            f"Stage test completed: {payload.get('stage')}",
            extra={
                "duration_ms": duration_ms,
                "status": stage_output.diagnostics.status,
            },
        )

        return ResponseEnvelope.success(
            data={
                "stage": payload.get("stage"),
                "result": stage_output.result,
                "duration_ms": duration_ms,
                "diagnostics": stage_output.diagnostics.dict(),
                "references": stage_output.references,
                "asset_overrides_used": payload.get("asset_overrides", []),
                "baseline_trace_id": payload.get("baseline_trace_id"),
                "trace_id": trace_id,
            }
        )

    except Exception as e:
        logger_inst.error(
            f"Stage test failed: {payload.get('stage')} - {str(e)}", exc_info=True
        )
        return ResponseEnvelope.error(message=f"Stage test failed: {str(e)}")


@router.post("/stage-compare", response_model=ResponseEnvelope)
async def compare_stages(
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Compare stages between two execution traces for regression analysis.

    Analyzes differences in stage execution between baseline and current traces
    to detect regressions or improvements.

    Payload structure:
        {
            "baseline_trace_id": "trace_id_1",
            "current_trace_id": "trace_id_2",
            "stages_to_compare": ["route_plan", "validate", "execute", "compose", "present"],
            "comparison_depth": "detailed|summary"
        }

    Args:
        payload: Comparison request with trace IDs and options
        session: Database session dependency

    Returns:
        ResponseEnvelope with detailed stage comparison results
    """
    from app.modules.inspector.service import get_execution_trace

    try:
        baseline_id = payload.get("baseline_trace_id")
        current_id = payload.get("current_trace_id")
        stages_to_compare = payload.get(
            "stages_to_compare",
            ["route_plan", "validate", "execute", "compose", "present"],
        )
        comparison_depth = payload.get("comparison_depth", "summary")

        if not baseline_id or not current_id:
            return ResponseEnvelope.error(
                message="baseline_trace_id and current_trace_id are required"
            )

        # Fetch traces
        baseline_trace = get_execution_trace(session, baseline_id)
        current_trace = get_execution_trace(session, current_id)

        if not baseline_trace or not current_trace:
            return ResponseEnvelope.error(message="One or both traces not found")

        # Compare stages
        comparison_results = []

        for stage in stages_to_compare:
            baseline_stage = None
            current_stage = None

            # Find stage in baseline trace
            for stage_output in baseline_trace.get("stage_outputs", []):
                if stage_output.get("stage") == stage:
                    baseline_stage = stage_output
                    break

            # Find stage in current trace
            for stage_output in current_trace.get("stage_outputs", []):
                if stage_output.get("stage") == stage:
                    current_stage = stage_output
                    break

            if baseline_stage and current_stage:
                comparison = {
                    "stage": stage,
                    "baseline": {
                        "duration_ms": baseline_stage.get("duration_ms"),
                        "status": baseline_stage.get("diagnostics", {}).get("status"),
                        "counts": baseline_stage.get("diagnostics", {}).get(
                            "counts", {}
                        ),
                        "has_references": len(baseline_stage.get("references", [])) > 0,
                    },
                    "current": {
                        "duration_ms": current_stage.get("duration_ms"),
                        "status": current_stage.get("diagnostics", {}).get("status"),
                        "counts": current_stage.get("diagnostics", {}).get(
                            "counts", {}
                        ),
                        "has_references": len(current_stage.get("references", [])) > 0,
                    },
                    "changed": False,
                }

                # Check for changes
                if (
                    comparison["baseline"]["duration_ms"]
                    != comparison["current"]["duration_ms"]
                    or comparison["baseline"]["status"]
                    != comparison["current"]["status"]
                    or comparison["baseline"]["has_references"]
                    != comparison["current"]["has_references"]
                ):
                    comparison["changed"] = True

                if comparison_depth == "detailed":
                    comparison["baseline_result"] = baseline_stage.get("result", {})
                    comparison["current_result"] = current_stage.get("result", {})
                    comparison["baseline_references"] = baseline_stage.get(
                        "references", []
                    )
                    comparison["current_references"] = current_stage.get(
                        "references", []
                    )

                comparison_results.append(comparison)

        # Calculate summary metrics
        total_stages = len(comparison_results)
        changed_stages = len([r for r in comparison_results if r["changed"]])
        regressed_stages = len(
            [
                r
                for r in comparison_results
                if r["current"]["status"] == "error"
                and r["baseline"]["status"] != "error"
            ]
        )

        return ResponseEnvelope.success(
            data={
                "baseline_trace_id": baseline_id,
                "current_trace_id": current_id,
                "total_stages": total_stages,
                "changed_stages": changed_stages,
                "regressed_stages": regressed_stages,
                "comparison_results": comparison_results,
                "summary": {
                    "regression_detected": regressed_stages > 0,
                    "change_percentage": (changed_stages / total_stages * 100)
                    if total_stages > 0
                    else 0,
                    "performance_change": sum(
                        1 for r in comparison_results if r["changed"]
                    )
                    / total_stages
                    * 100
                    if total_stages > 0
                    else 0,
                },
            }
        )

    except Exception as e:
        logger.error(f"Stage comparison failed: {str(e)}", exc_info=True)
        return ResponseEnvelope.error(message=f"Stage comparison failed: {str(e)}")
