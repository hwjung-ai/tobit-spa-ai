from __future__ import annotations

import uuid
from datetime import datetime

from typing import Any

from sqlalchemy import Column, Text, Boolean, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class ApiType(str):
    system = "system"
    custom = "custom"


class LogicType(str):
    sql = "sql"
    python = "python"
    workflow = "workflow"
    script = "script"
    http = "http"


class TbApiDef(SQLModel, table=True):
    __tablename__ = "tb_api_def"

    api_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
    )
    api_name: str = Field(sa_column=Column(Text, nullable=False))
    api_type: str = Field(sa_column=Column(Text, nullable=False))
    method: str = Field(sa_column=Column(Text, nullable=False))
    endpoint: str = Field(sa_column=Column(Text, nullable=False))
    logic_type: str = Field(sa_column=Column(Text, nullable=False))
    logic_body: str = Field(sa_column=Column(Text, nullable=False))
    param_schema: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    runtime_policy: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    logic_spec: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
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


class ApiExecLog(SQLModel, table=True):
    __tablename__ = "tb_api_exec_log"

    exec_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    api_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
    executed_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(sa_column=Column(Text, nullable=False))
    duration_ms: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    row_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    request_params: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))


class ApiExecStepLog(SQLModel, table=True):
    __tablename__ = "tb_api_exec_step_log"

    exec_step_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    exec_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))
    node_id: str = Field(sa_column=Column(Text, nullable=False))
    node_type: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(sa_column=Column(Text, nullable=False))
    duration_ms: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    row_count: int = Field(sa_column=Column(Integer, nullable=False, server_default=text("0")))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    references: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
