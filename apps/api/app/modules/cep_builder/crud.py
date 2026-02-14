from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlmodel import Session

from .models import (
    TbCepExecLog,
    TbCepMetricPollSnapshot,
    TbCepNotification,
    TbCepNotificationLog,
    TbCepRule,
)
from .schemas import CepRuleCreate, CepRuleUpdate


def list_rules(
    session: Session,
    trigger_type: str | None = None,
    active_only: bool = False,
    tenant_id: str | None = None,
) -> list[TbCepRule]:
    """
    List CEP rules with optional filtering.

    Performance: Uses indexes on (is_active, updated_at DESC) and (trigger_type)
    """
    query = select(TbCepRule)
    if tenant_id:
        query = query.where(
            (TbCepRule.tenant_id == tenant_id) | (TbCepRule.tenant_id.is_(None))
        )
    if active_only:
        query = query.where(TbCepRule.is_active.is_(True))
    if trigger_type:
        query = query.where(TbCepRule.trigger_type == trigger_type)
    query = query.order_by(TbCepRule.updated_at.desc())
    return session.exec(query).scalars().all()


def get_rule(session: Session, rule_id: str) -> TbCepRule | None:
    return session.get(TbCepRule, rule_id)


def create_rule(
    session: Session,
    payload: CepRuleCreate,
    tenant_id: str | None = None,
) -> TbCepRule:
    rule = TbCepRule(
        rule_name=payload.rule_name,
        trigger_type=payload.trigger_type,
        trigger_spec=payload.trigger_spec,
        action_spec=payload.action_spec,
        is_active=payload.is_active,
        tenant_id=tenant_id,
        created_by=payload.created_by,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


def update_rule(session: Session, rule: TbCepRule, payload: CepRuleUpdate) -> TbCepRule:
    for attr, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, attr, value)
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


