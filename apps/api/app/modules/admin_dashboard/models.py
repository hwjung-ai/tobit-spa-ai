from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbAdminSetting(SQLModel, table=True):
    __tablename__ = "tb_admin_setting"
    __table_args__ = ({"extend_existing": True},)

    setting_key: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    setting_value: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    updated_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )


class TbAdminSettingAudit(SQLModel, table=True):
    __tablename__ = "tb_admin_setting_audit"
    __table_args__ = ({"extend_existing": True},)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    setting_key: str = Field(sa_column=Column(Text, nullable=False))
    old_value: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    new_value: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    admin_id: str = Field(sa_column=Column(Text, nullable=False))
    reason: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )


class TbUserActivityLog(SQLModel, table=True):
    __tablename__ = "tb_user_activity_log"
    __table_args__ = ({"extend_existing": True},)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    user_id: str = Field(foreign_key="tb_user.id", index=True, max_length=36)
    activity_type: str = Field(max_length=50, index=True)
    activity_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
        ),
    )
