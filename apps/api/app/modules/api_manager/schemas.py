from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator, validator

ApiType = Literal["system", "custom"]
LogicType = Literal["sql", "workflow", "python", "script", "http"]


def _ensure_json_mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return {}
        try:
            parsed = json.loads(trimmed)
        except ValueError as exc:
            raise ValueError(f"{name} must be a valid JSON object: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"{name} must be a JSON object")
        return parsed
    if isinstance(value, dict):
        return value
    raise ValueError(f"{name} must be a JSON object")


class ApiDefinitionCreate(BaseModel):
    api_name: str
    api_type: ApiType
    method: Literal["GET", "POST", "PUT", "DELETE"]
    endpoint: str
    logic_type: LogicType = "sql"
    logic_body: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    param_schema: dict[str, Any] = Field(default_factory=dict)
    runtime_policy: dict[str, Any] = Field(default_factory=dict)
    logic_spec: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_by: str | None = None

    @validator("api_name", "method", "endpoint")
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @validator("param_schema", pre=True, always=True)
    def ensure_param_schema(cls, value: Any) -> dict[str, Any]:
        return _ensure_json_mapping(value, "param_schema")

    @validator("runtime_policy", pre=True, always=True)
    def ensure_runtime_policy(cls, value: Any) -> dict[str, Any]:
        return _ensure_json_mapping(value, "runtime_policy")

    @validator("logic_spec", pre=True, always=True)
    def ensure_logic_spec(cls, value: Any) -> dict[str, Any]:
        return _ensure_json_mapping(value, "logic_spec")


class ApiDefinitionUpdate(BaseModel):
    api_name: str | None = None
    method: Literal["GET", "POST", "PUT", "DELETE"] | None = None
    endpoint: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None
    logic_body: str | None = None
    logic_type: LogicType | None = None
    param_schema: dict[str, Any] | None = None
    runtime_policy: dict[str, Any] | None = None
    logic_spec: dict[str, Any] | None = None

    @validator("api_name", "method", "endpoint", pre=True)
    def strip_update_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @validator("param_schema", pre=True)
    def ensure_param_schema_update(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return _ensure_json_mapping(value, "param_schema")

    @validator("runtime_policy", pre=True)
    def ensure_runtime_policy_update(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return _ensure_json_mapping(value, "runtime_policy")

    @validator("logic_spec", pre=True)
    def ensure_logic_spec_update(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return _ensure_json_mapping(value, "logic_spec")


class ApiDefinitionRead(BaseModel):
    api_id: str
    api_name: str
    api_type: ApiType
    method: str
    endpoint: str
    logic_type: LogicType
    logic_body: str
    description: str | None
    tags: list[str]
    param_schema: dict[str, Any]
    runtime_policy: dict[str, Any]
    logic_spec: dict[str, Any]
    is_active: bool
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("api_id", mode="before")
    def _normalize_api_id(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    @field_validator("tags", mode="before")
    def _normalize_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, dict):
            flattened: list[str] = []
            for entry in value.values():
                if isinstance(entry, list):
                    flattened.extend(
                        str(item) for item in entry if isinstance(item, str)
                    )
            return flattened
        return [str(value)]

    @model_validator(mode="before")
    def _ensure_dict(cls, values: Any) -> dict[str, Any]:
        if hasattr(values, "model_dump"):
            values = values.model_dump()
        return values


class ApiExecuteRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    limit: int | None = 200
    executed_by: str | None = None
    input: Any | None = None


class ApiDryRunRequest(BaseModel):
    logic_type: LogicType
    logic_body: str
    params: dict[str, Any] = Field(default_factory=dict)
    input: Any | None = None
    runtime_policy: dict[str, Any] = Field(default_factory=dict)
    logic_spec: dict[str, Any] = Field(default_factory=dict)


class ApiExecuteResponse(BaseModel):
    executed_sql: str
    params: dict[str, Any]
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    duration_ms: int


class ApiScriptExecuteResult(BaseModel):
    output: dict[str, Any]
    params: dict[str, Any]
    input: Any | None
    duration_ms: int
    references: dict[str, Any]
    logs: list[str]


class WorkflowStep(BaseModel):
    node_id: str
    node_type: Literal["sql", "script"]
    status: Literal["success", "fail"]
    duration_ms: int
    row_count: int
    columns: list[str] | None = None
    output: dict[str, Any] | None = None
    error_message: str | None = None
    references: dict[str, Any] | None = None


class WorkflowExecuteResult(BaseModel):
    steps: list[WorkflowStep]
    final_output: dict[str, Any]
    references: list[dict[str, Any]]


class ApiExecLogRead(BaseModel):
    exec_id: str
    api_id: str
    executed_at: datetime
    executed_by: str | None
    status: str
    duration_ms: int
    row_count: int
    request_params: dict | None
    error_message: str | None

    class Config:
        from_attributes = True

    @field_validator("exec_id", "api_id", mode="before")
    def _normalize_uuid_fields(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value
