from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy import JSON, Column, Text
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel


def _now_kst() -> datetime:
    """Get current time in KST (UTC+9)."""
    return datetime.now(timezone(timedelta(hours=9)))


class QueryHistory(SQLModel, table=True):
    __tablename__ = "query_history"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
    )
    tenant_id: str = Field(
        default="default",
        sa_column=Column(Text, nullable=False, server_default=sa.text("'default'")),
    )
    user_id: str = Field(
        default="default",
        sa_column=Column(Text, nullable=False, server_default=sa.text("'default'")),
    )
    feature: str = Field(sa_column=Column(Text, nullable=False))
    question: str = Field(sa_column=Column(Text, nullable=False))
    summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(
        default="ok",
        sa_column=Column(Text, nullable=False, server_default=sa.text("'ok'")),
    )
    response: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    metadata_info: dict[str, Any] | None = Field(
        default=None,
        alias="metadata",
        sa_column=Column("metadata", JSON, nullable=True),
    )
    trace_id: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=_now_kst,
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
