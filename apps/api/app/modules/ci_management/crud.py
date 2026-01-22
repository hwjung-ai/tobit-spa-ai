"""
CRUD operations for CI Management (Configuration Item tracking and integrity validation).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, func, select

from .models import (
    ChangeStatus,
    ChangeType,
    CIChangeHistory,
    CIChangeStats,
    CIIntegritySummary,
    IntegrityStatus,
    TbCIChange,
    TbCIDuplicate,
    TbCIIntegrityIssue,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CI Change Management
# ============================================================================

def create_change(
    session: Session,
    ci_id: str,
    change_type: ChangeType,
    changed_by_user_id: str,
    change_reason: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
) -> TbCIChange:
    """Create a new CI change record."""
    change = TbCIChange(
        ci_id=ci_id,
        change_type=change_type,
        changed_by_user_id=changed_by_user_id,
        change_reason=change_reason,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
    )
    session.add(change)
    session.commit()
    session.refresh(change)
    return change


def get_change(session: Session, change_id: str) -> Optional[TbCIChange]:
    """Get a CI change by ID."""
    return session.get(TbCIChange, change_id)


def list_changes(
    session: Session,
    ci_id: Optional[str] = None,
    status: Optional[ChangeStatus] = None,
    change_type: Optional[ChangeType] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[TbCIChange], int]:
    """List CI changes with filtering."""
    statement = select(TbCIChange)

    if ci_id:
        statement = statement.where(TbCIChange.ci_id == ci_id)
    if status:
        statement = statement.where(TbCIChange.status == status)
    if change_type:
        statement = statement.where(TbCIChange.change_type == change_type)

    statement = statement.order_by(TbCIChange.created_at.desc())

    # Get total count
    count_statement = select(func.count()).select_from(TbCIChange)
    if ci_id:
        count_statement = count_statement.where(TbCIChange.ci_id == ci_id)
    if status:
        count_statement = count_statement.where(TbCIChange.status == status)
    if change_type:
        count_statement = count_statement.where(TbCIChange.change_type == change_type)

    total_count = session.exec(count_statement).one()

    # Get paginated results
    changes = session.exec(statement.offset(offset).limit(limit)).all()
    return changes, total_count


def approve_change(
    session: Session,
    change_id: str,
    approved_by_user_id: str,
    approved: bool = True,
    approval_notes: Optional[str] = None,
) -> Optional[TbCIChange]:
    """Approve or reject a CI change."""
    change = session.get(TbCIChange, change_id)
    if not change:
        return None

    if approved:
        change.status = ChangeStatus.APPROVED
    else:
        change.status = ChangeStatus.REJECTED

    change.approved_by_user_id = approved_by_user_id
    change.approved_at = datetime.now(timezone.utc)
    change.approval_notes = approval_notes
    change.updated_at = datetime.now(timezone.utc)

    session.add(change)
    session.commit()
    session.refresh(change)
    return change


def apply_change(session: Session, change_id: str) -> Optional[TbCIChange]:
    """Mark a change as applied."""
    change = session.get(TbCIChange, change_id)
    if not change:
        return None

    if change.status != ChangeStatus.APPROVED:
        raise ValueError(f"Cannot apply non-approved change (status: {change.status})")

    change.status = ChangeStatus.APPLIED
    change.updated_at = datetime.now(timezone.utc)

    session.add(change)
    session.commit()
    session.refresh(change)
    return change


def get_change_history(session: Session, ci_id: str) -> CIChangeHistory:
    """Get change history summary for a CI."""
    statement = select(TbCIChange).where(TbCIChange.ci_id == ci_id)
    changes = session.exec(statement).all()

    create_count = sum(1 for c in changes if c.change_type == ChangeType.CREATE)
    update_count = sum(1 for c in changes if c.change_type == ChangeType.UPDATE)
    delete_count = sum(1 for c in changes if c.change_type == ChangeType.DELETE)
    merge_count = sum(1 for c in changes if c.change_type == ChangeType.MERGE)
    pending_count = sum(1 for c in changes if c.status == ChangeStatus.PENDING)
    approved_count = sum(1 for c in changes if c.status == ChangeStatus.APPROVED)

    last_change = max((c.created_at for c in changes), default=None)
    last_changed_by = None
    if changes:
        last_c = max(changes, key=lambda c: c.created_at)
        last_changed_by = last_c.changed_by_user_id

    return CIChangeHistory(
        ci_id=ci_id,
        total_changes=len(changes),
        create_count=create_count,
        update_count=update_count,
        delete_count=delete_count,
        merge_count=merge_count,
        last_change=last_change,
        last_changed_by=last_changed_by,
        pending_approvals=pending_count,
        approved_changes=approved_count,
    )


# ============================================================================
# CI Integrity Validation
# ============================================================================

def create_integrity_issue(
    session: Session,
    ci_id: str,
    issue_type: str,
    severity: str,
    description: str,
    related_ci_ids: Optional[List[str]] = None,
) -> TbCIIntegrityIssue:
    """Create a CI integrity issue."""
    issue = TbCIIntegrityIssue(
        ci_id=ci_id,
        issue_type=issue_type,
        severity=severity,
        description=description,
        related_ci_ids=json.dumps(related_ci_ids) if related_ci_ids else None,
    )
    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


def get_integrity_issues(
    session: Session,
    ci_id: Optional[str] = None,
    resolved: Optional[bool] = None,
) -> List[TbCIIntegrityIssue]:
    """Get integrity issues for a CI."""
    statement = select(TbCIIntegrityIssue)

    if ci_id:
        statement = statement.where(TbCIIntegrityIssue.ci_id == ci_id)
    if resolved is not None:
        statement = statement.where(TbCIIntegrityIssue.is_resolved == resolved)

    statement = statement.order_by(TbCIIntegrityIssue.detected_at.desc())
    return session.exec(statement).all()


def resolve_integrity_issue(
    session: Session,
    issue_id: str,
    resolved_by_user_id: str,
    resolution_notes: Optional[str] = None,
) -> Optional[TbCIIntegrityIssue]:
    """Resolve a CI integrity issue."""
    issue = session.get(TbCIIntegrityIssue, issue_id)
    if not issue:
        return None

    issue.is_resolved = True
    issue.resolved_by_user_id = resolved_by_user_id
    issue.resolved_at = datetime.now(timezone.utc)
    issue.resolution_notes = resolution_notes
    issue.updated_at = datetime.now(timezone.utc)

    session.add(issue)
    session.commit()
    session.refresh(issue)
    return issue


def get_integrity_summary(session: Session, ci_id: str) -> CIIntegritySummary:
    """Get integrity summary for a CI."""
    issues = get_integrity_issues(session, ci_id=ci_id, resolved=False)

    warning_count = sum(1 for i in issues if i.severity == "warning")
    error_count = sum(1 for i in issues if i.severity == "error")

    # Determine overall status
    if error_count > 0:
        status = IntegrityStatus.ERROR
    elif warning_count > 0:
        status = IntegrityStatus.WARNING
    else:
        status = IntegrityStatus.VALID

    # Check for duplicates
    duplicates = get_duplicates_for_ci(session, ci_id)
    duplicate_count = sum(1 for d in duplicates if not d.is_merged)

    last_validation = None
    if issues:
        last_validation = max((i.detected_at for i in issues))

    requires_review = error_count > 0 or len([d for d in duplicates if d.is_confirmed and not d.is_merged]) > 0

    return CIIntegritySummary(
        ci_id=ci_id,
        integrity_status=status,
        issue_count=len(issues),
        warning_count=warning_count,
        error_count=error_count,
        duplicate_count=duplicate_count,
        last_validation=last_validation,
        requires_review=requires_review,
    )


# ============================================================================
# Duplicate Detection & Management
# ============================================================================

def create_duplicate_entry(
    session: Session,
    ci_id_1: str,
    ci_id_2: str,
    similarity_score: float,
    match_fields: Optional[List[str]] = None,
) -> TbCIDuplicate:
    """Create a duplicate detection entry."""
    duplicate = TbCIDuplicate(
        ci_id_1=ci_id_1,
        ci_id_2=ci_id_2,
        similarity_score=similarity_score,
        match_fields=json.dumps(match_fields) if match_fields else None,
    )
    session.add(duplicate)
    session.commit()
    session.refresh(duplicate)
    return duplicate


def get_duplicates_for_ci(session: Session, ci_id: str) -> List[TbCIDuplicate]:
    """Get all duplicates for a CI."""
    statement = select(TbCIDuplicate).where(
        (TbCIDuplicate.ci_id_1 == ci_id) | (TbCIDuplicate.ci_id_2 == ci_id)
    )
    return session.exec(statement.order_by(TbCIDuplicate.similarity_score.desc())).all()


def confirm_duplicate(
    session: Session,
    duplicate_id: str,
    confirmed_by_user_id: str,
    action: str = "review",  # merge, ignore, review
    merge_into_ci_id: Optional[str] = None,
) -> Optional[TbCIDuplicate]:
    """Confirm a duplicate detection."""
    duplicate = session.get(TbCIDuplicate, duplicate_id)
    if not duplicate:
        return None

    duplicate.is_confirmed = True
    duplicate.confirmed_by_user_id = confirmed_by_user_id
    duplicate.confirmed_at = datetime.now(timezone.utc)

    if action == "merge" and merge_into_ci_id:
        duplicate.is_merged = True
        duplicate.merged_into_ci_id = merge_into_ci_id

    duplicate.updated_at = datetime.now(timezone.utc)

    session.add(duplicate)
    session.commit()
    session.refresh(duplicate)
    return duplicate


def get_duplicate_statistics(session: Session) -> Dict[str, Any]:
    """Get global duplicate statistics."""
    statement = select(TbCIDuplicate)
    duplicates = session.exec(statement).all()

    total = len(duplicates)
    confirmed = sum(1 for d in duplicates if d.is_confirmed)
    merged = sum(1 for d in duplicates if d.is_merged)
    pending = total - confirmed

    avg_similarity = (
        sum(d.similarity_score for d in duplicates) / total if total > 0 else 0
    )

    return {
        "total_duplicates": total,
        "confirmed": confirmed,
        "merged": merged,
        "pending": pending,
        "average_similarity": round(avg_similarity, 3),
    }


# ============================================================================
# Overall Statistics
# ============================================================================

def get_change_statistics(session: Session, days: int = 30) -> CIChangeStats:
    """Get change statistics for the last N days."""
    datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_date_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date_week = cutoff_date_today - timedelta(days=7)

    # All changes
    all_changes_stmt = select(TbCIChange)
    all_changes = session.exec(all_changes_stmt).all()

    # By type
    by_type = {}
    for change_type in ChangeType:
        count = sum(1 for c in all_changes if c.change_type == change_type)
        by_type[change_type.value] = count

    # By status
    by_status = {}
    for status in ChangeStatus:
        count = sum(1 for c in all_changes if c.status == status)
        by_status[status.value] = count

    # Today's changes
    changes_today = sum(1 for c in all_changes if c.created_at >= cutoff_date_today)

    # This week's changes
    changes_this_week = sum(1 for c in all_changes if c.created_at >= cutoff_date_week)

    # Most changed CI
    ci_change_counts = {}
    for change in all_changes:
        ci_change_counts[change.ci_id] = ci_change_counts.get(change.ci_id, 0) + 1

    most_changed_ci = max(ci_change_counts, key=ci_change_counts.get) if ci_change_counts else None

    # Most active user
    user_counts = {}
    for change in all_changes:
        user_counts[change.changed_by_user_id] = user_counts.get(change.changed_by_user_id, 0) + 1

    most_active_user = max(user_counts, key=user_counts.get) if user_counts else None

    return CIChangeStats(
        total_changes=len(all_changes),
        pending_changes=by_status.get("pending", 0),
        approved_changes=by_status.get("approved", 0),
        rejected_changes=by_status.get("rejected", 0),
        by_type=by_type,
        by_status=by_status,
        changes_today=changes_today,
        changes_this_week=changes_this_week,
        most_changed_ci=most_changed_ci,
        most_active_user=most_active_user,
    )


def validate_ci_integrity(
    session: Session,
    ci_id: str,
    ci_data: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """Validate CI integrity against predefined rules."""
    issues = []

    # Check required fields
    required_fields = ["name", "type", "status"]
    for field in required_fields:
        if field not in ci_data or not ci_data[field]:
            issues.append(f"Missing or empty required field: {field}")

    # Check field types
    if "type" in ci_data and not isinstance(ci_data["type"], str):
        issues.append("Field 'type' must be a string")

    # Check for suspicious patterns
    if "name" in ci_data:
        name = str(ci_data["name"]).lower()
        if "test" in name or "temp" in name or "dummy" in name:
            issues.append(f"Warning: CI name contains test/temporary keyword: {ci_data['name']}")

    # Create issues in database
    for issue_desc in issues:
        severity = "error" if "Missing" in issue_desc else "warning"
        create_integrity_issue(
            session,
            ci_id=ci_id,
            issue_type="validation",
            severity=severity,
            description=issue_desc,
        )

    is_valid = not any("Missing" in i for i in issues)
    return is_valid, issues
