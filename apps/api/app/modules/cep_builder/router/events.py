"""Event management and streaming endpoints for CEP Builder."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.common import ResponseEnvelope
from sqlalchemy import desc, select
from sqlmodel import Session
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

from ..crud import (
    acknowledge_event,
    get_event,
    get_exec_log,
    get_latest_exec_log_for_rule,
    list_events,
    summarize_events,
)
from ..event_broadcaster import event_broadcaster
from ..models import TbCepExecLog, TbCepNotificationLog
from ..schemas import (
    CepEventDetail,
    CepEventRead,
    CepEventSummary,
    CepExecLogRead,
    CepNotificationLogRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cep/events", tags=["cep-events"])


def _extract_severity(payload: dict[str, Any], trigger: dict[str, Any]) -> str:
    """Extract severity from payload or trigger spec."""
    severity = payload.get("severity") or trigger.get("severity")
    if isinstance(severity, str) and severity.strip():
        return severity
    return "info"


def _build_summary(reason: str | None, payload: dict[str, Any]) -> str:
    """Build event summary from reason or payload."""
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
    """Extract condition and value from payload."""
    condition = payload.get("condition_evaluated")
    extracted = payload.get("extracted_value")
    return (condition if isinstance(condition, bool) else None, extracted)


def _truncate_json(value: Any | None, limit: int = 32768) -> str | None:
    """Truncate JSON representation of a value."""
    if value is None:
        return None
    try:
        text = json.dumps(value, default=str)
    except Exception:
        return str(value)
    return text if len(text) <= limit else text[:limit] + "…"


@router.get("")
def list_events_endpoint(
    acked: bool | None = Query(None),
    severity: str | None = Query(None),
    rule_id: str | None = Query(None),
    since: datetime | None = Query(None),
    until: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ResponseEnvelope:
    """List CEP events with optional filters. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    rows = list_events(
        session,
        acked=acked,
        rule_id=rule_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
        tenant_id=tenant_id,
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


@router.get("/summary")
def event_summary_endpoint(
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ResponseEnvelope:
    """Get event summary (counts by severity and ack status). Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    summary = summarize_events(session, tenant_id=tenant_id)
    payload = CepEventSummary(**summary).model_dump()
    return ResponseEnvelope.success(data={"summary": payload})


@router.get("/stream")
async def event_stream(
    request: Request,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> EventSourceResponse:
    """
    Real-time event streaming via SSE (Server-Sent Events).

    Sends:
    1. Initial summary of unacked events
    2. Historical events from last hour (for reconnection recovery)
    3. Live events as they occur
    4. Heartbeat pings every second
    """
    await event_broadcaster.ensure_redis_listener()

    tenant_id = getattr(current_user, "tenant_id", None)
    summary = summarize_events(session, tenant_id=tenant_id)

    async def event_generator():
        try:
            # Send initial summary
            yield {"event": "summary", "data": json.dumps(summary)}

            # Load recent events for reconnection recovery
            LOOKBACK_MINUTES = 60
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
            recent_events = session.exec(
                select(TbCepNotificationLog)
                .where(TbCepNotificationLog.fired_at >= cutoff_time)
                .order_by(TbCepNotificationLog.fired_at.asc())
                .limit(100)
            ).scalars().all()

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

            # Subscribe to live events
            queue = event_broadcaster.subscribe()
            try:
                while True:
                    if await request.is_disconnected():
                        break

                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=1.0)
                        yield {
                            "event": message["type"],
                            "data": json.dumps(message["data"]),
                        }
                    except asyncio.TimeoutError:
                        if await request.is_disconnected():
                            break
                        yield {"event": "ping", "data": "{}"}
            except (asyncio.CancelledError, GeneratorExit):
                yield {"event": "shutdown", "data": "{}"}
                raise
            finally:
                event_broadcaster.unsubscribe(queue)
        except Exception as e:
            logger.error(f"Event stream error: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/{event_id}")
def get_event_endpoint(
    event_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get detailed information for a specific event."""
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


@router.post("/{event_id}/ack")
def ack_event_endpoint(
    event_id: str,
    ack_by: str | None = Query(None),
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ResponseEnvelope:
    """Acknowledge (mark as read) a specific event. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    log = session.get(TbCepNotificationLog, event_id)
    if not log:
        raise HTTPException(status_code=404, detail="Event not found")
    updated = acknowledge_event(session, log, ack_by=ack_by)
    payload = CepNotificationLogRead.from_orm(updated).model_dump()
    summary = summarize_events(session, tenant_id=tenant_id)
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


@router.get("/run")
def get_run_endpoint(
    exec_log_id: str | None = Query(None),
    simulation_id: str | None = Query(None),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get execution run details by exec_log_id or simulation_id."""
    from ..crud import find_exec_log_by_simulation

    if not exec_log_id and not simulation_id:
        return ResponseEnvelope.success(
            data={
                "run": {
                    "found": False,
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


@router.get("/search")
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
    Advanced event search with full-text and filtering.

    - q: Full-text search in rule names, summaries, and payloads
    - rule_id: Filter by specific rule
    - severity: CRITICAL, HIGH, MEDIUM, LOW
    - acked: Filter by acknowledgment status
    - since/until: Date range filtering
    """
    query = select(TbCepNotificationLog)

    if q:
        search_pattern = f"%{q}%"
        query = query.where(
            (TbCepNotificationLog.reason.ilike(search_pattern))
            | (TbCepNotificationLog.payload.astext.ilike(search_pattern))
        )

    if rule_id:
        try:
            rule_uuid = uuid.UUID(rule_id)
            query = query.where(TbCepNotificationLog.rule_id == rule_uuid)
        except ValueError:
            pass

    if severity:
        query = query.where(TbCepNotificationLog.payload["severity"].astext == severity)

    if acked is not None:
        query = query.where(TbCepNotificationLog.ack.is_(acked))

    if since:
        query = query.where(TbCepNotificationLog.fired_at >= since)
    if until:
        query = query.where(TbCepNotificationLog.fired_at <= until)

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


@router.get("/stats")
def get_event_stats(
    period: str = Query("24h"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Get event statistics for a time period.

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

    total_query = select(TbCepNotificationLog).where(
        TbCepNotificationLog.fired_at >= cutoff_time
    )
    total_events = session.exec(total_query).scalars().all()

    acked_count = sum(1 for e in total_events if e.ack)

    severity_dist = {}
    for event in total_events:
        severity = event.payload.get("severity", "info") if event.payload else "info"
        severity_dist[severity] = severity_dist.get(severity, 0) + 1

    rule_dist = {}
    for event in total_events:
        rule_id = str(event.rule_id) if event.rule_id else "unknown"
        rule_dist[rule_id] = rule_dist.get(rule_id, 0) + 1

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
