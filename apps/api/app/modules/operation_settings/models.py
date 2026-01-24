from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Column, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbOperationSettings(SQLModel, table=True):
    """Operation settings table for runtime configuration management."""

    __tablename__ = "tb_operation_settings"

    __table_args__ = ({"extend_existing": True},)

    setting_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    setting_key: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    setting_value: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    source: str = Field(
        default="published",
        sa_column=Column(Text, nullable=False, server_default=text("'published'")),
    )
    env_override: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    restart_required: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    published_by: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    published_at: datetime | None = Field(
        default=None, sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
