"""
Screen Editor Models
Provides database models for screen definitions and versions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional, List
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from pydantic import BaseModel


class TbScreen(SQLModel, table=True):
    """Screen definition model."""
    __tablename__ = "tb_screen"

    screen_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique screen identifier"
    )
    tenant_id: str = Field(
        index=True,
        description="Tenant identifier for multi-tenancy"
    )
    screen_name: str = Field(
        max_length=255,
        description="Human-readable screen name"
    )
    screen_type: str = Field(
        default="custom",
        max_length=50,
        description="Screen type (custom, dashboard, form, etc.)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Screen description"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the screen is active"
    )
    is_published: bool = Field(
        default=False,
        description="Whether the screen is published"
    )
    version: int = Field(
        default=1,
        description="Current version number"
    )
    schema_version: str = Field(
        default="1.0",
        max_length=20,
        description="Schema version for compatibility"
    )
    created_by: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User who created the screen"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_by: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User who last updated the screen"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
        description="Last update timestamp"
    )
    published_at: Optional[datetime] = Field(
        default=None,
        description="Publication timestamp"
    )
    published_by: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User who published the screen"
    )
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Tags for categorization"
    )

    # Screen schema content
    components: List[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="UI components definition"
    )
    layout: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Layout configuration"
    )
    state: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="State management configuration"
    )
    bindings: List[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Data bindings"
    )
    actions: List[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON),
        description="Action handlers"
    )
    styles: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Custom styles"
    )

    # Metadata
    meta: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional metadata"
    )


class TbScreenVersion(SQLModel, table=True):
    """Screen version history for rollback and audit."""
    __tablename__ = "tb_screen_version"

    version_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique version identifier"
    )
    screen_id: str = Field(
        index=True,
        foreign_key="tb_screen.screen_id",
        description="Reference to parent screen"
    )
    tenant_id: str = Field(
        index=True,
        description="Tenant identifier"
    )
    version: int = Field(
        description="Version number"
    )
    change_summary: Optional[str] = Field(
        default=None,
        description="Summary of changes"
    )
    created_by: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User who created this version"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Version creation timestamp"
    )

    # Snapshot of screen at this version
    snapshot: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Complete screen snapshot"
    )


class TbScreenAuditLog(SQLModel, table=True):
    """Audit log for screen changes."""
    __tablename__ = "tb_screen_audit_log"

    log_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique log identifier"
    )
    screen_id: str = Field(
        index=True,
        description="Reference to screen"
    )
    tenant_id: str = Field(
        index=True,
        description="Tenant identifier"
    )
    action: str = Field(
        max_length=50,
        description="Action type (create, update, publish, rollback, delete)"
    )
    version_from: Optional[int] = Field(
        default=None,
        description="Previous version"
    )
    version_to: Optional[int] = Field(
        default=None,
        description="New version"
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User who performed the action"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Action timestamp"
    )
    details: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="Additional details"
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="Client IP address"
    )
    user_agent: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Client user agent"
    )


# Pydantic models for API

class ScreenComponent(BaseModel):
    """Component definition."""
    id: str
    type: str
    props: dict = {}
    children: List["ScreenComponent"] = []


class ScreenLayout(BaseModel):
    """Layout definition."""
    type: str = "flex"
    direction: str = "column"
    gap: int = 16
    padding: int = 16


class ScreenState(BaseModel):
    """State definition."""
    schema: dict = {}
    initial: dict = {}


class ScreenBinding(BaseModel):
    """Binding definition."""
    id: str
    source: str
    target: str
    transform: Optional[str] = None


class ScreenAction(BaseModel):
    """Action definition."""
    id: str
    trigger: str
    handler: str
    params: dict = {}


class ScreenCreateRequest(BaseModel):
    """Request to create a new screen."""
    screen_name: str
    screen_type: str = "custom"
    description: Optional[str] = None
    components: List[dict] = []
    layout: dict = {}
    state: dict = {}
    bindings: List[dict] = []
    actions: List[dict] = []
    styles: dict = {}
    tags: List[str] = []
    meta: dict = {}


class ScreenUpdateRequest(BaseModel):
    """Request to update an existing screen."""
    screen_name: Optional[str] = None
    description: Optional[str] = None
    components: Optional[List[dict]] = None
    layout: Optional[dict] = None
    state: Optional[dict] = None
    bindings: Optional[List[dict]] = None
    actions: Optional[List[dict]] = None
    styles: Optional[dict] = None
    tags: Optional[List[str]] = None
    meta: Optional[dict] = None
    is_active: Optional[bool] = None
    change_summary: Optional[str] = None


class ScreenPublishRequest(BaseModel):
    """Request to publish a screen."""
    change_summary: Optional[str] = None


class ScreenRollbackRequest(BaseModel):
    """Request to rollback to a specific version."""
    target_version: int
    reason: Optional[str] = None


class ScreenResponse(BaseModel):
    """Response for a single screen."""
    screen_id: str
    tenant_id: str
    screen_name: str
    screen_type: str
    description: Optional[str]
    is_active: bool
    is_published: bool
    version: int
    schema_version: str
    components: List[dict]
    layout: dict
    state: dict
    bindings: List[dict]
    actions: List[dict]
    styles: dict
    tags: List[str]
    meta: dict
    created_by: Optional[str]
    created_at: datetime
    updated_by: Optional[str]
    updated_at: datetime
    published_at: Optional[datetime]
    published_by: Optional[str]


class ScreenListResponse(BaseModel):
    """Response for screen list."""
    screens: List[ScreenResponse]
    total: int
    page: int
    page_size: int


class ScreenVersionResponse(BaseModel):
    """Response for screen version."""
    version_id: str
    screen_id: str
    version: int
    change_summary: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    snapshot: dict
