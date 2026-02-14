"""Scheduler status and monitoring endpoints for CEP Builder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core.db import get_session
from fastapi import APIRouter, Depends, Query
from schemas.common import ResponseEnvelope
from sqlalchemy import desc, select
from sqlmodel import Session

from ..crud import list_metric_poll_snapshots
from ..models import TbCepMetricPollSnapshot, TbCepSchedulerState
from ..scheduler import (
    get_metric_poll_stats,
    get_metric_polling_telemetry,
    get_scheduler_instance_id,
    is_scheduler_leader,
)

router = APIRouter(prefix="/cep/scheduler", tags=["cep-scheduler"])


def _snapshot_summary(
    snapshot: TbCepMetricPollSnapshot | None,
) -> dict[str, Any] | None:
    """Convert snapshot model to summary dict."""
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


@router.get("/status")
def scheduler_status(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """Get overall scheduler status and leader information."""
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


@router.get("/metric-polling")
def metric_polling_telemetry() -> ResponseEnvelope:
    """Get metric polling telemetry data."""
    telemetry = get_metric_polling_telemetry()
    return ResponseEnvelope.success(data={"telemetry": telemetry})


@router.get("/metric-polling/snapshots")
def metric_polling_snapshots(
    limit: int = Query(200, ge=1, le=500),
    since_minutes: int | None = Query(None, ge=1),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get metric polling snapshots."""
    snapshots = list_metric_poll_snapshots(
        session, limit=limit, since_minutes=since_minutes
    )
    payload = [_snapshot_summary(snapshot) for snapshot in snapshots]
    return ResponseEnvelope.success(data={"snapshots": payload})


@router.get("/metric-polling/snapshots/latest")
def metric_polling_snapshots_latest(
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get the latest metric polling snapshot."""
    snapshots = list_metric_poll_snapshots(session, limit=1)
    latest = _snapshot_summary(snapshots[0]) if snapshots else None
    return ResponseEnvelope.success(data={"snapshot": latest})


@router.get("/instances")
def scheduler_instances(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """Get all scheduler instances."""
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