def record_exec_log(
    session: Session,
    rule_id: str,
    status: str,
    duration_ms: int,
    references: dict[str, object],
    executed_by: str,
    error_message: str | None = None,
) -> TbCepExecLog:
    log = TbCepExecLog(
        rule_id=rule_id,
        status=status,
        duration_ms=duration_ms,
        references=references,
        error_message=error_message,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def list_exec_logs(
    session: Session, rule_id: str, limit: int = 50, status: str | None = None
) -> list[TbCepExecLog]:
    """
    List execution logs for a specific rule.

    Performance: Uses composite index (rule_id, triggered_at DESC)
    """
    query = (
        select(TbCepExecLog)
        .where(TbCepExecLog.rule_id == rule_id)
    )
    if status:
        query = query.where(TbCepExecLog.status == status)
    query = query.order_by(desc(TbCepExecLog.triggered_at)).limit(limit)
    return session.exec(query).scalars().all()


def insert_metric_poll_snapshot(
    session: Session,
    payload: dict[str, Any],
) -> TbCepMetricPollSnapshot:
    snapshot = TbCepMetricPollSnapshot(**payload)
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def list_metric_poll_snapshots(
    session: Session,
    limit: int = 200,
    since_minutes: int | None = None,
) -> list[TbCepMetricPollSnapshot]:
    query = select(TbCepMetricPollSnapshot).order_by(
        desc(TbCepMetricPollSnapshot.tick_at)
    )
    if since_minutes:
        cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
        query = query.where(TbCepMetricPollSnapshot.tick_at >= cutoff)
    query = query.limit(limit)
    return session.exec(query).scalars().all()


def list_notifications(
    session: Session, active_only: bool = True, channel: str | None = None, limit: int = 500
) -> list[TbCepNotification]:
    """
    List notifications with optional filtering.

    Performance: Uses indexes on (is_active, created_at DESC), (channel), and (rule_id)
    """
    query = select(TbCepNotification)
    if active_only:
        query = query.where(TbCepNotification.is_active.is_(True))
    if channel:
        query = query.where(TbCepNotification.channel == channel)
    query = query.order_by(desc(TbCepNotification.created_at)).limit(limit)
    return session.exec(query).scalars().all()


def get_notification(
    session: Session, notification_id: str
) -> TbCepNotification | None:
    return session.get(TbCepNotification, notification_id)


def create_notification(session: Session, payload: dict[str, Any]) -> TbCepNotification:
    notification = TbCepNotification(**payload)
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def update_notification(
    session: Session, notification: TbCepNotification, payload: dict[str, Any]
) -> TbCepNotification:
    for key, value in payload.items():
        setattr(notification, key, value)
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def get_exec_log(session: Session, exec_id: str) -> TbCepExecLog | None:
    return session.get(TbCepExecLog, exec_id)


def find_exec_log_by_simulation(
    session: Session, simulation_id: str
) -> TbCepExecLog | None:
    query = select(TbCepExecLog).where(
        TbCepExecLog.references["simulation_id"].astext == simulation_id
    )
    return session.exec(query).scalars().first()


def insert_notification_log(
    session: Session, payload: dict[str, Any]
) -> TbCepNotificationLog:
    log = TbCepNotificationLog(**payload)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def list_notification_logs(
    session: Session, notification_id: str, limit: int = 200, status: str | None = None
) -> list[TbCepNotificationLog]:
    """
    List notification logs for a specific notification.

    Performance: Uses composite index (notification_id, ack) and status index
    """
    query = (
        select(TbCepNotificationLog)
        .where(TbCepNotificationLog.notification_id == notification_id)
    )
    if status:
        query = query.where(TbCepNotificationLog.status == status)
    query = query.order_by(desc(TbCepNotificationLog.fired_at)).limit(limit)
    return session.exec(query).scalars().all()


def list_events(
    session: Session,
    *,
    acked: bool | None = None,
    rule_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
    tenant_id: str | None = None,
) -> list[tuple[TbCepNotificationLog, TbCepNotification, TbCepRule | None]]:
    """
    List events with optional filtering.

    Performance: Optimized JOIN with indexes on fired_at DESC and composite indexes
    Avoids N+1 by joining all tables at once instead of lazy loading

    Security: Filters by tenant_id to ensure multi-tenant isolation
    """
    query = (
        select(TbCepNotificationLog, TbCepNotification, TbCepRule)
        .select_from(TbCepNotificationLog)
        .join(
            TbCepNotification,
            TbCepNotificationLog.notification_id == TbCepNotification.notification_id,
        )
        .outerjoin(TbCepRule, TbCepRule.rule_id == TbCepNotification.rule_id)
    )

    # Apply filters in order of selectivity (most selective first)
    # Tenant isolation - filter by tenant or include global rules (tenant_id is NULL)
    if tenant_id:
        query = query.where(
            (TbCepRule.tenant_id == tenant_id) | (TbCepRule.tenant_id.is_(None))
        )
    if acked is not None:
        query = query.where(TbCepNotificationLog.ack.is_(acked))
    if rule_id:
        query = query.where(TbCepNotification.rule_id == rule_id)
    if since:
        query = query.where(TbCepNotificationLog.fired_at >= since)
    if until:
        query = query.where(TbCepNotificationLog.fired_at <= until)

    query = query.order_by(desc(TbCepNotificationLog.fired_at)).limit(limit).offset(offset)
    return session.exec(query).all()


def get_event(
    session: Session,
    event_id: str,
) -> tuple[TbCepNotificationLog, TbCepNotification, TbCepRule | None] | None:
    query = (
        select(TbCepNotificationLog, TbCepNotification, TbCepRule)
        .select_from(TbCepNotificationLog)
        .join(
            TbCepNotification,
            TbCepNotificationLog.notification_id == TbCepNotification.notification_id,
        )
        .outerjoin(TbCepRule, TbCepRule.rule_id == TbCepNotification.rule_id)
        .where(TbCepNotificationLog.log_id == event_id)
    )
    return session.exec(query).first()


def acknowledge_event(
    session: Session,
    log: TbCepNotificationLog,
    *,
    ack_by: str | None = None,
) -> TbCepNotificationLog:
    log.ack = True
    log.ack_at = datetime.utcnow()
    log.ack_by = ack_by
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def get_latest_exec_log_for_rule(
    session: Session,
    *,
    rule_id: str,
    before: datetime | None = None,
) -> TbCepExecLog | None:
    query = select(TbCepExecLog).where(TbCepExecLog.rule_id == rule_id)
    if before:
        query = query.where(TbCepExecLog.triggered_at <= before)
    query = query.order_by(desc(TbCepExecLog.triggered_at)).limit(1)
    return session.exec(query).scalars().first()


def summarize_events(
    session: Session,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """
    Summarize events by ACK status and severity.

    Performance: Uses index on (ack) for unacked count and aggregates in single query

    Security: Filters by tenant_id to ensure multi-tenant isolation
    """
    # Build base query with optional tenant filter
    if tenant_id:
        unacked_query = (
            select(func.count())
            .select_from(TbCepNotificationLog)
            .join(
                TbCepNotification,
                TbCepNotificationLog.notification_id == TbCepNotification.notification_id,
            )
            .outerjoin(TbCepRule, TbCepRule.rule_id == TbCepNotification.rule_id)
            .where(TbCepNotificationLog.ack.is_(False))
            .where(
                (TbCepRule.tenant_id == tenant_id) | (TbCepRule.tenant_id.is_(None))
            )
        )
    else:
        unacked_query = (
            select(func.count())
            .select_from(TbCepNotificationLog)
            .where(TbCepNotificationLog.ack.is_(False))
        )

    unacked = session.exec(unacked_query).one()[0]

    severity_expr = func.coalesce(TbCepNotification.trigger["severity"].astext, "info")
    severity_query = (
        select(severity_expr.label("severity"), func.count())
        .select_from(TbCepNotificationLog)
        .join(
            TbCepNotification,
            TbCepNotificationLog.notification_id == TbCepNotification.notification_id,
        )
        .outerjoin(TbCepRule, TbCepRule.rule_id == TbCepNotification.rule_id)
    )

    if tenant_id:
        severity_query = severity_query.where(
            (TbCepRule.tenant_id == tenant_id) | (TbCepRule.tenant_id.is_(None))
        )

    severity_query = severity_query.group_by(severity_expr)
    rows = session.exec(severity_query).all()

    by_severity: dict[str, int] = {}
    for severity, count in rows:
        by_severity[str(severity)] = int(count)

    return {"unacked_count": int(unacked or 0), "by_severity": by_severity}
