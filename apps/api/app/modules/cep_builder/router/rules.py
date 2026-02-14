"""Rule CRUD endpoints for CEP Builder."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from core.auth import get_current_user
from core.db import get_session
from core.tenant import get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.common import ResponseEnvelope
from sqlalchemy import desc, select
from sqlmodel import Session

from app.modules.auth.models import TbUser
from app.modules.audit_log.crud import create_audit_log
import uuid as _uuid

from ..crud import (
    create_rule,
    get_rule,
    list_rules,
    record_exec_log,
    update_rule,
)
from ..executor import evaluate_trigger, manual_trigger
from ..form_converter import (
    convert_form_to_action_spec,
    convert_form_to_trigger_spec,
)
from ..models import TbCepExecLog
from ..schemas import (
    CepExecLogRead,
    CepRuleCreate,
    CepRuleFormData,
    CepRuleRead,
    CepRuleUpdate,
    CepSimulateRequest,
    CepSimulateResponse,
    CepTriggerRequest,
    CepTriggerResponse,
)

router = APIRouter(prefix="/cep/rules", tags=["cep-rules"])


@router.get("")
def list_rules_endpoint(
    trigger_type: str | None = Query(None),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """List all CEP rules, optionally filtered by trigger type."""
    rules = list_rules(session, trigger_type=trigger_type, tenant_id=tenant_id)
    payload = [CepRuleRead.from_orm(rule).model_dump() for rule in rules]
    return ResponseEnvelope.success(data={"rules": payload})


@router.get("/performance")
def get_rules_performance(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    """
    Get performance metrics for all rules.

    Returns:
        - Rules sorted by execution frequency
        - Execution count, error count, avg duration for each rule
    """
    try:
        all_rules = list_rules(session)
        now = datetime.now(timezone.utc)
        last_7d = now - timedelta(days=7)

        rules_perf = []
        for rule in all_rules:
            try:
                # Get execution logs for last 7 days
                rule_logs_query = select(TbCepExecLog).where(
                    (TbCepExecLog.rule_id == rule.rule_id) &
                    (TbCepExecLog.triggered_at >= last_7d)
                )
                rule_logs = session.exec(rule_logs_query).scalars().all()

                if rule_logs:
                    exec_count = len(rule_logs)
                    error_count = sum(1 for log in rule_logs if log.status == "fail")
                    avg_duration = sum(log.duration_ms for log in rule_logs) / exec_count

                    rules_perf.append({
                        "rule_id": str(rule.rule_id),
                        "rule_name": str(rule.rule_name),
                        "is_active": bool(rule.is_active),
                        "execution_count": int(exec_count),
                        "error_count": int(error_count),
                        "error_rate": float(error_count / exec_count),
                        "avg_duration_ms": float(round(avg_duration, 2)),
                    })
            except Exception:
                continue

        # Sort by execution count (descending)
        rules_perf.sort(key=lambda x: x["execution_count"], reverse=True)

        return ResponseEnvelope.success(
            data={
                "rules": rules_perf[:limit],
                "total_rules": int(len(all_rules)),
                "period_days": 7,
            }
        )
    except Exception:
        return ResponseEnvelope.success(
            data={
                "rules": [],
                "total_rules": 0,
                "period_days": 7,
            }
        )


@router.get("/anomaly-status/{rule_id}")
async def get_anomaly_status(
    rule_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    """
    Get anomaly detection baseline status for a rule.

    Returns baseline value count, detection method, and last detection result.
    Only applicable for rules with trigger_type='anomaly'.
    """
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.trigger_type != "anomaly":
        return ResponseEnvelope.success(
            data={
                "rule_id": str(rule.rule_id),
                "trigger_type": rule.trigger_type,
                "anomaly_enabled": False,
                "message": "This rule does not use anomaly detection",
            }
        )

    spec = rule.trigger_spec or {}
    method = spec.get("anomaly_method", "zscore")
    config = spec.get("anomaly_config", {})
    baseline_values = spec.get("baseline_values", [])

    # Try to get baseline from Redis
    from ..redis_state_manager import get_redis_state_manager
    redis_mgr = get_redis_state_manager()
    redis_baseline = None
    try:
        if await redis_mgr.is_available():
            redis_baseline = await redis_mgr.get_baseline(rule_id)
    except Exception:
        pass

    effective_baseline = redis_baseline or baseline_values

    return ResponseEnvelope.success(
        data={
            "rule_id": str(rule.rule_id),
            "trigger_type": "anomaly",
            "anomaly_enabled": True,
            "method": method,
            "config": config,
            "baseline_count": len(effective_baseline),
            "baseline_source": "redis" if redis_baseline else "trigger_spec",
            "baseline_summary": {
                "min": round(min(effective_baseline), 4) if effective_baseline else None,
                "max": round(max(effective_baseline), 4) if effective_baseline else None,
                "mean": round(sum(effective_baseline) / len(effective_baseline), 4) if effective_baseline else None,
            } if effective_baseline else None,
        }
    )


@router.get("/{rule_id}")
def get_rule_endpoint(
    rule_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    """Get a single CEP rule by ID."""
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(rule).model_dump()}
    )


@router.post("")
def create_rule_endpoint(
    payload: CepRuleCreate,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Create a new CEP rule."""
    rule = create_rule(session, payload)

    create_audit_log(
        session=session,
        trace_id=str(_uuid.uuid4()),
        resource_type="cep_rule",
        resource_id=str(rule.rule_id),
        action="create",
        actor=str(current_user.id),
        changes={"rule_name": rule.rule_name, "trigger_type": rule.trigger_type},
    )

    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(rule).model_dump()}
    )


