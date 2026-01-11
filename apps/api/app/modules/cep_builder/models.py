from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TriggerType(str):
    metric = "metric"
    event = "event"
    schedule = "schedule"


class TbCepRule(SQLModel, table=True):
    __tablename__ = "tb_cep_rule"
    __table_args__ = {"extend_existing": True}

    rule_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    rule_name: str = Field(sa_column=Column(Text, nullable=False))
    trigger_type: str = Field(sa_column=Column(Text, nullable=False))
    trigger_spec: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    action_spec: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default=text("true")))
    created_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )


class TbCepExecLog(SQLModel, table=True):
    __tablename__ = "tb_cep_exec_log"
    __table_args__ = {"extend_existing": True}

    exec_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    rule_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))
    triggered_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    status: str = Field(sa_column=Column(Text, nullable=False))
    duration_ms: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    references: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )


class TbCepSchedulerState(SQLModel, table=True):
    __tablename__ = "tb_cep_scheduler_state"
    __table_args__ = {"extend_existing": True}

    state_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    instance_id: str = Field(sa_column=Column(Text, nullable=False))
    is_leader: bool = Field(sa_column=Column(Boolean, nullable=False, server_default=text("false")))
    last_heartbeat_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class TbCepNotification(SQLModel, table=True):
    __tablename__ = "tb_cep_notification"
    __table_args__ = {"extend_existing": True}

    notification_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    name: str = Field(sa_column=Column(Text, nullable=False))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, server_default=text("true")))
    channel: str = Field(sa_column=Column(Text, nullable=False))
    webhook_url: str = Field(sa_column=Column(Text, nullable=False))
    rule_id: uuid.UUID | None = Field(default=None, sa_column=Column(UUID(as_uuid=True), nullable=True))
    headers: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    trigger: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    policy: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )


class TbCepNotificationLog(SQLModel, table=True):
    __tablename__ = "tb_cep_notification_log"
    __table_args__ = {"extend_existing": True}

    log_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    notification_id: uuid.UUID = Field(
        sa_column=Column(UUID(as_uuid=True), ForeignKey("tb_cep_notification.notification_id"), nullable=False)
    )
    fired_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    status: str = Field(sa_column=Column(Text, nullable=False))
    reason: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    response_status: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    response_body: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    dedup_key: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    ack: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default=text("false")))
    ack_at: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True))
    ack_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )


class TbCepMetricPollSnapshot(SQLModel, table=True):
    __tablename__ = "tb_cep_metric_poll_snapshot"
    __table_args__ = {"extend_existing": True}

    snapshot_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    instance_id: str = Field(sa_column=Column(Text, nullable=False))
    is_leader: bool = Field(sa_column=Column(Boolean, nullable=False))
    tick_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    tick_duration_ms: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    rule_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    evaluated_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    matched_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    skipped_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    fail_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    last_error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    recent_matches: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    recent_failures: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
