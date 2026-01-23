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


class MappingAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    content: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class PolicyAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    limits: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class QueryAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    query_sql: str | None = None
    query_params: dict[str, Any] | None = None
    query_metadata: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class ScreenAssetUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    screen_schema: dict[str, Any] | None = Field(default=None, alias="schema_json")
    tags: dict[str, Any] | None = None
