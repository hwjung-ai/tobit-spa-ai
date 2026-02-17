from __future__ import annotations

import enum
import os
import re
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


def coerce_source_type(value: Any) -> SourceType:
    """Convert legacy/raw source_type values into SourceType safely."""
    if isinstance(value, SourceType):
        return value

    raw = str(value or "").strip().lower()
    aliases = {
        "postgres": SourceType.POSTGRESQL,
        "postgresql": SourceType.POSTGRESQL,
        "pg": SourceType.POSTGRESQL,
        "neo4j": SourceType.NEO4J,
        "mysql": SourceType.MYSQL,
        "mongodb": SourceType.MONGODB,
        "redis": SourceType.REDIS,
        "kafka": SourceType.KAFKA,
        "bigquery": SourceType.BIGQUERY,
        "snowflake": SourceType.SNOWFLAKE,
        "s3": SourceType.S3,
        "rest_api": SourceType.REST_API,
        "graphql_api": SourceType.GRAPHQL_API,
    }
    return aliases.get(raw, SourceType.POSTGRESQL)


def _coerce_int(value: Any, default: int | None) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
        # Supports env placeholder format like ${DB_PORT:5432}
        match = re.match(r"^\$\{[^:}]+:([+-]?\d+)\}$", text)
        if match:
            return int(match.group(1))
    return default


def _resolve_env_placeholder(value: Any) -> Any:
    """Resolve ${ENV:default} placeholders for string values."""
    if not isinstance(value, str):
        return value

    text = value.strip()
    match = re.match(r"^\$\{([^:}]+)(?::([^}]*))?\}$", text)
    if not match:
        return value

    env_name = match.group(1).strip()
    fallback = match.group(2)
    env_value = os.getenv(env_name)
    if env_value is not None and env_value != "":
        return env_value
    return fallback if fallback is not None else value


def _resolve_env_placeholders(value: Any) -> Any:
    """Recursively resolve env placeholders in dict/list/string payloads."""
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    return _resolve_env_placeholder(value)


def coerce_source_connection(value: Any) -> "SourceConnection":
    """Convert legacy/raw connection payloads into SourceConnection safely."""
    if isinstance(value, SourceConnection):
        return value
    if not isinstance(value, dict):
        return SourceConnection()

    data = _resolve_env_placeholders(dict(value))
    data["port"] = _coerce_int(data.get("port"), 5432)
    data["timeout"] = _coerce_int(data.get("timeout"), 30)
    data["max_connections"] = _coerce_int(data.get("max_connections"), None)

    try:
        return SourceConnection(**data)
    except Exception:
        return SourceConnection(
            host=data.get("host"),
            port=_coerce_int(data.get("port"), 5432) or 5432,
            username=data.get("username"),
            database=data.get("database"),
            uri=data.get("uri"),
            timeout=_coerce_int(data.get("timeout"), 30) or 30,
            max_connections=_coerce_int(data.get("max_connections"), None),
            ssl_mode=data.get("ssl_mode"),
            connection_params=data.get("connection_params") if isinstance(data.get("connection_params"), dict) else {},
            description=data.get("description"),
            test_query=data.get("test_query"),
        )


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
    tags: Dict[str, Any] | None = Field(default_factory=dict)


class SourceAssetUpdate(SQLModel):
    name: str | None = Field(min_length=1)
    description: str | None = None
    source_type: SourceType | None = None
    connection: SourceConnection | None = None
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
