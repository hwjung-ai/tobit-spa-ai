from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field, field_validator


AssetType = Literal["prompt", "mapping", "policy", "query"]
AssetStatus = Literal["draft", "published"]


class AssetCreate(BaseModel):
    asset_type: AssetType
    name: str
    description: str | None = None

    # Prompt fields
    scope: str | None = None
    engine: str | None = None
    template: str | None = None
    input_schema: dict[str, Any] | None = None
    output_contract: dict[str, Any] | None = None

    # Mapping fields
    mapping_type: str | None = None
    content: dict[str, Any] | None = None

    # Policy fields
    policy_type: str | None = None
    limits: dict[str, Any] | None = None

    # Query fields
    query_sql: str | None = None
    query_params: dict[str, Any] | None = None
    query_metadata: dict[str, Any] | None = None

    created_by: str | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    # Prompt fields
    template: str | None = None
    input_schema: dict[str, Any] | None = None
    output_contract: dict[str, Any] | None = None

    # Mapping fields
    content: dict[str, Any] | None = None

    # Policy fields
    limits: dict[str, Any] | None = None

    # Query fields
    query_sql: str | None = None
    query_params: dict[str, Any] | None = None
    query_metadata: dict[str, Any] | None = None


class AssetRead(BaseModel):
    asset_id: str
    asset_type: AssetType
    name: str
    description: str | None
    version: int
    status: AssetStatus

    # Type-specific fields
    scope: str | None = None
    engine: str | None = None
    template: str | None = None
    input_schema: dict[str, Any] | None = None
    output_contract: dict[str, Any] | None = None
    mapping_type: str | None = None
    content: dict[str, Any] | None = None
    policy_type: str | None = None
    limits: dict[str, Any] | None = None
    query_sql: str | None = None
    query_params: dict[str, Any] | None = None
    query_metadata: dict[str, Any] | None = None

    # Metadata
    created_by: str | None
    published_by: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("asset_id", mode="before")
    @classmethod
    def normalize_asset_id(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value


class AssetPublishRequest(BaseModel):
    published_by: str = "system"


class AssetRollbackRequest(BaseModel):
    to_version: int = Field(..., ge=1)
    executed_by: str = "system"