@router.post("/form")
def create_rule_from_form(
    form_data: CepRuleFormData,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """
    Create CEP rule from form-based data.

    Converts form data to legacy trigger_spec and action_spec format,
    then creates the rule using standard create_rule endpoint.

    Args:
        form_data: Form-based rule data with composite conditions, windowing, etc.
        session: Database session

    Returns:
        ResponseEnvelope with created rule
    """
    # Convert form data to legacy format
    trigger_spec = convert_form_to_trigger_spec(form_data)
    action_spec = convert_form_to_action_spec(form_data)

    # Convert to CepRuleCreate format
    rule_create = CepRuleCreate(
        rule_name=form_data.rule_name,
        trigger_type=form_data.trigger_type,
        trigger_spec=trigger_spec,
        action_spec=action_spec,
        is_active=form_data.is_active,
        created_by=str(current_user.id),
    )

    # Create rule
    rule = create_rule(session, rule_create)

    create_audit_log(
        session=session,
        trace_id=str(_uuid.uuid4()),
        resource_type="cep_rule",
        resource_id=str(rule.rule_id),
        action="create",
        actor=str(current_user.id),
        changes={"rule_name": rule.rule_name, "trigger_type": rule.trigger_type},
    )

    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(rule).model_dump()}
    )


@router.put("/{rule_id}")
def update_rule_endpoint(
    rule_id: str,
    payload: CepRuleUpdate,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Update an existing CEP rule."""
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    updated = update_rule(session, rule, payload)

    create_audit_log(
        session=session,
        trace_id=str(_uuid.uuid4()),
        resource_type="cep_rule",
        resource_id=str(rule.rule_id),
        action="update",
        actor=str(current_user.id),
        changes={"rule_name": updated.rule_name},
    )

    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(updated).model_dump()}
    )


@router.post("/{rule_id}/simulate")
def simulate_rule_endpoint(
    rule_id: str,
    payload: CepSimulateRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Simulate a CEP rule with test payload (dry run)."""
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    start = perf_counter()
    status = "dry_run"
    references: dict[str, Any] = {}
    error_message: str | None = None
    try:
        condition, trigger_refs = evaluate_trigger(
            rule.trigger_type, rule.trigger_spec, payload.test_payload
        )
        references["trigger"] = trigger_refs
        condition_evaluated = trigger_refs.get("condition_evaluated", True)
        action_ref = {
            "endpoint": rule.action_spec.get("endpoint"),
            "method": rule.action_spec.get("method"),
            "params": rule.action_spec.get("params"),
        }
        references["action"] = action_ref
        response = CepSimulateResponse(
            condition_evaluated=condition_evaluated,
            would_execute=condition,
            resolved_action=rule.action_spec,
            references=references,
        )
        return ResponseEnvelope.success(data={"simulation": response.model_dump()})
    except HTTPException as exc:
        status = "fail"
        error_message = exc.detail if isinstance(exc.detail, str) else None
        raise
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        record_exec_log(
            session=session,
            rule_id=str(rule.rule_id),
            status=status,
            duration_ms=duration_ms,
            references=references,
            executed_by="cep-simulate",
            error_message=error_message,
        )


@router.post("/{rule_id}/trigger")
def trigger_rule_endpoint(
    rule_id: str,
    payload: CepTriggerRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
) -> ResponseEnvelope:
    """Manually trigger a CEP rule."""
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    executed_by = payload.executed_by or str(current_user.id)
    result = manual_trigger(rule, payload.payload, executed_by)
    if result["status"] == "fail":
        raise HTTPException(
            status_code=500, detail=result["error_message"] or "Trigger failed"
        )
    response = CepTriggerResponse(
        status=result["status"],
        result=result["result"],
        references=result["references"],
    )
    return ResponseEnvelope.success(data={"result": response.model_dump()})


@router.get("/{rule_id}/exec-logs")
def get_logs_endpoint(
    rule_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get execution logs for a specific rule."""
    from ..crud import list_exec_logs

    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    logs = list_exec_logs(session, rule_id, limit=limit)
    payload = [CepExecLogRead.from_orm(log).model_dump() for log in logs]
    return ResponseEnvelope.success(data={"logs": payload})
