from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.config import get_settings
from core.db import engine, get_session_context
from croniter import CroniterBadCronError, croniter
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from . import notification_engine
from .crud import insert_metric_poll_snapshot, list_rules
from .executor import manual_trigger
from .models import TbCepRule

logger = logging.getLogger(__name__)
_next_run: dict[str, datetime] = {}
_scheduler_task: asyncio.Task | None = None
_follower_task: asyncio.Task | None = None
_metric_poll_task: asyncio.Task | None = None
_metric_poll_semaphore: asyncio.Semaphore | None = None
_notification_task: asyncio.Task | None = None
_metric_last_polled: dict[str, datetime] = {}
_metric_telemetry: dict[str, Any] = {
    "metric_polling_enabled": False,
    "metric_poll_last_tick_at": None,
    "metric_poll_last_tick_duration_ms": None,
    "metric_poll_last_tick_rule_count": 0,
    "metric_poll_last_tick_evaluated_count": 0,
    "metric_poll_last_tick_matched_count": 0,
    "metric_poll_last_tick_skipped_count": 0,
    "metric_poll_last_tick_fail_count": 0,
    "metric_poll_last_error": None,
    "metric_poll_recent_matches": [],
    "metric_poll_recent_failures": [],
}
_metric_poll_snapshot_last_written: datetime | None = None
_is_leader: bool = False
_lock_key: int = 987654321
_lock_conn: Optional[Connection] = None
_last_heartbeat: datetime | None = None
HEARTBEAT_INTERVAL = 10
FOLLOWER_INTERVAL = 25
INSTANCE_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"


def _compute_next_run(rule: TbCepRule, now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    spec = rule.trigger_spec or {}
    interval = spec.get("interval_seconds")
    cron_expr = spec.get("cron")
    if cron_expr:
        try:
            return croniter(cron_expr, now).get_next(datetime)
        except CroniterBadCronError as exc:
            logger.warning("Invalid cron expression for CEP rule %s: %s", rule.rule_id, exc)
    if interval:
        try:
            seconds = int(interval)
            return now + timedelta(seconds=seconds)
        except (TypeError, ValueError):
            pass
    return now + timedelta(minutes=5)


async def _scheduler_loop() -> None:
    while True:
        try:
            with get_session_context() as session:
                rules = list_rules(session, trigger_type="schedule")
                now = datetime.utcnow()
                for rule in rules:
                    if not rule.is_active:
                        continue
                    next_run = _next_run.get(str(rule.rule_id))
                    if not next_run:
                        _next_run[str(rule.rule_id)] = _compute_next_run(rule, now)
                        continue
                    if now >= next_run:
                        await asyncio.to_thread(
                            manual_trigger,
                            rule,
                            {},
                            "cep-scheduler",
                        )
                        _next_run[str(rule.rule_id)] = _compute_next_run(rule, now)
        except Exception:
            logger.exception("CEP scheduler loop failure")
        finally:
            _maybe_heartbeat()
        await asyncio.sleep(5)


def start_scheduler() -> None:
    global _scheduler_task
    settings = get_settings()
    if not settings.ops_enable_cep_scheduler:
        logger.info("[CEP] Scheduler disabled by environment variable")
        return
    logger.info("[CEP] Scheduler enabled (OPS_ENABLE_CEP_SCHEDULER=true)")
    if _scheduler_task and not _scheduler_task.done():
        return
    if not _acquire_leader_lock():
        logger.info("CEP scheduler leader not acquired; scheduler disabled in this process")
        _ensure_state_record(False, notes="leader unavailable")
        _ensure_follower_loop()
        return
    logger.info("CEP scheduler leader acquired")
    _ensure_state_record(True, notes="scheduler started")
    global _last_heartbeat
    _last_heartbeat = datetime.now(timezone.utc)
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    _start_metric_poll_loop(settings)
    _start_notification_loop(settings)


def stop_scheduler() -> None:
    global _scheduler_task
    _release_leader_lock()
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
    _stop_metric_poll_loop()
    _stop_notification_loop()
    _stop_follower_loop()


def _acquire_leader_lock() -> bool:
    global _is_leader, _lock_conn
    if _is_leader and _lock_conn:
        return True
    conn = engine.connect()
    result = conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": _lock_key})
    acquired = bool(result.scalar())
    if acquired:
        _is_leader = True
        _lock_conn = conn
        return True
    conn.close()
    return False


def _release_leader_lock() -> None:
    global _is_leader, _lock_conn
    if not _is_leader or not _lock_conn:
        _is_leader = False
        return
    try:
        _lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _lock_key})
    finally:
        _lock_conn.close()
        _lock_conn = None
        _is_leader = False


