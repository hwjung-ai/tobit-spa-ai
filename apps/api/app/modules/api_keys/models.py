"""API Key models for managing programmatic access."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class ApiKeyScope(str, Enum):
    """API Key permission scopes."""
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_DELETE = "api:delete"
    API_EXECUTE = "api:execute"
    CI_READ = "ci:read"
    CI_WRITE = "ci:write"
    CI_DELETE = "ci:delete"
    METRIC_READ = "metric:read"
    GRAPH_READ = "graph:read"
    HISTORY_READ = "history:read"
    CEP_READ = "cep:read"
    CEP_WRITE = "cep:write"


class TbApiKeyBase(SQLModel):
    """Base API Key model."""
    user_id: str = Field(foreign_key="tb_user.id", index=True, max_length=36)
    name: str = Field(max_length=100)
    key_prefix: str = Field(max_length=8, description="First 8 characters of key for preview")
    key_hash: str = Field(max_length=255, description="bcrypt hash of full key")
    scope: str = Field(default="api:read", description="JSON array of scopes")
    is_active: bool = Field(default=True)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class TbApiKey(TbApiKeyBase, table=True):
    """API Key storage table."""
    __tablename__ = "tb_api_key"

    id: str = Field(
        primary_key=True,
        max_length=36,
        default_factory=lambda: str(uuid4())
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_by_trace_id: str = Field(max_length=36, default="system")


class TbApiKeyRead(SQLModel):
    """API Key read schema (without key hash)."""
    id: str
    user_id: str
    name: str
    key_prefix: str
    scope: str
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


class TbApiKeyCreate(SQLModel):
    """API Key creation schema."""
    name: str = Field(min_length=1, max_length=100)
    scope: list[str] = Field(default_factory=lambda: ["api:read"])
    expires_at: Optional[datetime] = None
