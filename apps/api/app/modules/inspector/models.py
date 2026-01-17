from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import Column, Integer, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class TbExecutionTrace(SQLModel, table=True):
    __tablename__ = "tb_execution_trace"

    trace_id: str = Field(
        sa_column=Column(Text, primary_key=True, nullable=False),
    )
    parent_trace_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True, index=True),
    )
    feature: str = Field(sa_column=Column(Text, nullable=False))
    endpoint: str = Field(sa_column=Column(Text, nullable=False))
    method: str = Field(sa_column=Column(Text, nullable=False))
    ops_mode: str = Field(sa_column=Column(Text, nullable=False))
    question: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(
        default="success",
        sa_column=Column(Text, nullable=False, server_default=text("'success'")),
    )
    duration_ms: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False),
    )
    request_payload: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    applied_assets: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    asset_versions: List[str] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    fallbacks: Dict[str, bool] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    plan_raw: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    plan_validated: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    execution_steps: List[Dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    references: List[Dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    answer: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    ui_render: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    audit_links: Dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
