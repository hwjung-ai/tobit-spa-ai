"""
Admin Regression - Automated Test Scheduling
Provides scheduling and automation for regression tests.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from core.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

class ScheduleConfig(BaseModel):
    """Schedule configuration."""
    schedule_id: str
    name: str
    description: Optional[str] = None
    enabled: bool = True
    schedule_type: str  # "cron", "interval"
    cron_expression: Optional[str] = None  # e.g., "0 2 * * *" (daily at 2 AM)
    interval_minutes: Optional[int] = None
    test_suite_ids: List[str] = []
    notify_on_failure: bool = True
    notify_on_success: bool = False
    notification_channels: List[str] = []  # slack, email, webhook
    tenant_id: Optional[str] = None  # Multi-tenant isolation
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ScheduleRun(BaseModel):
    """Record of a scheduled run."""
    run_id: str
    schedule_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "running", "success", "failed", "partial"
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error_message: Optional[str] = None
    results: List[Dict[str, Any]] = []


class ScheduleCreateRequest(BaseModel):
    """Request to create a new schedule."""
    name: str
    description: Optional[str] = None
    schedule_type: str = "cron"
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    test_suite_ids: List[str] = []
    notify_on_failure: bool = True
    notify_on_success: bool = False
    notification_channels: List[str] = []


class ScheduleUpdateRequest(BaseModel):
    """Request to update a schedule."""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    test_suite_ids: Optional[List[str]] = None
    notify_on_failure: Optional[bool] = None
    notify_on_success: Optional[bool] = None
    notification_channels: Optional[List[str]] = None


# ============================================================================
# Scheduler Manager
# ============================================================================

class RegressionScheduler:
    """Manages automated regression test scheduling."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.run_history: Dict[str, List[ScheduleRun]] = {}
        self._started = False

    async def start(self):
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Regression scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        if self._started:
            self.scheduler.shutdown(wait=True)
            self._started = False
            logger.info("Regression scheduler stopped")

    def add_schedule(self, config: ScheduleConfig) -> bool:
        """Add a new schedule to the scheduler."""
        try:
            if config.schedule_type == "cron" and config.cron_expression:
                trigger = CronTrigger.from_crontab(config.cron_expression)
            elif config.schedule_type == "interval" and config.interval_minutes:
                trigger = IntervalTrigger(minutes=config.interval_minutes)
            else:
                raise ValueError(f"Invalid schedule configuration: {config.schedule_type}")

            job_id = f"regression_{config.schedule_id}"

            # Remove existing job if any
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            # Add new job
            self.scheduler.add_job(
                self._execute_schedule,
                trigger=trigger,
                id=job_id,
                args=[config.schedule_id],
                replace_existing=True,
            )

            self.schedules[config.schedule_id] = config
            logger.info(f"Added schedule: {config.name} ({config.schedule_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to add schedule: {e}")
            return False

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule from the scheduler."""
        try:
            job_id = f"regression_{schedule_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            self.schedules.pop(schedule_id, None)
            logger.info(f"Removed schedule: {schedule_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove schedule: {e}")
            return False

    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a paused schedule."""
        job_id = f"regression_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            if schedule_id in self.schedules:
                self.schedules[schedule_id].enabled = True
            return True
        return False

    def disable_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        job_id = f"regression_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)
            if schedule_id in self.schedules:
                self.schedules[schedule_id].enabled = False
            return True
        return False

    async def _execute_schedule(self, schedule_id: str):
        """Execute a scheduled regression test."""
        config = self.schedules.get(schedule_id)
        if not config or not config.enabled:
            logger.warning(f"Schedule {schedule_id} not found or disabled")
            return

        run_id = str(uuid4())
        run = ScheduleRun(
            run_id=run_id,
            schedule_id=schedule_id,
            started_at=datetime.utcnow(),
            status="running",
        )

        logger.info(f"Starting scheduled run: {config.name} ({run_id})")

        try:
            # Import regression executor
            from app.modules.admin.routes.regression import execute_regression_suite

            # Execute tests
            results = []
            total = len(config.test_suite_ids)
            passed = 0
            failed = 0
            skipped = 0

            for suite_id in config.test_suite_ids:
                try:
                    result = await execute_regression_suite(suite_id)
                    results.append(result)

                    if result.get("status") == "passed":
                        passed += 1
                    elif result.get("status") == "failed":
                        failed += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Suite {suite_id} failed: {e}")
                    failed += 1
                    results.append({
                        "suite_id": suite_id,
                        "status": "error",
                        "error": str(e),
                    })

            # Update run record
            run.completed_at = datetime.utcnow()
            run.total_tests = total
            run.passed = passed
            run.failed = failed
            run.skipped = skipped
            run.results = results
            run.status = "success" if failed == 0 else ("partial" if passed > 0 else "failed")

            # Send notifications
            if config.notify_on_failure and failed > 0:
                await self._send_notification(config, run, "failure")
            elif config.notify_on_success and failed == 0:
                await self._send_notification(config, run, "success")

            logger.info(f"Completed scheduled run: {run.status} (passed: {passed}, failed: {failed})")

        except Exception as e:
            run.completed_at = datetime.utcnow()
            run.status = "failed"
            run.error_message = str(e)
            logger.exception(f"Scheduled run failed: {e}")

            if config.notify_on_failure:
                await self._send_notification(config, run, "error")

        # Store run history
        if schedule_id not in self.run_history:
            self.run_history[schedule_id] = []
        self.run_history[schedule_id].append(run)

        # Keep only last 100 runs
        if len(self.run_history[schedule_id]) > 100:
            self.run_history[schedule_id] = self.run_history[schedule_id][-100:]

    async def _send_notification(self, config: ScheduleConfig, run: ScheduleRun, event_type: str):
        """Send notification for schedule events."""
        try:
            from app.modules.cep_builder.notification_channels import send_notification

            message = self._build_notification_message(config, run, event_type)

            for channel in config.notification_channels:
                try:
                    await send_notification(
                        channel_type=channel,
                        message=message,
                        subject=f"Regression Test: {config.name}",
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel}: {e}")

        except ImportError:
            logger.warning("Notification channels not available")

    def _build_notification_message(self, config: ScheduleConfig, run: ScheduleRun, event_type: str) -> str:
        """Build notification message."""
        if event_type == "success":
            return f"✅ Regression tests passed for '{config.name}'\n\nAll {run.passed} tests passed."
        elif event_type == "partial":
            return f"⚠️ Partial success for '{config.name}'\n\nPassed: {run.passed}, Failed: {run.failed}, Skipped: {run.skipped}"
        else:
            return f"❌ Regression tests failed for '{config.name}'\n\nError: {run.error_message or 'See logs for details'}"

    def get_schedules(self) -> List[ScheduleConfig]:
        """Get all schedules."""
        return list(self.schedules.values())

    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Get a specific schedule."""
        return self.schedules.get(schedule_id)

    def get_run_history(self, schedule_id: str, limit: int = 50) -> List[ScheduleRun]:
        """Get run history for a schedule."""
        history = self.run_history.get(schedule_id, [])
        return history[-limit:]

    async def run_now(self, schedule_id: str) -> ScheduleRun:
        """Trigger an immediate run of a schedule."""
        await self._execute_schedule(schedule_id)
        history = self.run_history.get(schedule_id, [])
        return history[-1] if history else None


# Global scheduler instance
scheduler = RegressionScheduler()


# ============================================================================
# API Router
# ============================================================================


router = APIRouter(prefix="/regression/schedules", tags=["admin-regression"])


@router.on_event("startup")
async def startup_scheduler():
    """Start the scheduler on application startup."""
    await scheduler.start()


@router.on_event("shutdown")
async def shutdown_scheduler():
    """Stop the scheduler on application shutdown."""
    await scheduler.stop()


def _filter_schedules_by_tenant(schedules: List[ScheduleConfig], tenant_id: str | None) -> List[ScheduleConfig]:
    """Filter schedules by tenant ID."""
    if not tenant_id:
        return schedules
    return [s for s in schedules if s.tenant_id is None or s.tenant_id == tenant_id]


@router.post("")
async def create_schedule(
    request: ScheduleCreateRequest,
    current_user=Depends(get_current_user),
):
    """Create a new regression test schedule. Tenant-isolated."""
    schedule_id = str(uuid4())
    tenant_id = getattr(current_user, "tenant_id", None)

    config = ScheduleConfig(
        schedule_id=schedule_id,
        name=request.name,
        description=request.description,
        schedule_type=request.schedule_type,
        cron_expression=request.cron_expression,
        interval_minutes=request.interval_minutes,
        test_suite_ids=request.test_suite_ids,
        notify_on_failure=request.notify_on_failure,
        notify_on_success=request.notify_on_success,
        notification_channels=request.notification_channels,
        tenant_id=tenant_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    if scheduler.add_schedule(config):
        return {"success": True, "schedule_id": schedule_id, "schedule": config.model_dump()}
    else:
        raise HTTPException(status_code=400, detail="Failed to create schedule")


@router.get("")
async def list_schedules(current_user=Depends(get_current_user)):
    """List all regression test schedules. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    schedules = scheduler.get_schedules()
    filtered = _filter_schedules_by_tenant(schedules, tenant_id)
    return {"schedules": [s.model_dump() for s in filtered], "count": len(filtered)}


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str, current_user=Depends(get_current_user)):
    """Get a specific schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return config.model_dump()


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdateRequest,
    current_user=Depends(get_current_user),
):
    """Update a schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    config.updated_at = datetime.utcnow()

    if scheduler.add_schedule(config):
        return {"success": True, "schedule": config.model_dump()}
    else:
        raise HTTPException(status_code=400, detail="Failed to update schedule")


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, current_user=Depends(get_current_user)):
    """Delete a schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if scheduler.remove_schedule(schedule_id):
        return {"success": True, "schedule_id": schedule_id}
    else:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/{schedule_id}/enable")
async def enable_schedule(schedule_id: str, current_user=Depends(get_current_user)):
    """Enable a schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if scheduler.enable_schedule(schedule_id):
        return {"success": True, "schedule_id": schedule_id}
    else:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/{schedule_id}/disable")
async def disable_schedule(schedule_id: str, current_user=Depends(get_current_user)):
    """Disable a schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if scheduler.disable_schedule(schedule_id):
        return {"success": True, "schedule_id": schedule_id}
    else:
        raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/{schedule_id}/run")
async def run_schedule_now(schedule_id: str, current_user=Depends(get_current_user)):
    """Trigger an immediate run of a schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    run = await scheduler.run_now(schedule_id)
    if run:
        return {"success": True, "run": run.model_dump()}
    else:
        raise HTTPException(status_code=400, detail="Failed to execute schedule")


@router.get("/{schedule_id}/history")
async def get_schedule_history(
    schedule_id: str,
    limit: int = 50,
    current_user=Depends(get_current_user),
):
    """Get run history for a schedule. Tenant-isolated."""
    tenant_id = getattr(current_user, "tenant_id", None)
    config = scheduler.get_schedule(schedule_id)
    if not config:
        raise HTTPException(status_code=404, detail="Schedule not found")
    # Check tenant access
    if tenant_id and config.tenant_id and config.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    history = scheduler.get_run_history(schedule_id, limit)
    return {"runs": [r.model_dump() for r in history], "count": len(history)}
