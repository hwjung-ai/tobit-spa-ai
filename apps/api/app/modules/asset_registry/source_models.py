from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List

from sqlmodel import Field, SQLModel


class SourceType(str, enum.Enum):
    # SQL Databases
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    # NoSQL / Graph
    MONGODB = "mongodb"
    NEO4J = "neo4j"
    REDIS = "redis"
    # Message Queue
    KAFKA = "kafka"
    # Storage
    S3 = "s3"
    # API
    REST_API = "rest_api"
    GRAPHQL_API = "graphql_api"


class SourceConnection(SQLModel):
    # Connection parameters
    host: str | None = Field(default=None)
    port: int = Field(default=5432)
    username: str | None = Field(default=None)
    database: str | None = None

    # URI-based connection (alternative to host/port/username)
    uri: str | None = Field(default=None, description="Connection URI (e.g., bolt://localhost, postgresql://...)")

    # Password fields
    password: str | None = Field(
        default=None, description="Plain text password (use only in development)"
    )
    password_encrypted: str | None = Field(
        default=None, description="DEPRECATED: Use secret_key_ref instead"
    )
    secret_key_ref: str | None = Field(
        default=None, description="Reference to secret in secrets manager"
    )

    # Connection settings
    timeout: int = Field(default=30)
    max_connections: int | None = Field(default=None)
    ssl_mode: str | None = Field(default="verify-full")
    connection_params: Dict[str, Any] | None = Field(default_factory=dict)

    # Metadata
    description: str | None = None
    test_query: str | None = None

    @property
    def connection_string(self) -> str:
        """Generate connection string without password"""
        if self.uri:
            # Extract host from URI for display
            return self.uri
        base = f"{self.username}@{self.host}:{self.port}"
        if self.database:
            base += f"/{self.database}"
        return base


class SourceAsset(SQLModel):
    # Asset metadata
    asset_type: str = Field(default="source")
    name: str = Field(min_length=1)
    description: str | None = None
    version: int = Field(default=1)
    status: str = Field(default="draft")

    # Source-specific fields
    source_type: SourceType
    connection: SourceConnection

    # Asset management
    scope: str | None = None
    tags: Dict[str, Any] | None = Field(default_factory=dict)

    # Metadata
    created_by: str | None = None
    published_by: str | None = None
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # For spec_json pattern consistency (P0-7)
    spec_json: Dict[str, Any] | None = Field(
        default=None, description="JSON spec for the source connection"
    )

    @property
    def spec(self) -> Dict[str, Any]:
        """Get the spec for this source"""
        if self.spec_json:
            return self.spec_json

        # Build spec from connection
        spec = {
            "source_type": self.source_type.value,
            "host": self.connection.host,
            "port": self.connection.port,
            "username": self.connection.username,
            "database": self.connection.database,
            "timeout": self.connection.timeout,
        }

        if self.connection.ssl_mode:
            spec["ssl_mode"] = self.connection.ssl_mode
        if self.connection.connection_params:
            spec["connection_params"] = self.connection.connection_params

        return spec

    @spec.setter
    def spec(self, value: Dict[str, Any]) -> None:
        """Set the spec and update connection"""
        self.spec_json = value
        self.connection.host = value.get("host", "")
        self.connection.port = value.get("port", 5432)
        self.connection.username = value.get("username", "")
        self.connection.database = value.get("database")
        self.connection.timeout = value.get("timeout", 30)
        self.connection.ssl_mode = value.get("ssl_mode")
        self.connection.connection_params = value.get("connection_params", {})


class SourceAssetCreate(SQLModel):
    name: str = Field(min_length=1)
    description: str | None = None
    source_type: SourceType
    connection: SourceConnection
    scope: str | None = None
    tags: Dict[str, Any] | None = Field(default_factory=dict)


class SourceAssetUpdate(SQLModel):
    name: str | None = Field(min_length=1)
    description: str | None = None
    source_type: SourceType | None = None
    connection: SourceConnection | None = None
    scope: str | None = None
    tags: Dict[str, Any] | None = None


class SourceAssetResponse(SQLModel):
    asset_id: str
    asset_type: str
    name: str
    description: str | None
    version: int
    status: str
    source_type: SourceType
    connection: SourceConnection
    scope: str | None
    tags: Dict[str, Any] | None
    created_by: str | None
    published_by: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionTestResult(SQLModel):
    success: bool
    message: str
    error_details: str | None = None
    execution_time_ms: int | None = None
    test_result: Dict[str, Any] | None = None


class SourceListResponse(SQLModel):
    assets: List[SourceAssetResponse]
    total: int
    page: int
    page_size: int
