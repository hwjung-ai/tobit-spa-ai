"""
OPS Regression Routes

Handles golden queries and regression testing endpoints for monitoring
query result changes over time.

Endpoints:
    GET /ops/golden-queries - List all golden queries
    POST /ops/golden-queries - Create a new golden query
    PUT /ops/golden-queries/{query_id} - Update a golden query
    DELETE /ops/golden-queries/{query_id} - Delete a golden query
    POST /ops/golden-queries/{query_id}/set-baseline - Set baseline for regression testing
    POST /ops/golden-queries/{query_id}/run-regression - Run regression test
    GET /ops/regression-runs - List regression runs
    GET /ops/regression-runs/{run_id} - Get regression run details
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from core.db import get_session
from core.logging import get_logger
from fastapi import APIRouter, Depends
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.inspector.span_tracker import clear_spans, get_all_spans
from app.modules.ops.services import handle_ops_query
from app.modules.ops.security import SecurityUtils

router = APIRouter(prefix="/ops", tags=["ops"])
logger = get_logger(__name__)


@router.get("/golden-queries")
def list_golden_queries(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """List all golden queries.

    Retrieves all registered golden queries for regression testing.

    Args:
        session: Database session dependency

    Returns:
        ResponseEnvelope with list of golden queries
    """
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
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Create a new golden query.

    Creates a golden query that can be used for baseline establishment and
    regression testing.

    Args:
        payload: Request payload with name, query_text, ops_type, options
        session: Database session dependency

    Returns:
        ResponseEnvelope with created golden query details
    """
    from app.modules.inspector.crud import create_golden_query as crud_create

    try:
        # 로깅을 위해 요청 데이터 마스킹
        masked_payload = SecurityUtils.mask_dict(payload)
        logger.info(
            "regression.golden_query.create",
            extra={
                "query_name": payload.get("name"),
                "masked_payload": masked_payload,
            },
        )

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
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Update a golden query.

    Updates the definition of an existing golden query.

    Args:
        query_id: ID of the golden query to update
        payload: Request payload with fields to update
        session: Database session dependency

    Returns:
        ResponseEnvelope with updated golden query details
    """
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
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Delete a golden query.

    Removes a golden query and its associated baselines.

    Args:
        query_id: ID of the golden query to delete
        session: Database session dependency

    Returns:
        ResponseEnvelope with deletion confirmation
    """
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
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Set baseline trace for a golden query.

    Establishes a baseline execution result for a golden query that will be
    used as reference for future regression testing.

    Args:
        query_id: ID of the golden query
        payload: Request payload with trace_id and optional metadata
        session: Database session dependency

    Returns:
        ResponseEnvelope with baseline record details
    """
    from app.modules.inspector.crud import (
        create_regression_baseline,
        get_execution_trace,
        get_golden_query,
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
    payload: dict[str, Any],
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Run regression check for a golden query.

    Executes the golden query and compares result against the established baseline,
    detecting any regressions or improvements.

    Args:
        query_id: ID of the golden query to test
        payload: Request payload with trigger info and metadata
        session: Database session dependency

    Returns:
        ResponseEnvelope with regression analysis results
    """
    from app.modules.inspector.crud import (
        create_regression_run,
        get_execution_trace,
        get_golden_query,
        get_latest_regression_baseline,
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
            return ResponseEnvelope.error(
                message="No baseline set for this golden query"
            )

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
            get_all_spans()

            # Build candidate trace dict for comparison
            candidate_trace = {
                "status": "success",
                "asset_versions": [],
                "plan_validated": (
                    answer_envelope.meta.__dict__ if answer_envelope.meta else None
                ),
                "execution_steps": [],
                "answer": answer_envelope.model_dump() if answer_envelope else {},
                "references": (
                    answer_envelope.blocks
                    if answer_envelope and answer_envelope.blocks
                    else []
                ),
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
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """List regression runs.

    Lists all regression test runs, optionally filtered by golden query.

    Args:
        golden_query_id: Optional filter by golden query ID
        limit: Maximum number of runs to return
        session: Database session dependency

    Returns:
        ResponseEnvelope with list of regression runs
    """
    from app.modules.inspector.crud import list_regression_runs

    try:
        runs = list_regression_runs(
            session, golden_query_id=golden_query_id, limit=limit
        )
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
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get regression run details.

    Retrieves detailed information about a specific regression test run.

    Args:
        run_id: ID of the regression run
        session: Database session dependency

    Returns:
        ResponseEnvelope with regression run details
    """
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
