from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class ApiScope(str, enum.Enum):
    system = "system"
    custom = "custom"


class ApiMode(str, enum.Enum):
    sql = "sql"
    python = "python"
    workflow = "workflow"


class ApiDefinition(SQLModel, table=True):
    __tablename__ = "api_definitions"
    __table_args__ = (UniqueConstraint("method", "path", name="uq_api_method_path"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    scope: ApiScope = Field(default=ApiScope.custom, nullable=False)
    name: str = Field(nullable=False, index=True)
    method: str = Field(nullable=False)
    path: str = Field(nullable=False)
    description: str | None = Field(default=None, sa_column=Column(Text))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, default=list))
    mode: ApiMode | None = Field(default=ApiMode.sql)
    logic: str | None = Field(default=None, sa_column=Column(Text))
    is_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = Field(default=None)
