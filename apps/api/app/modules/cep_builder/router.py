from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from core.db import get_session
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from starlette.requests import Request
from schemas.common import ResponseEnvelope
from sqlalchemy import desc, select
from sqlmodel import Session
from sse_starlette.sse import EventSourceResponse

from .crud import (
    acknowledge_event,
    create_notification,
    create_rule,
    find_exec_log_by_simulation,
    get_event,
    get_exec_log,
    get_latest_exec_log_for_rule,
    get_notification,
    get_rule,
    list_events,
    list_exec_logs,
    list_metric_poll_snapshots,
    list_notification_logs,
    list_notifications,
    list_rules,
    record_exec_log,
    summarize_events,
    update_notification,
    update_rule,
)
from .event_broadcaster import event_broadcaster
from .executor import evaluate_trigger, manual_trigger
from .models import (
    TbCepExecLog,
    TbCepMetricPollSnapshot,
    TbCepNotificationLog,
    TbCepSchedulerState,
)
from .scheduler import (
    get_metric_poll_stats,
    get_metric_polling_telemetry,
    get_scheduler_instance_id,
    is_scheduler_leader,
)
from .schemas import (
    CepEventDetail,
    CepEventRead,
    CepEventSummary,
    CepExecLogRead,
    CepNotificationCreate,
    CepNotificationLogRead,
    CepNotificationRead,
    CepNotificationUpdate,
    CepRuleCreate,
    CepRuleRead,
    CepRuleUpdate,
    CepSimulateRequest,
    CepSimulateResponse,
    CepTriggerRequest,
    CepTriggerResponse,
    # Phase 2: Form-based UI schemas
    CepRuleFormData,
    ConditionSpec,
    ValidationResult,
    PreviewResult,
    FieldInfo,
    ConditionTemplate,
)

router = APIRouter(prefix="/cep", tags=["cep-builder"])


def _snapshot_summary(
    snapshot: TbCepMetricPollSnapshot | None,
) -> dict[str, Any] | None:
    if not snapshot:
        return None
    return {
        "tick_at": snapshot.tick_at.isoformat(),
        "instance_id": snapshot.instance_id,
        "is_leader": snapshot.is_leader,
        "tick_duration_ms": snapshot.tick_duration_ms,
        "rule_count": snapshot.rule_count,
        "evaluated_count": snapshot.evaluated_count,
        "matched_count": snapshot.matched_count,
        "skipped_count": snapshot.skipped_count,
        "fail_count": snapshot.fail_count,
        "last_error": snapshot.last_error,
    }


def _extract_severity(payload: dict[str, Any], trigger: dict[str, Any]) -> str:
    severity = payload.get("severity") or trigger.get("severity")
    if isinstance(severity, str) and severity.strip():
        return severity
    return "info"


def _build_summary(reason: str | None, payload: dict[str, Any]) -> str:
    if reason:
        return reason
    summary = payload.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary
    if isinstance(summary, dict):
        matched = summary.get("matched_count")
        failed = summary.get("fail_count")
        instance_id = summary.get("instance_id")
        parts = []
        if matched is not None:
            parts.append(f"matched={matched}")
        if failed is not None:
            parts.append(f"fail={failed}")
        if instance_id:
            parts.append(f"instance={instance_id}")
        if parts:
            return ", ".join(parts)
    return "Event triggered"


def _extract_condition(payload: dict[str, Any]) -> tuple[bool | None, Any | None]:
    condition = payload.get("condition_evaluated")
    extracted = payload.get("extracted_value")
    return (condition if isinstance(condition, bool) else None, extracted)


def _truncate_json(value: Any | None, limit: int = 32768) -> str | None:
    if value is None:
        return None
    try:
        text = json.dumps(value, default=str)
    except Exception:
        return str(value)
    return text if len(text) <= limit else text[:limit] + "…"


@router.get("/rules")
def list_rules_endpoint(
    trigger_type: str | None = Query(None),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    rules = list_rules(session, trigger_type=trigger_type)
    payload = [CepRuleRead.from_orm(rule).model_dump() for rule in rules]
    return ResponseEnvelope.success(data={"rules": payload})


@router.get("/rules/{rule_id}")
def get_rule_endpoint(
    rule_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(rule).model_dump()}
    )


