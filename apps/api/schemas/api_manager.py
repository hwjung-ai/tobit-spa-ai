from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ScopeType(str, Enum):
    system = "system"
    custom = "custom"


class ModeType(str, Enum):
    sql = "sql"
    python = "python"
    workflow = "workflow"


class ApiDefinitionBase(BaseModel):
    name: str
    method: str
    path: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class ApiDefinitionCreate(ApiDefinitionBase):
    mode: ModeType
    logic: str


class ApiDefinitionUpdate(BaseModel):
    name: str | None = None
    method: str | None = None
    path: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    mode: ModeType | None = None
    logic: str | None = None

    @model_validator(mode="after")
    def ensure_editable_fields(cls, values: ApiDefinitionUpdate) -> "ApiDefinitionUpdate":
        if values.logic is not None and values.mode is None:
            raise ValueError("mode must accompany logic changes")
        return values


class ApiDefinitionRead(BaseModel):
    id: str
    scope: ScopeType
    name: str
    method: str
    path: str
    description: str | None
    tags: list[str]
    mode: ModeType | None
    logic: str | None
    is_enabled: bool


class ApiTestResult(BaseModel):
    summary: str
    tables: list[dict[str, list[str]]] = Field(default_factory=list)


class ApiSyncResponse(BaseModel):
    synced: int
    skipped: int
