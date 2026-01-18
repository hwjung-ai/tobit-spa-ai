from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Text, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbAuditLog(SQLModel, table=True):
    """Audit log table for tracking changes to assets, settings, and other resources."""

    __tablename__ = "tb_audit_log"

    __table_args__ = ({"extend_existing": True},)
    audit_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    trace_id: str = Field(sa_column=Column(Text, nullable=False, index=True))
    parent_trace_id: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    resource_type: str = Field(sa_column=Column(Text, nullable=False))
    resource_id: str = Field(sa_column=Column(Text, nullable=False))
    action: str = Field(sa_column=Column(Text, nullable=False))
    actor: str = Field(sa_column=Column(Text, nullable=False))
    changes: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    old_values: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    new_values: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    audit_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")),
    )
