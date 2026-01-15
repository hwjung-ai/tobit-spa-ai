from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Literal

UiType = Literal["grid", "chart", "dashboard"]


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


def _validate_data_source(value: dict[str, Any]) -> dict[str, Any]:
    endpoint = value.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError("schema.data_source.endpoint is required")
    method = value.get("method")
    if method not in {"GET", "POST"}:
        raise ValueError("schema.data_source.method must be GET or POST")
    default_params = value.get("default_params", {})
    if not isinstance(default_params, dict):
        raise ValueError("schema.data_source.default_params must be an object")
    return {"endpoint": endpoint.strip(), "method": method, "default_params": default_params}


def _validate_layout(value: dict[str, Any]) -> dict[str, Any]:
    layout_type = value.get("type")
    if layout_type not in {"grid", "chart", "dashboard"}:
        raise ValueError("schema.layout.type must be grid, chart, or dashboard")
    return value


def _validate_widget(widget: dict[str, Any]) -> dict[str, Any]:
    widget_id = widget.get("id")
    if not isinstance(widget_id, str) or not widget_id.strip():
        raise ValueError("dashboard.widget.id is required")
    layout = widget.get("layout")
    if not isinstance(layout, dict):
        raise ValueError(f"widget {widget_id} missing layout")
    for coord in ("x", "y", "w", "h"):
        if not isinstance(layout.get(coord), (int, float)):
            raise ValueError(f"widget {widget_id} layout.{coord} must be a number")
    data_source = widget.get("data_source")
    if not isinstance(data_source, dict):
        raise ValueError(f"widget {widget_id} missing data_source")
    endpoint = data_source.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ValueError(f"widget {widget_id} data_source.endpoint is required")
    render = widget.get("render")
    if not isinstance(render, dict):
        raise ValueError(f"widget {widget_id} missing render")
    if render.get("type") not in {"grid", "chart_line", "json"}:
        raise ValueError(f"widget {widget_id} render.type must be grid/chart_line/json")
    return widget


class UiDefinitionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ui_name: str
    ui_type: UiType
    ui_schema: dict[str, Any] = Field(alias="schema")
    description: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_by: str | None = None

    @validator("ui_name")
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @validator("ui_schema", pre=True, always=True)
    def ensure_schema(cls, value: Any) -> dict[str, Any]:
        parsed = _ensure_json_mapping(value, "schema")
        data_source = parsed.get("data_source")
        if not isinstance(data_source, dict):
            raise ValueError("schema.data_source is required")
        layout = parsed.get("layout")
        if not isinstance(layout, dict):
            raise ValueError("schema.layout is required")
        parsed["data_source"] = _validate_data_source(data_source)
        parsed["layout"] = _validate_layout(layout)
        if parsed.get("ui_type") == "dashboard":
            widgets = parsed.get("widgets")
            if not isinstance(widgets, list) or not widgets:
                raise ValueError("dashboard schema requires widgets array")
            parsed["widgets"] = [_validate_widget(widget) for widget in widgets]
        return parsed


class UiDefinitionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ui_name: str | None = None
    ui_type: UiType | None = None
    ui_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    description: str | None = None
    tags: dict[str, Any] | None = None
    is_active: bool | None = None

    @validator("ui_name", pre=True)
    def normalize_name(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @validator("ui_schema", pre=True)
    def ensure_schema(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        parsed = _ensure_json_mapping(value, "schema")
        data_source = parsed.get("data_source")
        if not isinstance(data_source, dict):
            raise ValueError("schema.data_source is required")
        layout = parsed.get("layout")
        if not isinstance(layout, dict):
            raise ValueError("schema.layout is required")
        parsed["data_source"] = _validate_data_source(data_source)
        parsed["layout"] = _validate_layout(layout)
        if parsed.get("ui_type") == "dashboard":
            widgets = parsed.get("widgets")
            if not isinstance(widgets, list) or not widgets:
                raise ValueError("dashboard schema requires widgets array")
            parsed["widgets"] = [_validate_widget(widget) for widget in widgets]
        return parsed


class UiDefinitionRead(BaseModel):
    ui_id: str
    ui_name: str
    ui_type: UiType
    ui_schema: dict[str, Any] = Field(alias="schema")
    description: str | None
    tags: dict[str, Any]
    is_active: bool
    created_by: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @validator("ui_id", pre=True)
    def stringify_id(cls, value: Any) -> str:
        return str(value)


class UiDefinitionList(BaseModel):
    ui_id: str
    ui_name: str
    ui_type: UiType
    is_active: bool
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @validator("ui_id", pre=True)
    def stringify_id(cls, value: Any) -> str:
        return str(value)
