from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssetStatus(str, Enum):
    draft = "draft"
    published = "published"


class PromptAssetCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_type: str = "prompt"
    name: str
    scope: str
    engine: str
    template: str
    input_schema: dict[str, Any]
    output_contract: dict[str, Any]
    tags: dict[str, Any] | None = None
    created_by: str | None = None


class QueryAssetCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_type: str = "query"
    name: str
    description: str | None = None
    scope: str
    query_sql: str
    query_params: dict[str, Any]
    query_metadata: dict[str, Any]
    tags: dict[str, Any] | None = None
    created_by: str | None = None


class ScreenAssetCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_type: str = "screen"
    screen_id: str
    name: str
    description: str | None = None
    screen_schema: dict[str, Any] = Field(alias="schema_json")
    tags: dict[str, Any] | None = None
    created_by: str | None = None


class AssetCreate(ScreenAssetCreate):
    """Backward-compatible alias for screen assets."""


class ScreenAssetRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_id: str
    asset_type: str
    screen_id: str | None = None
    name: str
    description: str | None = None
    version: int
    status: str
    screen_schema: dict[str, Any] | None = Field(default=None, alias="schema_json")
    tags: dict[str, Any] | None = None
    created_by: str | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PromptAssetRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_id: str
    asset_type: str
    name: str
    scope: str
    engine: str
    version: int
    status: str
    template: str
    input_schema: dict[str, Any]
    output_contract: dict[str, Any]
    tags: dict[str, Any] | None = None
    created_by: str | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetRead(ScreenAssetRead):
    """Backward-compatible alias for screen assets."""


class PromptAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    template: str | None = None
    input_schema: dict[str, Any] | None = None
    output_contract: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    expected_updated_at: datetime | None = None
    force: bool = False


class MappingAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    content: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    expected_updated_at: datetime | None = None
    force: bool = False


class PolicyAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    limits: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    expected_updated_at: datetime | None = None
    force: bool = False


class QueryAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    query_sql: str | None = None
    query_params: dict[str, Any] | None = None
    query_metadata: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
    expected_updated_at: datetime | None = None
    force: bool = False


class ScreenAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    screen_schema: dict[str, Any] | None = Field(default=None, alias="schema_json")
    tags: dict[str, Any] | None = None
    expected_updated_at: datetime | None = None
    force: bool = False


class ToolAssetCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_type: str = "tool"
    name: str
    description: str
    tool_type: str
    tool_config: dict[str, Any]
    tool_input_schema: dict[str, Any]
    tool_output_schema: dict[str, Any] | None = None
    tool_catalog_ref: str | None = None
    tags: dict[str, Any] | None = None
    created_by: str | None = None


class ToolAssetRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    asset_id: str
    asset_type: str
    tool_type: str
    name: str
    description: str
    version: int
    status: str
    tool_config: dict[str, Any]
    tool_input_schema: dict[str, Any]
    tool_output_schema: dict[str, Any] | None = None
    tool_catalog_ref: str | None = None
    tags: dict[str, Any] | None = None
    created_by: str | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ToolAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    tool_type: str | None = None
    tool_config: dict[str, Any] | None = None
    tool_input_schema: dict[str, Any] | None = None
    tool_output_schema: dict[str, Any] | None = None
    tool_catalog_ref: str | None = None
    tags: dict[str, Any] | None = None
