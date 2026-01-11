"""
Simple webhook notification engine for metric polling.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, select

from core.config import get_settings
from core.db import get_session_context
from .crud import (
    get_rule,
    insert_notification_log,
    list_metric_poll_snapshots,
    list_notifications,
    summarize_events,
)
from .event_broadcaster import event_broadcaster
from .models import TbCepNotification, TbCepNotificationLog

PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
METADATA_HOSTS = {"169.254.169.254"}
MAX_SNAPSHOTS = 20
HTTP_TIMEOUT = 3.0
MAX_RESPONSE_BODY = 1024


def _ensure_webhook_allowed(url: str) -> None:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid webhook URL")
    lower_host = host.lower()
    if lower_host in METADATA_HOSTS:
        raise ValueError("Metadata endpoints are blocked")
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise ValueError("Unable to resolve webhook host") from exc
    for info in infos:
        addr = info[4][0]
        try:
            ip_addr = ipaddress.ip_address(addr)
        except ValueError:
            continue
        for network in PRIVATE_NETWORKS:
            if ip_addr in network:
                raise ValueError(f"Webhook host resolves to private address: {ip_addr}")


def _value_satisfies(value: Any, op: str, threshold: float) -> bool:
    try:
        actual = float(value)
    except (TypeError, ValueError):
        return False
    match op:
        case ">":
            return actual > threshold
        case ">=":
            return actual >= threshold
        case "<":
            return actual < threshold
        case "<=":
            return actual <= threshold
        case "==":
            return actual == threshold
        case "=":
            return actual == threshold
        case _:
            return False


def _build_payload(notification: TbCepNotification, trigger: Dict[str, Any], snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    latest = snapshots[0]
    summary = {
        "window_minutes": trigger.get("window_minutes"),
        "latest_tick_at": latest.get("tick_at"),
        "matched_count": latest.get("matched_count"),
        "fail_count": latest.get("fail_count"),
        "instance_id": latest.get("instance_id"),
    }
    return {
        "notification": {
            "id": str(notification.notification_id),
            "name": notification.name,
        },
        "trigger": trigger,
        "summary": summary,
        "snapshots": snapshots,
    }


def _serialize_snapshots(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    safe: List[Dict[str, Any]] = []
    for snapshot in snapshots[:MAX_SNAPSHOTS]:
        safe.append(
            {
                "tick_at": snapshot.get("tick_at"),
                "matched_count": snapshot.get("matched_count"),
                "fail_count": snapshot.get("fail_count"),
                "rule_count": snapshot.get("rule_count"),
                "instance_id": snapshot.get("instance_id"),
            }
        )
    return safe


def run_once() -> None:
    settings = get_settings()
    if not settings.cep_enable_notifications:
        return
    now = datetime.utcnow()
    with get_session_context() as session:
        notifications = list_notifications(session)
        for notification in notifications:
            _evaluate_notification(session, notification, now)


def _evaluate_notification(session, notification: TbCepNotification, now: datetime) -> None:
    if notification.channel != "webhook":
        return
    trigger = notification.trigger or {}
    if trigger.get("type") != "snapshot_threshold":
        return
    window_minutes = int(trigger.get("window_minutes") or 5)
    snapshot_models = list_metric_poll_snapshots(session, limit=MAX_SNAPSHOTS, since_minutes=window_minutes)
    if not snapshot_models:
        return
    snapshots = [snapshot.model_dump() for snapshot in snapshot_models]
    if not snapshots:
        return
    field = trigger.get("field")
    op = trigger.get("op", ">=")
    threshold_raw = trigger.get("value")
    try:
        threshold = float(threshold_raw)
    except (TypeError, ValueError):
        return
    if not any(_value_satisfies(snapshot.get(field), op, threshold) for snapshot in snapshots):
        return
    dedup_key = ":".join(
        [
            str(notification.notification_id),
            trigger.get("type", ""),
            field or "",
            op,
            str(threshold),
        ]
    )
    policy = notification.policy or {}
    cooldown = int(policy.get("cooldown_seconds") or 300)
    max_per_hour = int(policy.get("max_per_hour") or 20)
    reason = None
    if _is_within_cooldown(session, notification.notification_id, dedup_key, now, cooldown):
        reason = f"cooldown {cooldown}s"
        _log_notification(session, notification, "skipped", reason, dedup_key, trigger, snapshots)
        return
    if _exceeds_rate_limit(session, notification.notification_id, now, max_per_hour):
        reason = f"rate limit ({max_per_hour}/h)"
        _log_notification(session, notification, "skipped", reason, dedup_key, trigger, snapshots)
        return
    payload = _build_payload(notification, trigger, _serialize_snapshots(snapshots))
    headers = notification.headers or {}
    try:
        _ensure_webhook_allowed(notification.webhook_url)
        response = _send_webhook(notification.webhook_url, headers, payload)
        _log_notification(
            session,
            notification,
            "sent",
            "webhook sent",
            dedup_key,
            trigger,
            snapshots,
            response.status_code,
            response.text[:MAX_RESPONSE_BODY],
        )
    except Exception as exc:
        _log_notification(
            session,
            notification,
            "fail",
            str(exc),
            dedup_key,
            trigger,
            snapshots,
        )


def _is_within_cooldown(
    session,
    notification_id: uuid.UUID,
    dedup_key: str,
    now: datetime,
    cooldown_seconds: int,
) -> bool:
    if cooldown_seconds <= 0:
        return False
    cutoff = now - timedelta(seconds=cooldown_seconds)
    query = (
        select(TbCepNotificationLog)
        .where(TbCepNotificationLog.notification_id == notification_id)
        .where(TbCepNotificationLog.dedup_key == dedup_key)
        .where(TbCepNotificationLog.fired_at >= cutoff)
        .order_by(desc(TbCepNotificationLog.fired_at))
        .limit(1)
    )
    recent = session.exec(query).first()
    return recent is not None


def _exceeds_rate_limit(session, notification_id: uuid.UUID, now: datetime, max_per_hour: int) -> bool:
    if max_per_hour <= 0:
        return False
    cutoff = now - timedelta(hours=1)
    count_query = (
        select(func.count())
        .where(TbCepNotificationLog.notification_id == notification_id)
        .where(TbCepNotificationLog.status == "sent")
        .where(TbCepNotificationLog.fired_at >= cutoff)
    )
    count = session.exec(count_query).scalar_one_or_none() or 0
    return count >= max_per_hour


def _send_webhook(url: str, headers: dict[str, Any], payload: dict[str, Any]) -> httpx.Response:
    headers_clean = {str(key): str(value) for key, value in (headers or {}).items()}
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.post(url, headers=headers_clean, json=payload)
        response.raise_for_status()
        return response


def _log_notification(
    session,
    notification: TbCepNotification,
    status: str,
    reason: str,
    dedup_key: str,
    trigger: dict[str, Any],
    snapshots: List[Dict[str, Any]],
    response_status: int | None = None,
    response_body: str | None = None,
) -> None:
    payload = {
        "notification": {
            "id": str(notification.notification_id),
            "name": notification.name,
        },
        "trigger": trigger,
        "snapshots": _serialize_snapshots(snapshots),
    }
    log_payload = {
        "notification_id": notification.notification_id,
        "status": status,
        "reason": reason,
        "payload": payload,
        "response_status": response_status,
        "response_body": response_body,
        "dedup_key": dedup_key,
    }
    saved = insert_notification_log(session, log_payload)
    summary = summarize_events(session)
    rule = get_rule(session, str(notification.rule_id)) if notification.rule_id else None
    event_broadcaster.publish(
        "new_event",
        {
            "event_id": str(saved.log_id),
            "triggered_at": saved.fired_at.isoformat(),
            "status": saved.status,
            "summary": saved.reason or payload.get("summary") or "Event triggered",
            "severity": trigger.get("severity") or payload.get("severity") or "info",
            "ack": saved.ack,
            "ack_at": saved.ack_at.isoformat() if saved.ack_at else None,
            "rule_id": str(notification.rule_id) if notification.rule_id else None,
            "rule_name": rule.rule_name if rule else None,
            "notification_id": str(notification.notification_id),
        },
    )
    event_broadcaster.publish(
        "summary",
        {
            "unacked_count": summary["unacked_count"],
            "by_severity": summary["by_severity"],
        },
    )