@router.post("/rules")
def create_rule_endpoint(
    payload: CepRuleCreate, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    rule = create_rule(session, payload)
    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(rule).model_dump()}
    )


@router.put("/rules/{rule_id}")
def update_rule_endpoint(
    rule_id: str,
    payload: CepRuleUpdate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    updated = update_rule(session, rule, payload)
    return ResponseEnvelope.success(
        data={"rule": CepRuleRead.from_orm(updated).model_dump()}
    )


@router.post("/rules/{rule_id}/simulate")
def simulate_rule_endpoint(
    rule_id: str,
    payload: CepSimulateRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
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


@router.post("/rules/{rule_id}/trigger")
def trigger_rule_endpoint(
    rule_id: str,
    payload: CepTriggerRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    executed_by = payload.executed_by or "cep-builder"
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


@router.get("/rules/{rule_id}/exec-logs")
def get_logs_endpoint(
    rule_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    rule = get_rule(session, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    logs = list_exec_logs(session, rule_id, limit=limit)
    payload = [CepExecLogRead.from_orm(log).model_dump() for log in logs]
    return ResponseEnvelope.success(data={"logs": payload})


@router.get("/notifications")
def list_notifications_endpoint(
    active_only: bool = Query(True),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    notifications = list_notifications(session, active_only=active_only)
    payload = [
        CepNotificationRead.from_orm(notification).model_dump()
        for notification in notifications
    ]
    return ResponseEnvelope.success(data={"notifications": payload})


@router.get("/notifications/{notification_id}")
def get_notification_endpoint(
    notification_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    notification = get_notification(session, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return ResponseEnvelope.success(
        data={"notification": CepNotificationRead.from_orm(notification).model_dump()}
    )


@router.post("/notifications")
def create_notification_endpoint(
    payload: CepNotificationCreate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    notification = create_notification(session, payload.model_dump())
    return ResponseEnvelope.success(
        data={"notification": CepNotificationRead.from_orm(notification).model_dump()}
    )


@router.put("/notifications/{notification_id}")
def update_notification_endpoint(
    notification_id: str,
    payload: CepNotificationUpdate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    notification = get_notification(session, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    update_payload = payload.model_dump(exclude_unset=True)
    updated = update_notification(session, notification, update_payload)
    return ResponseEnvelope.success(
        data={"notification": CepNotificationRead.from_orm(updated).model_dump()}
    )


@router.get("/notifications/{notification_id}/logs")
def get_notification_logs_endpoint(
    notification_id: str,
    limit: int = Query(200, ge=1, le=500),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    notification = get_notification(session, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    logs = list_notification_logs(session, notification_id, limit=limit)
    payload = [CepNotificationLogRead.from_orm(log).model_dump() for log in logs]
    return ResponseEnvelope.success(data={"logs": payload})


@router.get("/events")
def list_events_endpoint(
    acked: bool | None = Query(None),
    severity: str | None = Query(None),
    rule_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    rows = list_events(
        session,
        acked=acked,
        rule_id=rule_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )
    events: list[dict[str, Any]] = []
    for log, notification, rule in rows:
        payload = log.payload or {}
        trigger = notification.trigger or {}
        severity_value = _extract_severity(payload, trigger)
        if severity and severity_value != severity:
            continue
        summary = _build_summary(log.reason, payload)
        events.append(
            CepEventRead(
                event_id=str(log.log_id),
                triggered_at=log.fired_at,
                status=log.status,
                summary=summary,
                severity=severity_value,
                ack=log.ack,
                ack_at=log.ack_at,
                rule_id=str(notification.rule_id) if notification.rule_id else None,
                rule_name=rule.rule_name if rule else None,
                notification_id=str(notification.notification_id),
            ).model_dump()
        )
    return ResponseEnvelope.success(
        data={"events": events, "limit": limit, "offset": offset}
    )


@router.get("/events/run")
def get_run_endpoint(
    exec_log_id: str | None = Query(None),
    simulation_id: str | None = Query(None),
    tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    tenant = tenant_id or "default"
    if not exec_log_id and not simulation_id:
        return ResponseEnvelope.success(
            data={
                "run": {
                    "found": False,
                    "tenant_id": tenant,
                    "message": "Provide exec_log_id or simulation_id to look up a run.",
                }
            }
        )
    exec_log = get_exec_log(session, exec_log_id) if exec_log_id else None
    if not exec_log and simulation_id:
        exec_log = find_exec_log_by_simulation(session, simulation_id)
    if not exec_log:
        return ResponseEnvelope.success(
            data={
                "run": {
                    "found": False,
                    "tenant_id": tenant,
                    "exec_log_id": exec_log_id,
                    "simulation_id": simulation_id,
                    "message": "No CEP simulate run found for the requested ID.",
                }
            }
        )
    references = exec_log.references or {}
    trigger = references.get("trigger") or {}
    evidence = trigger.copy()
    simulation_id_value = references.get("simulation_id")
    run_details = {
        "found": True,
        "tenant_id": tenant,
        "exec_log_id": str(exec_log.exec_id),
        "simulation_id": simulation_id_value,
        "created_at": exec_log.triggered_at.isoformat(),
        "rule_id": str(exec_log.rule_id),
        "status": exec_log.status,
        "duration_ms": exec_log.duration_ms,
        "error_message": exec_log.error_message,
        "condition_evaluated": trigger.get("condition_evaluated")
        if "condition_evaluated" in trigger
        else references.get("condition_evaluated"),
        "extracted_value": trigger.get("extracted_value")
        if "extracted_value" in trigger
        else references.get("extracted_value"),
        "evidence": {
            "runtime_endpoint": evidence.get("runtime_endpoint"),
            "method": evidence.get("method"),
            "value_path": evidence.get("value_path"),
            "op": evidence.get("op"),
            "threshold": evidence.get("threshold"),
            "extracted_value": evidence.get("extracted_value"),
            "condition_evaluated": evidence.get("condition_evaluated"),
            "fetch_status": evidence.get("fetch_status"),
            "fetch_error": evidence.get("fetch_error"),
        },
        "raw": _truncate_json(references),
    }
    return ResponseEnvelope.success(data={"run": run_details})


@router.post("/events/{event_id}/ack")
def ack_event_endpoint(
    event_id: str,
    ack_by: str | None = Query(None),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    log = session.get(TbCepNotificationLog, event_id)
    if not log:
        raise HTTPException(status_code=404, detail="Event not found")
    updated = acknowledge_event(session, log, ack_by=ack_by)
    payload = CepNotificationLogRead.from_orm(updated).model_dump()
    summary = summarize_events(session)
    event_broadcaster.publish(
        "ack_event",
        {
            "event_id": str(updated.log_id),
            "ack": updated.ack,
            "ack_at": updated.ack_at.isoformat() if updated.ack_at else None,
        },
    )
    event_broadcaster.publish(
        "summary",
        {
            "unacked_count": summary["unacked_count"],
            "by_severity": summary["by_severity"],
        },
    )
    return ResponseEnvelope.success(data={"event": payload})


@router.get("/events/summary")
def event_summary_endpoint(session: Session = Depends(get_session)) -> ResponseEnvelope:
    summary = summarize_events(session)
    payload = CepEventSummary(**summary).model_dump()
    return ResponseEnvelope.success(data={"summary": payload})


@router.get("/events/stream")
async def event_stream(
    request: Request,
    session: Session = Depends(get_session)
) -> EventSourceResponse:
    summary = summarize_events(session)

    async def event_generator():
        yield {"event": "summary", "data": json.dumps(summary)}
        queue = event_broadcaster.subscribe()
        try:
            while True:
                # Check if client disconnected or server is shutting down
                if await request.is_disconnected():
                    break

                try:
                    # Use shorter timeout (1s) to allow faster shutdown detection
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield {
                        "event": message["type"],
                        "data": json.dumps(message["data"]),
                    }
                except asyncio.TimeoutError:
                    # Check disconnect again on timeout
                    if await request.is_disconnected():
                        break
                    yield {"event": "ping", "data": "{}"}
        except (asyncio.CancelledError, GeneratorExit):
            # Gracefully handle shutdown request
            yield {"event": "shutdown", "data": "{}"}
            raise
        finally:
            event_broadcaster.unsubscribe(queue)

    return EventSourceResponse(event_generator())


@router.get("/events/{event_id}")
def get_event_endpoint(
    event_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    try:
        uuid.UUID(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid event id") from exc
    row = get_event(session, event_id)
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    log, notification, rule = row
    payload = log.payload or {}
    trigger = notification.trigger or {}
    summary = _build_summary(log.reason, payload)
    condition_evaluated, extracted_value = _extract_condition(payload)
    exec_log_payload = None
    exec_log_id = payload.get("exec_log_id")
    if exec_log_id:
        exec_log = session.get(TbCepExecLog, exec_log_id)
        if exec_log:
            exec_log_payload = CepExecLogRead.from_orm(exec_log).model_dump()
            if condition_evaluated is None:
                condition_evaluated = exec_log.references.get("condition_evaluated")
            if extracted_value is None:
                extracted_value = exec_log.references.get("extracted_value")
    if (
        condition_evaluated is None or extracted_value is None
    ) and notification.rule_id:
        exec_log = get_latest_exec_log_for_rule(
            session, rule_id=str(notification.rule_id), before=log.fired_at
        )
        if exec_log:
            exec_log_payload = CepExecLogRead.from_orm(exec_log).model_dump()
            if condition_evaluated is None:
                condition_evaluated = exec_log.references.get("condition_evaluated")
            if extracted_value is None:
                extracted_value = exec_log.references.get("extracted_value")
    detail = CepEventDetail(
        event_id=str(log.log_id),
        triggered_at=log.fired_at,
        status=log.status,
        reason=log.reason,
        summary=summary,
        severity=_extract_severity(payload, trigger),
        ack=log.ack,
        ack_at=log.ack_at,
        ack_by=log.ack_by,
        notification_id=str(notification.notification_id),
        rule_id=str(notification.rule_id) if notification.rule_id else None,
        rule_name=rule.rule_name if rule else None,
        payload=payload,
        condition_evaluated=condition_evaluated,
        extracted_value=extracted_value,
        exec_log=exec_log_payload,
    ).model_dump()
    return ResponseEnvelope.success(data={"event": detail})


@router.get("/scheduler/status")
def scheduler_status(session: Session = Depends(get_session)) -> ResponseEnvelope:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=30)
    latest_leader = session.exec(
        select(TbCepSchedulerState)
        .where(TbCepSchedulerState.is_leader.is_(True))
        .order_by(desc(TbCepSchedulerState.updated_at))
    ).first()
    leader = (
        latest_leader if latest_leader and latest_leader.updated_at >= cutoff else None
    )
    leader_stale = bool(latest_leader and latest_leader.updated_at < cutoff)
    response = {
        "instance_id": get_scheduler_instance_id(),
        "is_leader": is_scheduler_leader(),
        "leader_instance_id": leader.instance_id if leader else None,
        "last_heartbeat_at": leader.last_heartbeat_at if leader else None,
        "started_at": leader.started_at if leader else None,
        "updated_at": leader.updated_at if leader else None,
        "leader_stale": leader_stale,
    }
    response.update(get_metric_poll_stats())
    return ResponseEnvelope.success(data={"status": response})


@router.get("/scheduler/metric-polling")
def metric_polling_telemetry() -> ResponseEnvelope:
    telemetry = get_metric_polling_telemetry()
    return ResponseEnvelope.success(data={"telemetry": telemetry})


@router.get("/scheduler/metric-polling/snapshots")
def metric_polling_snapshots(
    limit: int = Query(200, ge=1, le=500),
    since_minutes: int | None = Query(None, ge=1),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    snapshots = list_metric_poll_snapshots(
        session, limit=limit, since_minutes=since_minutes
    )
    payload = [_snapshot_summary(snapshot) for snapshot in snapshots]
    return ResponseEnvelope.success(data={"snapshots": payload})


@router.get("/scheduler/metric-polling/snapshots/latest")
def metric_polling_snapshots_latest(
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    snapshots = list_metric_poll_snapshots(session, limit=1)
    latest = _snapshot_summary(snapshots[0]) if snapshots else None
    return ResponseEnvelope.success(data={"snapshot": latest})


@router.get("/scheduler/instances")
def scheduler_instances(session: Session = Depends(get_session)) -> ResponseEnvelope:
    instances = session.exec(
        select(TbCepSchedulerState).order_by(desc(TbCepSchedulerState.updated_at))
    ).all()
    payload = [
        {
            "instance_id": instance.instance_id,
            "is_leader": instance.is_leader,
            "last_heartbeat_at": instance.last_heartbeat_at,
            "started_at": instance.started_at,
            "updated_at": instance.updated_at,
            "notes": instance.notes,
        }
        for instance in instances
    ]
    return ResponseEnvelope.success(data={"instances": payload})


# ============================================================================
# Phase 2: Form-based UI API Endpoints
# ============================================================================


@router.post("/validate/condition")
def validate_condition(
    condition: ConditionSpec, payload: dict[str, Any]
) -> ResponseEnvelope:
    """단일 조건 검증"""
    try:
        from .executor import _evaluate_single_condition

        matched, refs = _evaluate_single_condition(condition.model_dump(), payload)
        result = ValidationResult(
            valid=True,
            suggestions=(
                ["조건이 매치되었습니다." if matched else "조건이 매치되지 않았습니다."]
            ),
        )
    except Exception as e:
        result = ValidationResult(valid=False, errors=[str(e)])
    return ResponseEnvelope.success(data={"validation": result.model_dump()})


@router.get("/condition-templates")
def get_condition_templates() -> ResponseEnvelope:
    """조건 템플릿 조회"""
    templates = [
        ConditionTemplate(
            id="gt",
            name="초과",
            description="값이 임계값보다 큼",
            operator=">",
            example_value=80,
            category="numeric",
        ),
        ConditionTemplate(
            id="lt",
            name="미만",
            description="값이 임계값보다 작음",
            operator="<",
            example_value=20,
            category="numeric",
        ),
        ConditionTemplate(
            id="eq",
            name="같음",
            description="값이 정확히 일치",
            operator="==",
            example_value="error",
            category="string",
        ),
        ConditionTemplate(
            id="ne",
            name="다름",
            description="값이 일치하지 않음",
            operator="!=",
            example_value="success",
            category="string",
        ),
        ConditionTemplate(
            id="gte",
            name="이상",
            description="값이 임계값 이상",
            operator=">=",
            example_value=70,
            category="numeric",
        ),
        ConditionTemplate(
            id="lte",
            name="이하",
            description="값이 임계값 이하",
            operator="<=",
            example_value=90,
            category="numeric",
        ),
    ]
    return ResponseEnvelope.success(
        data={"templates": [t.model_dump() for t in templates]}
    )


@router.post("/rules/preview")
def preview_rule(
    trigger_spec: dict[str, Any],
    conditions: list[dict[str, Any]] | None = None,
    test_payload: dict[str, Any] | None = None,
) -> ResponseEnvelope:
    """규칙 미리보기 (조건 평가만 수행)"""
    try:
        from .executor import _evaluate_composite_conditions, _evaluate_event_trigger

        if conditions:
            # 복합 조건 평가
            logic = "AND"  # 기본값
            matched, refs = _evaluate_composite_conditions(conditions, logic, test_payload or {})
            result = PreviewResult(
                condition_matched=matched,
                would_execute=matched,
                references=refs,
                condition_evaluation_tree=refs,
            )
        else:
            # 트리거 스펙 평가
            matched, refs = _evaluate_event_trigger(trigger_spec, test_payload)
            result = PreviewResult(
                condition_matched=matched,
                would_execute=matched,
                references=refs,
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseEnvelope.success(data={"preview": result.model_dump()})


@router.get("/field-suggestions")
def get_field_suggestions(search: str = "") -> ResponseEnvelope:
    """자동완성용 필드 제안"""
    # 기본 필드 제안
    common_fields = [
        FieldInfo(
            name="cpu",
            description="CPU 사용률",
            type="number",
            examples=[45.2, 78.5, 92.1],
        ),
        FieldInfo(
            name="memory",
            description="메모리 사용률",
            type="number",
            examples=[32.0, 64.5, 85.3],
        ),
        FieldInfo(
            name="disk",
            description="디스크 사용률",
            type="number",
            examples=[50.0, 75.2, 95.8],
        ),
        FieldInfo(
            name="status",
            description="상태",
            type="string",
            examples=["success", "error", "warning"],
        ),
        FieldInfo(
            name="count",
            description="카운트",
            type="number",
            examples=[1, 5, 10],
        ),
        FieldInfo(
            name="duration_ms",
            description="지속시간 (밀리초)",
            type="number",
            examples=[100, 500, 2000],
        ),
    ]

    if search:
        common_fields = [f for f in common_fields if search.lower() in f.name.lower()]

    return ResponseEnvelope.success(
        data={"fields": [f.model_dump() for f in common_fields]}
    )
