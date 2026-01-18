from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Text, Boolean, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlmodel import Field, SQLModel


class TbUiDef(SQLModel, table=True):
    __tablename__ = 'tb_ui_def'
    __table_args__ = ({"extend_existing": True},)
    model_config = {"populate_by_name": True}

    ui_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    ui_name: str = Field(sa_column=Column(Text, nullable=False))
    ui_type: str = Field(sa_column=Column(Text, nullable=False))
    schema_definition: dict[str, Any] = Field(
        alias="schema",
        default_factory=dict,
        sa_column=Column("schema", JSONB, nullable=False),
    )
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    tags: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )

    @property
    def schema(self) -> dict[str, Any]:
        return self.schema_definition

    @schema.setter
    def schema(self, value: dict[str, Any]) -> None:
        self.schema_definition = value
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text('true')),
    )
    created_by: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()')),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()')),
    )
