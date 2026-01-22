"""
API Router for CI Management endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core.db import get_session
from core.tenant import get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from schemas.common import ResponseEnvelope
from sqlmodel import Session

from . import crud
from .models import (
    ChangeStatus,
    ChangeType,
    CIChangeApprove,
    CIChangeCreate,
    CIChangeHistory,
    CIChangeRead,
    CIChangeStats,
    CIDuplicateConfirm,
    CIDuplicateRead,
    CIIntegrityIssueRead,
    CIIntegritySummary,
)

router = APIRouter(prefix="/api/ci-management", tags=["CI Management"])


# ============================================================================
# CI Change Management Endpoints
# ============================================================================

@router.post("/changes", response_model=ResponseEnvelope[CIChangeRead])
def create_ci_change(
    change: CIChangeCreate,
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Create a new CI change record."""
    try:
        tenant_id = get_current_tenant(request)
        db_change = crud.create_change(
            session=session,
            ci_id=change.ci_id,
            change_type=change.change_type,
            changed_by_user_id=change.changed_by_user_id,
            tenant_id=tenant_id,
            change_reason=change.change_reason,
            old_values=change.old_values,
            new_values=change.new_values,
        )

        return ResponseEnvelope(
            code=201,
            message="CI change created successfully",
            data=CIChangeRead.model_validate(db_change),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/changes/{change_id}", response_model=ResponseEnvelope[CIChangeRead])
def get_ci_change(
    change_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Get a CI change by ID."""
    change = crud.get_change(session, change_id)
    if not change:
        raise HTTPException(status_code=404, detail="CI change not found")

    return ResponseEnvelope(
        code=200,
        message="CI change retrieved successfully",
        data=CIChangeRead.model_validate(change),
    )


@router.get("/changes", response_model=ResponseEnvelope[List[CIChangeRead]])
def list_ci_changes(
    ci_id: Optional[str] = Query(None),
    status: Optional[ChangeStatus] = Query(None),
    change_type: Optional[ChangeType] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """List CI changes with filtering."""
    tenant_id = get_current_tenant(request)
    changes, total = crud.list_changes(
        session,
        ci_id=ci_id,
        status=status,
        change_type=change_type,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )

    return ResponseEnvelope(
        code=200,
        message=f"Retrieved {len(changes)} changes",
        data=[CIChangeRead.model_validate(c) for c in changes],
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.post("/changes/{change_id}/approve", response_model=ResponseEnvelope[CIChangeRead])
def approve_ci_change(
    change_id: str,
    approval: CIChangeApprove,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Approve or reject a CI change."""
    change = crud.approve_change(
        session,
        change_id=change_id,
        approved_by_user_id=approval.approved_by_user_id,
        approved=approval.approved,
        approval_notes=approval.approval_notes,
    )

    if not change:
        raise HTTPException(status_code=404, detail="CI change not found")

    return ResponseEnvelope(
        code=200,
        message="CI change approval processed",
        data=CIChangeRead.model_validate(change),
    )


@router.post("/changes/{change_id}/apply", response_model=ResponseEnvelope[CIChangeRead])
def apply_ci_change(
    change_id: str,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Apply a CI change."""
    try:
        change = crud.apply_change(session, change_id)
        if not change:
            raise HTTPException(status_code=404, detail="CI change not found")

        return ResponseEnvelope(
            code=200,
            message="CI change applied successfully",
            data=CIChangeRead.model_validate(change),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/changes/{ci_id}/history", response_model=ResponseEnvelope[CIChangeHistory])
def get_ci_change_history(
    ci_id: str,
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Get change history for a CI."""
    tenant_id = get_current_tenant(request)
    history = crud.get_change_history(session, ci_id, tenant_id=tenant_id)

    return ResponseEnvelope(
        code=200,
        message="CI change history retrieved",
        data=history,
    )


# ============================================================================
# CI Integrity Validation Endpoints
# ============================================================================

@router.get("/integrity/{ci_id}/issues", response_model=ResponseEnvelope[List[CIIntegrityIssueRead]])
def get_ci_integrity_issues(
    ci_id: str,
    resolved: Optional[bool] = Query(None),
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Get integrity issues for a CI."""
    tenant_id = get_current_tenant(request)
    issues = crud.get_integrity_issues(session, ci_id=ci_id, resolved=resolved, tenant_id=tenant_id)

    return ResponseEnvelope(
        code=200,
        message=f"Retrieved {len(issues)} integrity issues",
        data=[CIIntegrityIssueRead.model_validate(i) for i in issues],
    )


@router.get("/integrity/{ci_id}/summary", response_model=ResponseEnvelope[CIIntegritySummary])
def get_ci_integrity_summary(
    ci_id: str,
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Get integrity summary for a CI."""
    tenant_id = get_current_tenant(request)
    summary = crud.get_integrity_summary(session, ci_id, tenant_id=tenant_id)

    return ResponseEnvelope(
        code=200,
        message="CI integrity summary retrieved",
        data=summary,
    )


@router.post("/integrity/{issue_id}/resolve", response_model=ResponseEnvelope[CIIntegrityIssueRead])
def resolve_integrity_issue(
    issue_id: str,
    resolved_by_user_id: str = Query(...),
    resolution_notes: str = Query(None),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Resolve an integrity issue."""
    issue = crud.resolve_integrity_issue(
        session,
        issue_id=issue_id,
        resolved_by_user_id=resolved_by_user_id,
        resolution_notes=resolution_notes,
    )

    if not issue:
        raise HTTPException(status_code=404, detail="Integrity issue not found")

    return ResponseEnvelope(
        code=200,
        message="Integrity issue resolved",
        data=CIIntegrityIssueRead.model_validate(issue),
    )


# ============================================================================
# CI Duplicate Detection Endpoints
# ============================================================================

@router.get("/duplicates/{ci_id}", response_model=ResponseEnvelope[List[CIDuplicateRead]])
def get_ci_duplicates(
    ci_id: str,
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Get duplicates for a CI."""
    tenant_id = get_current_tenant(request)
    duplicates = crud.get_duplicates_for_ci(session, ci_id, tenant_id=tenant_id)

    return ResponseEnvelope(
        code=200,
        message=f"Retrieved {len(duplicates)} potential duplicates",
        data=[CIDuplicateRead.model_validate(d) for d in duplicates],
    )


@router.post("/duplicates/{duplicate_id}/confirm", response_model=ResponseEnvelope[CIDuplicateRead])
def confirm_duplicate(
    duplicate_id: str,
    confirmation: CIDuplicateConfirm,
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Confirm a duplicate detection."""
    tenant_id = get_current_tenant(request)
    duplicate = crud.confirm_duplicate(
        session,
        duplicate_id=duplicate_id,
        confirmed_by_user_id=confirmation.confirmed_by_user_id,
        tenant_id=tenant_id,
        action=confirmation.action,
        merge_into_ci_id=confirmation.merge_into_ci_id,
    )

    if not duplicate:
        raise HTTPException(status_code=404, detail="Duplicate entry not found")

    return ResponseEnvelope(
        code=200,
        message="Duplicate confirmed",
        data=CIDuplicateRead.model_validate(duplicate),
    )


@router.get("/duplicates/statistics", response_model=ResponseEnvelope)
def get_duplicate_statistics(
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Get duplicate statistics."""
    tenant_id = get_current_tenant(request)
    stats = crud.get_duplicate_statistics(session, tenant_id=tenant_id)

    return ResponseEnvelope(
        code=200,
        message="Duplicate statistics retrieved",
        data=stats,
    )


# ============================================================================
# Overall Statistics Endpoints
# ============================================================================

@router.get("/statistics/changes", response_model=ResponseEnvelope[CIChangeStats])
def get_change_statistics(
    days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
    request: Request = None,  # For dependency injection
) -> ResponseEnvelope:
    """Get change statistics for the last N days."""
    tenant_id = get_current_tenant(request)
    stats = crud.get_change_statistics(session, tenant_id=tenant_id, days=days)

    return ResponseEnvelope(
        code=200,
        message=f"Change statistics for last {days} days",
        data=stats,
    )


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health", response_model=ResponseEnvelope)
def health_check() -> ResponseEnvelope:
    """Health check endpoint."""
    return ResponseEnvelope(
        code=200,
        message="CI Management service is healthy",
        data={"status": "ok", "timestamp": datetime.utcnow().isoformat()},
    )
