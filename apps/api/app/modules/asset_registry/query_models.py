from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class QueryAssetCreate(BaseModel):
    """Create a query asset"""
    model_config = ConfigDict(populate_by_name=True)
    name: str
    description: str | None = None
    scope: str
    # SQL for PostgreSQL/MySQL/BigQuery/Snowflake
    query_sql: str | None = None
    # Cypher for Neo4j
    query_cypher: str | None = None
    # HTTP config for REST/GraphQL APIs
    query_http: dict[str, Any] | None = None
    query_params: dict[str, Any] = {}
    query_metadata: dict[str, Any] = {}
    tags: dict[str, Any] = {}


class QueryAssetUpdate(BaseModel):
    """Update a query asset"""
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    description: str | None = None
    query_sql: str | None = None
    query_cypher: str | None = None
    query_http: dict[str, Any] | None = None
    query_params: dict[str, Any] | None = None
    query_metadata: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class QueryAssetResponse(BaseModel):
    """Query asset response"""
    asset_id: str
    asset_type: str
    name: str
    description: str | None = None
    version: int
    status: str
    scope: str
    # Source-specific query types
    query_sql: str | None = None
    query_cypher: str | None = None
    query_http: dict[str, Any] | None = None
    query_params: dict[str, Any]
    query_metadata: dict[str, Any]
    tags: dict[str, Any] | None = None
    created_by: str | None = None
    published_by: str | None = None
    published_at: Any | None = None
    created_at: Any
    updated_at: Any
