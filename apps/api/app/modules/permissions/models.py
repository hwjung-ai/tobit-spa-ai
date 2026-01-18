"""Permission models for resource-level access control."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class ResourcePermission(str, Enum):
    """Fine-grained resource permission enumeration."""
    # API Management
    API_READ = "api:read"
    API_CREATE = "api:create"
    API_UPDATE = "api:update"
    API_DELETE = "api:delete"
    API_EXECUTE = "api:execute"
    API_EXPORT = "api:export"

    # CI/CD Management
    CI_READ = "ci:read"
    CI_CREATE = "ci:create"
    CI_UPDATE = "ci:update"
    CI_DELETE = "ci:delete"
    CI_EXECUTE = "ci:execute"
    CI_PAUSE = "ci:pause"

    # Metrics & Monitoring
    METRIC_READ = "metric:read"
    METRIC_EXPORT = "metric:export"

    # Graph & Assets
    GRAPH_READ = "graph:read"
    GRAPH_UPDATE = "graph:update"

    # History & Audit
    HISTORY_READ = "history:read"
    HISTORY_DELETE = "history:delete"

    # CEP Rules
    CEP_READ = "cep:read"
    CEP_CREATE = "cep:create"
    CEP_UPDATE = "cep:update"
    CEP_DELETE = "cep:delete"
    CEP_EXECUTE = "cep:execute"

    # Documents
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_EXPORT = "document:export"

    # UI Definitions
    UI_READ = "ui:read"
    UI_CREATE = "ui:create"
    UI_UPDATE = "ui:update"
    UI_DELETE = "ui:delete"

    # Asset Registry
    ASSET_READ = "asset:read"
    ASSET_CREATE = "asset:create"
    ASSET_UPDATE = "asset:update"
    ASSET_DELETE = "asset:delete"

    # Settings & Configuration
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"

    # Audit & Compliance
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # User & Team Management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"


class RolePermissionDefault(str, Enum):
    """Predefined role-based permission sets."""
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class TbRolePermissionBase(SQLModel):
    """Base role permission mapping."""
    role: RolePermissionDefault
    permission: ResourcePermission
    is_granted: bool = Field(default=True)


class TbRolePermission(TbRolePermissionBase, table=True):
    """Role-to-permission mapping table."""
    __tablename__ = "tb_role_permission"

    __table_args__ = ({"extend_existing": True},)
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


class TbResourcePermissionBase(SQLModel):
    """Base resource-specific permission."""
    user_id: str = Field(foreign_key="tb_user.id", index=True, max_length=36)
    resource_type: str = Field(
        max_length=50,
        description="Type of resource (api, ci, metric, etc.)"
    )
    resource_id: Optional[str] = Field(
        default=None,
        max_length=100,
        index=True,
        description="Specific resource ID (None = all resources of type)"
    )
    permission: ResourcePermission
    is_granted: bool = Field(default=True)
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration for temporary permissions"
    )


class TbResourcePermission(TbResourcePermissionBase, table=True):
    """Resource-specific permission overrides table."""
    __tablename__ = "tb_resource_permission"

    __table_args__ = ({"extend_existing": True},)
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
    created_by_user_id: str = Field(max_length=36, description="Who created this permission")


class PermissionCheck(SQLModel):
    """Result of a permission check."""
    granted: bool
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
