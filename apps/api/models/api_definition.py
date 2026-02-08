from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ApiScope(str, enum.Enum):
    system = "system"
    custom = "custom"


class ApiMode(str, enum.Enum):
    sql = "sql"
    python = "python"
    workflow = "workflow"
    http = "http"
    script = "script"


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
    runtime_policy: dict | None = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    is_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = Field(default=None)


class ApiDefinitionVersion(SQLModel, table=True):
    __tablename__ = "api_definition_versions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    api_id: uuid.UUID = Field(foreign_key="api_definitions.id", nullable=False, index=True)
    version: int = Field(sa_column=Column(Integer, nullable=False))
    change_type: str = Field(default="update", nullable=False)
    change_summary: str | None = Field(default=None, sa_column=Column(Text))
    snapshot: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_by: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
