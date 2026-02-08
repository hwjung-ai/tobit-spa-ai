from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any

from core.db import get_session

logger = logging.getLogger(__name__)
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
from .form_converter import (
    convert_form_to_trigger_spec,
    convert_form_to_action_spec,
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


@router.get("/rules/performance")
def get_rules_performance(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    """
    Get performance metrics for all rules

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
            except Exception as e:
                logger.exception(f"Error processing rule {rule.rule_id}")
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
    except Exception as e:
        logger.exception("Error in get_rules_performance")
        return ResponseEnvelope.success(
            data={
                "rules": [],
                "total_rules": 0,
                "period_days": 7,
            }
        )


@router.get("/rules/{rule_id}/anomaly-status")
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
    from .redis_state_manager import get_redis_state_manager
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


@router.post("/rules/form")
def create_rule_from_form(
    form_data: CepRuleFormData, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    """
    Create CEP rule from form-based data

    Converts form data to legacy trigger_spec and action_spec format,
    then creates the rule using standard create_rule endpoint.

    Args:
        form_data: Form-based rule data with composite conditions, windowing, etc.
        session: Database session

    Returns:
        ResponseEnvelope with created rule
    """
    # 폼 데이터 → Legacy 형식 변환
    trigger_spec = convert_form_to_trigger_spec(form_data)
    action_spec = convert_form_to_action_spec(form_data)

    # 기존 CepRuleCreate 형식으로 변환
    rule_create = CepRuleCreate(
        rule_name=form_data.rule_name,
        trigger_type=form_data.trigger_type,
        trigger_spec=trigger_spec,
        action_spec=action_spec,
        is_active=form_data.is_active,
        created_by="cep-form-builder",
    )

    # 기존 create_rule 함수로 저장
    rule = create_rule(session, rule_create)

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
    """
    이벤트 실시간 스트림 (SSE: Server-Sent Events)

    클라이언트가 연결하면:
    1. 초기 요약(summary) 전송: 현재 미승인/심각도별 이벤트 수
    2. 최근 1시간 히스토리컬 이벤트 전송 (재연결 시 손실 복구)
    3. 라이브 구독: 새 이벤트/ACK/요약 변경 실시간 전송
    4. 매 초마다 ping 전송 (연결 유지)

    이벤트 타입:
    - summary: 이벤트 요약 (unacked_count, by_severity)
    - new_event: 새로운 이벤트 발생
    - ack_event: 이벤트 승인됨
    - ping: 연결 유지 신호
    - shutdown: 서버 종료 신호

    Redis가 활성화된 경우:
    - 분산 환경에서 여러 서버의 이벤트 통합
    - Pub/Sub을 통한 실시간 전파

    폴링 방식 대비 장점:
    - 서버 부하 감소 (pull → push)
    - 네트워크 트래픽 감소
    - 낮은 지연시간 (<100ms)
    """
    # Redis 리스너 확인 및 시작
    await event_broadcaster.ensure_redis_listener()

    summary = summarize_events(session)

    async def event_generator():
        try:
            # 1. 초기 요약 전송
            yield {"event": "summary", "data": json.dumps(summary)}

            # 2. 최근 1시간 이벤트 로드백 (클라이언트 재연결 시 손실 복구)
            LOOKBACK_MINUTES = 60
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
            recent_events = session.exec(
                select(TbCepNotificationLog)
                .where(TbCepNotificationLog.fired_at >= cutoff_time)
                .order_by(TbCepNotificationLog.fired_at.asc())
                .limit(100)
            ).scalars().all()

            # 과거 이벤트 전송
            for event_log in recent_events:
                try:
                    yield {
                        "event": "historical",
                        "data": json.dumps({
                            "event_id": str(event_log.log_id),
                            "fired_at": event_log.fired_at.isoformat(),
                            "status": event_log.status,
                        })
                    }
                except Exception:
                    continue

            # 3. 라이브 구독 시작
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
        except Exception as e:
            logger.error(f"Event stream error: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

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
    ).scalars().all()
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


@router.get("/events/search")
def search_events(
    q: str | None = Query(None),
    rule_id: str | None = None,
    severity: str | None = None,
    acked: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    고급 이벤트 검색

    - q: 규칙명, 요약, 페이로드에서 전문 검색
    - rule_id: 특정 규칙 필터
    - severity: CRITICAL, HIGH, MEDIUM, LOW
    - acked: 확인 상태 필터
    - since/until: 날짜 범위
    """
    query = select(TbCepNotificationLog)

    # 텍스트 검색
    if q:
        search_pattern = f"%{q}%"
        query = query.where(
            (TbCepNotificationLog.reason.ilike(search_pattern))
            | (TbCepNotificationLog.payload.astext.ilike(search_pattern))
        )

    # 규칙 필터
    if rule_id:
        try:
            rule_uuid = uuid.UUID(rule_id)
            query = query.where(TbCepNotificationLog.rule_id == rule_uuid)
        except ValueError:
            pass

    # 심각도 필터
    if severity:
        query = query.where(TbCepNotificationLog.payload["severity"].astext == severity)

    # ACK 상태 필터
    if acked is not None:
        query = query.where(TbCepNotificationLog.ack.is_(acked))

    # 날짜 범위
    if since:
        query = query.where(TbCepNotificationLog.fired_at >= since)
    if until:
        query = query.where(TbCepNotificationLog.fired_at <= until)

    # 정렬 및 제한
    query = query.order_by(desc(TbCepNotificationLog.fired_at)).limit(limit)

    events = session.exec(query).scalars().all()
    payload = [
        {
            "event_id": str(event.log_id),
            "fired_at": event.fired_at.isoformat(),
            "status": event.status,
            "rule_id": str(event.rule_id) if event.rule_id else None,
            "ack": event.ack,
            "ack_at": event.ack_at.isoformat() if event.ack_at else None,
        }
        for event in events
    ]

    return ResponseEnvelope.success(
        data={"events": payload, "count": len(events)}
    )


@router.get("/events/stats")
def get_event_stats(
    period: str = Query("24h"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    이벤트 통계

    - period: 1h, 6h, 24h, 7d
    """
    period_mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }

    lookback = period_mapping.get(period, timedelta(hours=24))
    cutoff_time = datetime.now(timezone.utc) - lookback

    # 전체 이벤트
    total_query = select(TbCepNotificationLog).where(
        TbCepNotificationLog.fired_at >= cutoff_time
    )
    total_events = session.exec(total_query).scalars().all()

    # 확인된 이벤트
    acked_count = sum(1 for e in total_events if e.ack)

    # 심각도별 분포
    severity_dist = {}
    for event in total_events:
        severity = event.payload.get("severity", "info") if event.payload else "info"
        severity_dist[severity] = severity_dist.get(severity, 0) + 1

    # 규칙별 분포
    rule_dist = {}
    for event in total_events:
        rule_id = str(event.rule_id) if event.rule_id else "unknown"
        rule_dist[rule_id] = rule_dist.get(rule_id, 0) + 1

    # ACK 시간 평균
    acked_events = [e for e in total_events if e.ack and e.ack_at]
    avg_time_to_ack = None
    if acked_events:
        total_seconds = sum(
            (e.ack_at - e.fired_at).total_seconds() for e in acked_events
        )
        avg_time_to_ack = int(total_seconds / len(acked_events))

    stats = {
        "total_count": len(total_events),
        "ack_count": acked_count,
        "ack_rate": acked_count / len(total_events) if total_events else 0,
        "avg_time_to_ack_seconds": avg_time_to_ack,
        "by_severity": severity_dist,
        "by_rule": rule_dist,
        "period": period,
    }

    return ResponseEnvelope.success(data={"stats": stats})


# ============================================================================
# Notification Channel Management
# ============================================================================


@router.post("/channels/test")
async def test_notification_channel(
    channel_type: str,
    config: dict = None,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Test a notification channel with sample data

    Args:
        channel_type: Type of channel (slack, email, sms, webhook, pagerduty)
        config: Channel configuration dict

    Returns:
        Test result with success status and message
    """
    if not config:
        raise HTTPException(status_code=400, detail="Config is required")

    try:
        from .notification_channels import NotificationChannelFactory, NotificationMessage

        channel = NotificationChannelFactory.create(channel_type, config)
        if not channel:
            raise HTTPException(
                status_code=400, detail=f"Unknown channel type: {channel_type}"
            )

        # Validate configuration
        if not channel.validate_config():
            raise HTTPException(
                status_code=400, detail="Invalid channel configuration"
            )

        # Create test message
        test_message = NotificationMessage(
            title="Test Notification from Tobit CEP",
            body="This is a test alert to verify your notification channel is working correctly.",
            recipients=config.get("recipients", []),
            metadata={
                "test": "true",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Send test notification
        result = await channel.send(test_message)

        return ResponseEnvelope.success(
            data={
                "success": result,
                "message": "Test notification sent successfully!"
                if result
                else "Failed to send test notification. Check configuration.",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error testing channel: {str(e)}"
        )


@router.get("/channels/types")
def get_channel_types() -> ResponseEnvelope:
    """
    Get available notification channel types and their configurations

    Returns:
        List of available channel types with required fields
    """
    channel_types = {
        "slack": {
            "display_name": "Slack",
            "description": "Send alerts to Slack channels via webhook",
            "icon": "📱",
            "required_fields": ["webhook_url"],
            "optional_fields": [],
        },
        "email": {
            "display_name": "Email",
            "description": "Send alerts via SMTP",
            "icon": "📧",
            "required_fields": [
                "smtp_host",
                "smtp_port",
                "from_email",
                "password",
            ],
            "optional_fields": ["use_tls"],
        },
        "sms": {
            "display_name": "SMS",
            "description": "Send alerts via Twilio",
            "icon": "📲",
            "required_fields": ["account_sid", "auth_token", "from_number"],
            "optional_fields": [],
        },
        "webhook": {
            "display_name": "Webhook",
            "description": "Send alerts to HTTP endpoints",
            "icon": "🔗",
            "required_fields": ["url"],
            "optional_fields": ["headers"],
        },
        "pagerduty": {
            "display_name": "PagerDuty",
            "description": "Create incidents in PagerDuty",
            "icon": "⚠️",
            "required_fields": ["integration_key"],
            "optional_fields": ["default_severity"],
        },
    }

    return ResponseEnvelope.success(data={"channel_types": channel_types})


# ============================================================================
# Monitoring Dashboard Endpoints
# ============================================================================


@router.get("/channels/status")
def get_channels_status(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """
    Get notification channels status with statistics

    Returns:
        - Each channel's status (active/inactive)
        - Recent send statistics
        - Failure rate and retry status
        - Last connection time
    """
    from datetime import timedelta

    notifications = list_notifications(session, active_only=False)

    channels_status = {}
    now = datetime.now(timezone.utc)
    lookback_hours = 24
    lookback = now - timedelta(hours=lookback_hours)

    for notification in notifications:
        channel_type = notification.channel

        if channel_type not in channels_status:
            channels_status[channel_type] = {
                "type": channel_type,
                "display_name": {
                    "slack": "Slack",
                    "email": "Email",
                    "sms": "SMS",
                    "webhook": "Webhook",
                    "pagerduty": "PagerDuty",
                }.get(channel_type, channel_type),
                "active": 0,
                "inactive": 0,
                "total_sent": 0,
                "total_failed": 0,
                "recent_logs": [],
                "last_sent_at": None,
            }

        if notification.is_active:
            channels_status[channel_type]["active"] += 1
        else:
            channels_status[channel_type]["inactive"] += 1

        # Get recent logs for this notification
        logs = list_notification_logs(session, str(notification.notification_id), limit=100)

        for log in logs:
            if log.fired_at >= lookback:
                channels_status[channel_type]["total_sent"] += 1
                if log.status != "success":
                    channels_status[channel_type]["total_failed"] += 1

                if not channels_status[channel_type]["last_sent_at"] or log.fired_at > channels_status[channel_type]["last_sent_at"]:
                    channels_status[channel_type]["last_sent_at"] = log.fired_at

                channels_status[channel_type]["recent_logs"].append({
                    "log_id": str(log.log_id),
                    "fired_at": log.fired_at.isoformat(),
                    "status": log.status,
                    "response_status": log.response_status,
                })

    # Calculate failure rate and add to each channel
    for channel_data in channels_status.values():
        if channel_data["total_sent"] > 0:
            channel_data["failure_rate"] = channel_data["total_failed"] / channel_data["total_sent"]
        else:
            channel_data["failure_rate"] = 0

        # Keep only last 10 logs
        channel_data["recent_logs"] = channel_data["recent_logs"][-10:]

    return ResponseEnvelope.success(
        data={
            "channels": list(channels_status.values()),
            "period_hours": lookback_hours,
        }
    )


@router.get("/stats/summary")
def get_stats_summary(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """
    Get overall CEP statistics summary

    Returns:
        - Total rule count
        - Today's execution count
        - Average execution time
        - Error rate
    """
    from datetime import timedelta

    # Total rules
    all_rules = list_rules(session)
    total_rules = len(all_rules)
    active_rules = sum(1 for rule in all_rules if rule.is_active)

    # Today's stats
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_logs_query = select(TbCepExecLog).where(
        TbCepExecLog.triggered_at >= today_start
    )
    today_logs = session.exec(today_logs_query).scalars().all()

    today_execution_count = len(today_logs)
    today_errors = sum(1 for log in today_logs if log.status == "fail")

    # Average execution time
    if today_logs:
        avg_duration = sum(log.duration_ms for log in today_logs) / len(today_logs)
        error_rate = today_errors / len(today_logs)
    else:
        avg_duration = 0
        error_rate = 0

    # Last 24 hours stats
    last_24h = now - timedelta(hours=24)
    logs_24h_query = select(TbCepExecLog).where(
        TbCepExecLog.triggered_at >= last_24h
    )
    logs_24h = session.exec(logs_24h_query).scalars().all()

    return ResponseEnvelope.success(
        data={
            "stats": {
                "total_rules": total_rules,
                "active_rules": active_rules,
                "inactive_rules": total_rules - active_rules,
                "today_execution_count": today_execution_count,
                "today_error_count": today_errors,
                "today_error_rate": error_rate,
                "today_avg_duration_ms": round(avg_duration, 2),
                "last_24h_execution_count": len(logs_24h),
                "timestamp": now.isoformat(),
            }
        }
    )


@router.get("/errors/timeline")
def get_errors_timeline(
    period: str = Query("24h"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get error timeline with hourly distribution

    Args:
        period: Time period to look back (1h, 6h, 24h, 7d)

    Returns:
        - Hourly error counts
        - Error type distribution
        - Recent error list
    """
    from datetime import timedelta

    period_mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }

    lookback = period_mapping.get(period, timedelta(hours=24))
    now = datetime.now(timezone.utc)
    cutoff_time = now - lookback

    # Get all error logs in period
    error_logs_query = select(TbCepExecLog).where(
        (TbCepExecLog.triggered_at >= cutoff_time) &
        (TbCepExecLog.status == "fail")
    ).order_by(TbCepExecLog.triggered_at.desc())

    error_logs = session.exec(error_logs_query).scalars().all()

    # Create hourly timeline
    timeline = {}
    current = cutoff_time.replace(minute=0, second=0, microsecond=0)
    while current <= now:
        timeline[current.isoformat()] = 0
        current += timedelta(hours=1)

    # Count errors by hour
    error_types = {}
    for log in error_logs:
        hour_key = log.triggered_at.replace(minute=0, second=0, microsecond=0).isoformat()
        if hour_key in timeline:
            timeline[hour_key] += 1

        # Categorize error type
        error_type = "unknown"
        if log.error_message:
            if "timeout" in log.error_message.lower():
                error_type = "timeout"
            elif "connection" in log.error_message.lower():
                error_type = "connection"
            elif "validation" in log.error_message.lower():
                error_type = "validation"
            elif "authentication" in log.error_message.lower():
                error_type = "authentication"
            else:
                error_type = "other"

        error_types[error_type] = error_types.get(error_type, 0) + 1

    # Get recent errors (last 10)
    recent_errors = []
    for log in error_logs[:10]:
        rule = get_rule(session, str(log.rule_id))
        recent_errors.append({
            "exec_id": str(log.exec_id),
            "rule_id": str(log.rule_id),
            "rule_name": rule.rule_name if rule else "Unknown",
            "triggered_at": log.triggered_at.isoformat(),
            "error_message": log.error_message,
            "duration_ms": log.duration_ms,
        })

    return ResponseEnvelope.success(
        data={
            "timeline": [
                {"timestamp": k, "error_count": v}
                for k, v in sorted(timeline.items())
            ],
            "error_distribution": error_types,
            "recent_errors": recent_errors,
            "period": period,
            "total_errors": len(error_logs),
        }
    )
