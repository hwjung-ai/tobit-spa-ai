"""
CI (Configuration Item) Management Models for change tracking and integrity validation.
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel


# ============================================================================
# Enumerations
# ============================================================================

class ChangeType(str, Enum):
    """Types of changes to a CI."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    DUPLICATE = "duplicate"
    RESTORE = "restore"


class ChangeStatus(str, Enum):
    """Status of a change."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"


class IntegrityStatus(str, Enum):
    """CI integrity status."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    DUPLICATE = "duplicate"


# ============================================================================
# Base Models
# ============================================================================

class TbCIChangeBase(SQLModel):
    """Base model for CI changes."""
    ci_id: str = Field(max_length=100, index=True)
    change_type: ChangeType
    status: ChangeStatus = Field(default=ChangeStatus.PENDING, index=True)

    changed_by_user_id: str = Field(max_length=36)
    change_reason: Optional[str] = Field(default=None, max_length=1000)

    old_values: Optional[str] = Field(default=None, max_length=5000)  # JSON string
    new_values: Optional[str] = Field(default=None, max_length=5000)  # JSON string

    approved_by_user_id: Optional[str] = Field(default=None, max_length=36)
    approved_at: Optional[datetime] = Field(default=None)
    approval_notes: Optional[str] = Field(default=None, max_length=1000)


class TbCIIntegrityIssueBase(SQLModel):
    """Base model for CI integrity issues."""
    ci_id: str = Field(max_length=100, index=True)
    issue_type: str = Field(max_length=50)  # duplicate, missing_field, inconsistent, etc.
    severity: str = Field(max_length=20)  # info, warning, error

    description: str = Field(max_length=1000)
    related_ci_ids: Optional[str] = Field(default=None, max_length=2000)  # JSON array

    is_resolved: bool = Field(default=False, index=True)
    resolved_by_user_id: Optional[str] = Field(default=None, max_length=36)
    resolved_at: Optional[datetime] = Field(default=None)
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)


class TbCIDuplicateBase(SQLModel):
    """Base model for duplicate CI detection."""
    ci_id_1: str = Field(max_length=100, index=True)
    ci_id_2: str = Field(max_length=100, index=True)

    similarity_score: float = Field(ge=0.0, le=1.0)  # 0-1 score
    match_fields: Optional[str] = Field(default=None, max_length=500)  # JSON array

    is_confirmed: bool = Field(default=False, index=True)
    is_merged: bool = Field(default=False)
    merged_into_ci_id: Optional[str] = Field(default=None, max_length=100)

    confirmed_by_user_id: Optional[str] = Field(default=None, max_length=36)
    confirmed_at: Optional[datetime] = Field(default=None)


# ============================================================================
# Database Models
# ============================================================================

class TbCIChange(TbCIChangeBase, table=True):
    """CI Change tracking table."""
    __tablename__ = "tb_ci_change"

    __table_args__ = ({"extend_existing": True},)
    id: str = Field(primary_key=True, max_length=36, default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by_trace_id: str = Field(max_length=36, default="system")


class TbCIIntegrityIssue(TbCIIntegrityIssueBase, table=True):
    """CI Integrity validation issues table."""
    __tablename__ = "tb_ci_integrity_issue"

    __table_args__ = ({"extend_existing": True},)
    id: str = Field(primary_key=True, max_length=36, default_factory=lambda: str(uuid4()))
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detected_by_trace_id: str = Field(max_length=36, default="system")


class TbCIDuplicate(TbCIDuplicateBase, table=True):
    """CI Duplicate detection table."""
    __tablename__ = "tb_ci_duplicate"

    __table_args__ = ({"extend_existing": True},)
    id: str = Field(primary_key=True, max_length=36, default_factory=lambda: str(uuid4()))
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Pydantic Schemas (for API)
# ============================================================================

class CIChangeRead(BaseModel):
    """Schema for reading CI changes."""
    id: str
    ci_id: str
    change_type: ChangeType
    status: ChangeStatus
    changed_by_user_id: str
    change_reason: Optional[str]
    old_values: Optional[str]
    new_values: Optional[str]
    approved_by_user_id: Optional[str]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class CIChangeCreate(BaseModel):
    """Schema for creating CI changes."""
    ci_id: str
    change_type: ChangeType
    changed_by_user_id: str
    change_reason: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None


class CIChangeApprove(BaseModel):
    """Schema for approving CI changes."""
    approved_by_user_id: str
    approval_notes: Optional[str] = None
    approved: bool = True


class CIIntegrityIssueRead(BaseModel):
    """Schema for reading CI integrity issues."""
    id: str
    ci_id: str
    issue_type: str
    severity: str
    description: str
    related_ci_ids: Optional[str]
    is_resolved: bool
    resolved_by_user_id: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    detected_at: datetime


class CIDuplicateRead(BaseModel):
    """Schema for reading CI duplicates."""
    id: str
    ci_id_1: str
    ci_id_2: str
    similarity_score: float
    match_fields: Optional[str]
    is_confirmed: bool
    is_merged: bool
    merged_into_ci_id: Optional[str]
    confirmed_by_user_id: Optional[str]
    confirmed_at: Optional[datetime]
    detected_at: datetime


class CIDuplicateConfirm(BaseModel):
    """Schema for confirming duplicates."""
    confirmed_by_user_id: str
    action: str  # "merge", "ignore", "review"
    merge_into_ci_id: Optional[str] = None


# ============================================================================
# Summary Models
# ============================================================================

class CIChangeHistory(BaseModel):
    """Summary of CI change history."""
    ci_id: str
    total_changes: int
    create_count: int
    update_count: int
    delete_count: int
    merge_count: int
    last_change: Optional[datetime]
    last_changed_by: Optional[str]
    pending_approvals: int
    approved_changes: int


class CIIntegritySummary(BaseModel):
    """Summary of CI integrity status."""
    ci_id: str
    integrity_status: IntegrityStatus
    issue_count: int
    warning_count: int
    error_count: int
    duplicate_count: int
    last_validation: Optional[datetime]
    requires_review: bool


class CIChangeStats(BaseModel):
    """Statistics for CI changes."""
    total_changes: int
    pending_changes: int
    approved_changes: int
    rejected_changes: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    changes_today: int
    changes_this_week: int
    most_changed_ci: Optional[str]
    most_active_user: Optional[str]
