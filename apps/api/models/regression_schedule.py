"""
Regression Schedule Model for persistent storage.
Ensures schedules survive server restarts in production.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, Text, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbRegressionSchedule(SQLModel, table=True):
    """
    Persistent storage for regression test schedules.

    Replaces the in-memory Dict storage in RegressionScheduler to ensure
    schedules survive server restarts in production environments.
    """
    __tablename__ = "tb_regression_schedule"
    __table_args__ = (
        Index("ix_regression_schedule_tenant_id", "tenant_id"),
        Index("ix_regression_schedule_enabled", "enabled"),
        {"extend_existing": True},
    )

    schedule_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    name: str = Field(sa_column=Column(Text, nullable=False))
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
    )
    schedule_type: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Type: 'cron' or 'interval'",
    )
    cron_expression: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Cron expression e.g., '0 2 * * *' (daily at 2 AM)",
    )
    interval_minutes: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )
    test_suite_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    notify_on_failure: bool = Field(default=True)
    notify_on_success: bool = Field(default=False)
    notification_channels: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
        description="List of channels: slack, email, webhook",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
        description="Tenant ID for multi-tenant isolation",
    )
    created_by: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default="now()"
        ),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default="now()"
        ),
    )

    def to_schedule_config(self) -> dict[str, Any]:
        """Convert to ScheduleConfig-like dict for compatibility."""
        return {
            "schedule_id": str(self.schedule_id),
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "schedule_type": self.schedule_type,
            "cron_expression": self.cron_expression,
            "interval_minutes": self.interval_minutes,
            "test_suite_ids": self.test_suite_ids,
            "notify_on_failure": self.notify_on_failure,
            "notify_on_success": self.notify_on_success,
            "notification_channels": self.notification_channels,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TbRegressionScheduleRun(SQLModel, table=True):
    """
    Persistent storage for regression schedule run history.
    """
    __tablename__ = "tb_regression_schedule_run"
    __table_args__ = (
        Index("ix_regression_schedule_run_schedule_id", "schedule_id"),
        Index("ix_regression_schedule_run_started_at", "started_at"),
        {"extend_existing": True},
    )

    run_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    schedule_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), nullable=False, index=True),
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default="now()"
        ),
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
    )
    status: str = Field(
        sa_column=Column(Text, nullable=False),
        description="running, success, failed, partial",
    )
    total_tests: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    results: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True),
    )
    tenant_id: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
    )