def _ensure_state_record(is_leader: bool, notes: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    params = {
        "instance_id": INSTANCE_ID,
        "is_leader": is_leader,
        "now": now,
        "notes": notes,
    }
    sql = text(
        """
        INSERT INTO tb_cep_scheduler_state
            (instance_id, is_leader, last_heartbeat_at, started_at, updated_at, notes)
        VALUES
            (:instance_id, :is_leader, :now, :now, :now, :notes)
        ON CONFLICT (instance_id) DO UPDATE
        SET
            is_leader = EXCLUDED.is_leader,
            last_heartbeat_at = EXCLUDED.last_heartbeat_at,
            updated_at = EXCLUDED.updated_at,
            notes = COALESCE(:notes, tb_cep_scheduler_state.notes)
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, params)


def _maybe_heartbeat() -> None:
    global _last_heartbeat
    now = datetime.now(timezone.utc)
    if _last_heartbeat and (now - _last_heartbeat).total_seconds() < HEARTBEAT_INTERVAL:
        return
    _last_heartbeat = now
    try:
        _ensure_state_record(_is_leader, notes="heartbeat")
    except Exception:
        logger.exception("Failed to record CEP scheduler heartbeat")


def _ensure_follower_loop() -> None:
    global _follower_task
    if _follower_task and not _follower_task.done():
        return
    _follower_task = asyncio.create_task(_follower_heartbeat_loop())


def _stop_follower_loop() -> None:
    global _follower_task
    if _follower_task:
        _follower_task.cancel()
        _follower_task = None


def _start_metric_poll_loop(settings: Any) -> None:
    global _metric_poll_task, _metric_poll_semaphore
    if not settings.cep_enable_metric_polling:
        return
    if _metric_poll_task and not _metric_poll_task.done():
        return
    concurrency = max(1, settings.cep_metric_poll_concurrency)
    _metric_poll_semaphore = asyncio.Semaphore(concurrency)
    _metric_poll_task = asyncio.create_task(_metric_poll_loop())


def _start_notification_loop(settings: Any) -> None:
    global _notification_task
    if not settings.cep_enable_notifications:
        return
    if _notification_task and not _notification_task.done():
        return
    _notification_task = asyncio.create_task(_notification_loop())


def _stop_notification_loop() -> None:
    global _notification_task
    if _notification_task:
        _notification_task.cancel()
        _notification_task = None


def _stop_metric_poll_loop() -> None:
    global _metric_poll_task, _metric_poll_semaphore
    if _metric_poll_task:
        _metric_poll_task.cancel()
        _metric_poll_task = None
    _metric_poll_semaphore = None


async def _run_metric_rule(rule: TbCepRule) -> dict[str, Any]:
    sem = _metric_poll_semaphore
    timestamp = datetime.utcnow()
    result: dict[str, Any] = {
        "rule_id": str(rule.rule_id),
        "rule_name": rule.rule_name,
        "timestamp": timestamp,
        "status": "unknown",
        "matched": False,
        "actual_value": None,
        "threshold": None,
        "op": None,
        "error": None,
    }
    if sem is None:
        return result
    async with sem:
        try:
            execution = await asyncio.to_thread(manual_trigger, rule, None, "cep-metric-poll")
            trigger_refs = (execution.get("references") or {}).get("trigger") or {}
            result["status"] = execution.get("status", "unknown")
            result["matched"] = bool(execution.get("condition_met"))
            result["actual_value"] = trigger_refs.get("actual_value")
            result["threshold"] = trigger_refs.get("threshold")
            result["op"] = trigger_refs.get("op")
            return result
        except HTTPException as exc:
            logger.warning("Metric rule %s failed: %s", rule.rule_id, exc.detail)
            result["status"] = "fail"
            result["error"] = str(exc.detail) if exc.detail is not None else str(exc)
            return result
        except Exception as exc:
            logger.exception("Metric rule %s encountered an unexpected error", rule.rule_id)
            result["status"] = "fail"
            result["error"] = str(exc)
            return result


async def _metric_poll_loop() -> None:
    global _metric_telemetry
    while True:
        settings = get_settings()
        interval = max(settings.cep_metric_poll_global_interval_seconds, 1)
        tick_start = datetime.utcnow()
        _metric_telemetry["metric_polling_enabled"] = settings.cep_enable_metric_polling
        try:
            if not settings.cep_enable_metric_polling or not is_scheduler_leader():
                _metric_telemetry["metric_poll_last_tick_at"] = None
                _metric_telemetry["metric_poll_last_tick_duration_ms"] = None
                _metric_telemetry["metric_poll_last_tick_rule_count"] = 0
                _metric_telemetry["metric_poll_last_tick_evaluated_count"] = 0
                _metric_telemetry["metric_poll_last_tick_matched_count"] = 0
                _metric_telemetry["metric_poll_last_tick_skipped_count"] = 0
                _metric_telemetry["metric_poll_last_tick_fail_count"] = 0
                _metric_telemetry["metric_poll_last_error"] = None
                continue
            now = datetime.utcnow()
            rules: list[TbCepRule] = []
            with get_session_context() as session:
                rules = list_rules(session, trigger_type="metric")
            tasks: list[asyncio.Task] = []
            rule_count = 0
            for rule in rules:
                if not rule.is_active:
                    continue
                spec = rule.trigger_spec or {}
                poll_interval = spec.get("poll_interval_seconds")
                try:
                    poll_secs = float(poll_interval) if poll_interval is not None else 0.0
                except (TypeError, ValueError):
                    poll_secs = 0.0
                last_polled = _metric_last_polled.get(str(rule.rule_id))
                if last_polled and (now - last_polled).total_seconds() < poll_secs:
                    continue
                _metric_last_polled[str(rule.rule_id)] = now
                rule_count += 1
                tasks.append(asyncio.create_task(_run_metric_rule(rule)))
            _metric_telemetry["metric_poll_last_tick_rule_count"] = rule_count
            _metric_telemetry["metric_poll_last_tick_evaluated_count"] = 0
            _metric_telemetry["metric_poll_last_tick_matched_count"] = 0
            _metric_telemetry["metric_poll_last_tick_skipped_count"] = 0
            _metric_telemetry["metric_poll_last_tick_fail_count"] = 0
            _metric_telemetry["metric_poll_last_error"] = None
            _metric_telemetry["metric_poll_recent_matches"] = _metric_telemetry["metric_poll_recent_matches"][:20]
            _metric_telemetry["metric_poll_recent_failures"] = _metric_telemetry["metric_poll_recent_failures"][:20]
            matches: list[dict[str, Any]] = []
            failures: list[dict[str, Any]] = []
            if tasks:
                results = await asyncio.gather(*tasks)
                evaluated = len(results)
                matched = 0
                skipped = 0
                last_error: str | None = None
                for entry in results:
                    if entry.get("matched"):
                        matched += 1
                        matches.append(
                            {
                                "rule_id": entry["rule_id"],
                                "rule_name": entry["rule_name"],
                                "matched_at": entry["timestamp"].isoformat(),
                                "actual_value": entry["actual_value"],
                                "threshold": entry["threshold"],
                                "op": entry["op"],
                            }
                        )
                    if entry.get("status") == "skipped":
                        skipped += 1
                    if entry.get("error"):
                        failures.append(
                            {
                                "rule_id": entry["rule_id"],
                                "rule_name": entry["rule_name"],
                                "failed_at": entry["timestamp"].isoformat(),
                                "error": entry["error"],
                            }
                        )
                        last_error = entry["error"]
                _metric_telemetry["metric_poll_last_tick_evaluated_count"] = evaluated
                _metric_telemetry["metric_poll_last_tick_matched_count"] = matched
                _metric_telemetry["metric_poll_last_tick_skipped_count"] = skipped
                _metric_telemetry["metric_poll_last_tick_fail_count"] = len(failures)
                _metric_telemetry["metric_poll_last_error"] = last_error
                _metric_telemetry["metric_poll_recent_matches"] = (
                    matches + _metric_telemetry["metric_poll_recent_matches"]
                )[:20]
                _metric_telemetry["metric_poll_recent_failures"] = (
                    failures + _metric_telemetry["metric_poll_recent_failures"]
                )[:20]
            tick_end = datetime.utcnow()
            _metric_telemetry["metric_poll_last_tick_at"] = tick_end
            _metric_telemetry["metric_poll_last_tick_duration_ms"] = int(
                (tick_end - tick_start).total_seconds() * 1000
            )
            _maybe_persist_metric_poll_snapshot(settings)
        except Exception:
            logger.exception("Metric polling loop failure")
            _metric_telemetry["metric_poll_last_error"] = "Metric polling loop failure"
        finally:
            await asyncio.sleep(interval)


async def _notification_loop() -> None:
    while True:
        settings = get_settings()
        interval = max(settings.cep_notification_interval_seconds, 1)
        try:
            if settings.cep_enable_notifications and is_scheduler_leader():
                await asyncio.to_thread(notification_engine.run_once)
        except Exception:
            logger.exception("Notification loop failure")
        finally:
            await asyncio.sleep(interval)


def _maybe_persist_metric_poll_snapshot(settings: Any) -> None:
    global _metric_poll_snapshot_last_written
    if not is_scheduler_leader():
        return
    interval = max(settings.cep_metric_poll_snapshot_interval_seconds, 1)
    now = datetime.utcnow()
    last = _metric_poll_snapshot_last_written
    if last and (now - last).total_seconds() < interval:
        return
    _metric_poll_snapshot_last_written = now
    telemetry = _metric_telemetry
    payload = {
        "instance_id": INSTANCE_ID,
        "is_leader": _is_leader,
        "tick_at": telemetry["metric_poll_last_tick_at"] or now,
        "tick_duration_ms": telemetry["metric_poll_last_tick_duration_ms"] or 0,
        "rule_count": telemetry["metric_poll_last_tick_rule_count"],
        "evaluated_count": telemetry["metric_poll_last_tick_evaluated_count"],
        "matched_count": telemetry["metric_poll_last_tick_matched_count"],
        "skipped_count": telemetry["metric_poll_last_tick_skipped_count"],
        "fail_count": telemetry["metric_poll_last_tick_fail_count"],
        "last_error": telemetry["metric_poll_last_error"],
        "recent_matches": list(telemetry["metric_poll_recent_matches"])[:20],
        "recent_failures": list(telemetry["metric_poll_recent_failures"])[:20],
    }
    try:
        with get_session_context() as session:
            insert_metric_poll_snapshot(session, payload)
    except Exception:
        logger.exception("Failed to persist metric polling snapshot")


async def _follower_heartbeat_loop() -> None:
    while True:
        try:
            _ensure_state_record(False, notes="follower heartbeat")
        except Exception:
            logger.exception("Follower heartbeat failed")
        await asyncio.sleep(FOLLOWER_INTERVAL)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def get_metric_poll_stats() -> dict[str, Any]:
    telemetry = _metric_telemetry
    return {
        "metric_polling_enabled": get_settings().cep_enable_metric_polling,
        "metric_poll_last_tick_at": _isoformat(telemetry["metric_poll_last_tick_at"]),
        "metric_poll_last_tick_duration_ms": telemetry["metric_poll_last_tick_duration_ms"],
        "metric_poll_last_tick_rule_count": telemetry["metric_poll_last_tick_rule_count"],
        "metric_poll_last_tick_evaluated_count": telemetry["metric_poll_last_tick_evaluated_count"],
        "metric_poll_last_tick_matched_count": telemetry["metric_poll_last_tick_matched_count"],
        "metric_poll_last_tick_skipped_count": telemetry["metric_poll_last_tick_skipped_count"],
        "metric_poll_last_tick_fail_count": telemetry["metric_poll_last_tick_fail_count"],
        "metric_poll_last_error": telemetry["metric_poll_last_error"],
    }


def get_metric_polling_telemetry() -> dict[str, Any]:
    telemetry = get_metric_poll_stats()
    telemetry["recent_matches"] = list(_metric_telemetry["metric_poll_recent_matches"])
    telemetry["recent_failures"] = list(_metric_telemetry["metric_poll_recent_failures"])
    return telemetry


def get_scheduler_instance_id() -> str:
    return INSTANCE_ID


def is_scheduler_leader() -> bool:
    return _is_leader
