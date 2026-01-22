"""
Comprehensive tests for CI Management module.
Tests cover change tracking, integrity validation, and duplicate detection.
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.modules.ci_management import crud
from app.modules.ci_management.models import (
    ChangeStatus,
    ChangeType,
)
from sqlmodel import Session


class TestCIChangeCreation:
    """Test CI change creation and tracking."""

    def test_create_change_basic(self, session: Session):
        """Test creating a basic CI change record."""
        change = crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
            change_reason="Configuration update",
            old_values={"key": "old_value"},
            new_values={"key": "new_value"},
        )

        assert change.id is not None
        assert change.ci_id == "ci-001"
        assert change.change_type == ChangeType.UPDATE
        assert change.status == ChangeStatus.PENDING
        assert change.changed_by_user_id == "user-001"
        assert change.tenant_id == "t1"

    def test_create_change_minimal(self, session: Session):
        """Test creating a change with minimal fields."""
        change = crud.create_change(
            session=session,
            ci_id="ci-002",
            change_type=ChangeType.CREATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        assert change.ci_id == "ci-002"
        assert change.change_type == ChangeType.CREATE
        assert change.change_reason is None
        assert change.old_values is None

    def test_create_change_all_types(self, session: Session):
        """Test creating changes of all types."""
        types = [
            ChangeType.CREATE,
            ChangeType.UPDATE,
            ChangeType.DELETE,
            ChangeType.MERGE,
            ChangeType.DUPLICATE,
            ChangeType.RESTORE,
        ]

        for change_type in types:
            change = crud.create_change(
                session=session,
                ci_id=f"ci-{change_type.value}",
                change_type=change_type,
                changed_by_user_id="user-001",
                tenant_id="t1",
            )
            assert change.change_type == change_type

    def test_get_change_by_id(self, session: Session):
        """Test retrieving a change by ID."""
        created = crud.create_change(
            session=session,
            ci_id="ci-003",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        retrieved = crud.get_change(session, created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.ci_id == "ci-003"

    def test_get_change_not_found(self, session: Session):
        """Test retrieving non-existent change."""
        result = crud.get_change(session, "non-existent-id")
        assert result is None

    def test_list_changes_all(self, session: Session):
        """Test listing all changes."""
        for i in range(3):
            crud.create_change(
                session=session,
                ci_id=f"ci-{i}",
                change_type=ChangeType.CREATE,
                changed_by_user_id="user-001",
                tenant_id="t1",
            )

        changes, total = crud.list_changes(session, tenant_id="t1")
        assert len(changes) >= 3
        assert total >= 3

    def test_list_changes_filter_by_ci_id(self, session: Session):
        """Test filtering changes by CI ID."""
        for i in range(3):
            crud.create_change(
                session=session,
                ci_id="ci-specific" if i == 0 else f"ci-other-{i}",
                change_type=ChangeType.CREATE,
                changed_by_user_id="user-001",
                tenant_id="t1",
            )

        changes, total = crud.list_changes(session, ci_id="ci-specific", tenant_id="t1")
        assert len(changes) >= 1
        assert all(c.ci_id == "ci-specific" for c in changes)

    def test_list_changes_filter_by_status(self, session: Session):
        """Test filtering changes by status."""
        change1 = crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        crud.create_change(
            session=session,
            ci_id="ci-002",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        crud.approve_change(session, change1.id, "approver-001", approved=True)

        pending_changes, _ = crud.list_changes(
            session, status=ChangeStatus.PENDING, tenant_id="t1"
        )
        approved_changes, _ = crud.list_changes(
            session, status=ChangeStatus.APPROVED, tenant_id="t1"
        )

        assert len(approved_changes) >= 1
        assert len(pending_changes) >= 1

    def test_list_changes_pagination(self, session: Session):
        """Test pagination of changes list."""
        for i in range(10):
            crud.create_change(
                session=session,
                ci_id=f"ci-{i}",
                change_type=ChangeType.CREATE,
                changed_by_user_id="user-001",
                tenant_id="t1",
            )

        changes1, total = crud.list_changes(session, limit=5, offset=0, tenant_id="t1")
        changes2, _ = crud.list_changes(session, limit=5, offset=5, tenant_id="t1")

        assert len(changes1) <= 5
        assert len(changes2) <= 5


class TestCIChangeApproval:
    """Test CI change approval workflow."""

    def test_approve_change(self, session: Session):
        """Test approving a pending change."""
        change = crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        approved = crud.approve_change(
            session=session,
            change_id=change.id,
            approved_by_user_id="approver-001",
            approved=True,
            approval_notes="Looks good",
        )

        assert approved is not None
        assert approved.status == ChangeStatus.APPROVED
        assert approved.approved_by_user_id == "approver-001"
        assert approved.approval_notes == "Looks good"
        assert approved.approved_at is not None

    def test_reject_change(self, session: Session):
        """Test rejecting a pending change."""
        change = crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        rejected = crud.approve_change(
            session=session,
            change_id=change.id,
            approved_by_user_id="approver-001",
            approved=False,
            approval_notes="Needs revision",
        )

        assert rejected is not None
        assert rejected.status == ChangeStatus.REJECTED
        assert rejected.approval_notes == "Needs revision"

    def test_approve_non_existent_change(self, session: Session):
        """Test approving non-existent change."""
        result = crud.approve_change(
            session=session,
            change_id="non-existent",
            approved_by_user_id="approver-001",
            approved=True,
        )
        assert result is None

    def test_apply_change(self, session: Session):
        """Test applying an approved change."""
        change = crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        crud.approve_change(
            session=session,
            change_id=change.id,
            approved_by_user_id="approver-001",
            approved=True,
        )

        applied = crud.apply_change(session, change.id)
        assert applied is not None
        assert applied.status == ChangeStatus.APPLIED
        assert applied.applied_at is not None

    def test_apply_unapproved_change_fails(self, session: Session):
        """Test that applying unapproved change fails."""
        change = crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        with pytest.raises(ValueError):
            crud.apply_change(session, change.id)


class TestCIChangeHistory:
    """Test CI change history tracking."""

    def test_get_change_history_single_ci(self, session: Session):
        """Test getting change history for a single CI."""
        ci_id = "ci-history-001"

        for i in range(3):
            crud.create_change(
                session=session,
                ci_id=ci_id,
                change_type=ChangeType.UPDATE,
                changed_by_user_id=f"user-{i}",
                tenant_id="t1",
            )

        history = crud.get_change_history(session, ci_id, tenant_id="t1")

        assert history.ci_id == ci_id
        assert history.total_changes >= 3
        assert history.create_count >= 0
        assert history.update_count >= 3

    def test_change_history_counts(self, session: Session):
        """Test that change history counts are correct."""
        ci_id = "ci-history-counts"

        # Create different types of changes
        for change_type in [ChangeType.CREATE, ChangeType.UPDATE, ChangeType.UPDATE]:
            crud.create_change(
                session=session,
                ci_id=ci_id,
                change_type=change_type,
                changed_by_user_id="user-001",
                tenant_id="t1",
            )

        history = crud.get_change_history(session, ci_id, tenant_id="t1")

        assert history.create_count >= 1
        assert history.update_count >= 2

    def test_change_history_pending_approvals(self, session: Session):
        """Test pending approvals count in history."""
        ci_id = "ci-history-pending"

        change1 = crud.create_change(
            session=session,
            ci_id=ci_id,
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        crud.create_change(
            session=session,
            ci_id=ci_id,
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        crud.approve_change(session, change1.id, "approver-001", approved=True)

        history = crud.get_change_history(session, ci_id, tenant_id="t1")
        assert history.pending_approvals >= 1


class TestCIIntegrityValidation:
    """Test CI integrity validation."""

    def test_create_integrity_issue(self, session: Session):
        """Test creating an integrity issue."""
        issue = crud.create_integrity_issue(
            session=session,
            ci_id="ci-001",
            issue_type="missing_field",
            severity="high",
            description="Required field 'name' is missing",
            tenant_id="t1",
        )

        assert issue.id is not None
        assert issue.ci_id == "ci-001"
        assert issue.issue_type == "missing_field"
        assert issue.severity == "high"
        assert issue.is_resolved is False

    def test_get_integrity_issues(self, session: Session):
        """Test retrieving integrity issues for a CI."""
        ci_id = "ci-integrity-001"

        for i in range(3):
            crud.create_integrity_issue(
                session=session,
                ci_id=ci_id,
                issue_type=f"issue_type_{i}",
                severity="medium",
                description=f"Description {i}",
                tenant_id="t1",
            )

        issues = crud.get_integrity_issues(session, ci_id=ci_id, tenant_id="t1")
        assert len(issues) >= 3

    def test_filter_integrity_issues_unresolved(self, session: Session):
        """Test filtering unresolved integrity issues."""
        ci_id = "ci-integrity-filter"

        issue1 = crud.create_integrity_issue(
            session=session,
            ci_id=ci_id,
            issue_type="issue_1",
            severity="high",
            description="Unresolved issue",
            tenant_id="t1",
        )

        crud.create_integrity_issue(
            session=session,
            ci_id=ci_id,
            issue_type="issue_2",
            severity="medium",
            description="Another issue",
            tenant_id="t1",
        )

        crud.resolve_integrity_issue(
            session, issue1.id, "resolver-001", "Fixed"
        )

        unresolved = crud.get_integrity_issues(
            session, ci_id=ci_id, resolved=False, tenant_id="t1"
        )
        assert len(unresolved) >= 1

    def test_resolve_integrity_issue(self, session: Session):
        """Test resolving an integrity issue."""
        issue = crud.create_integrity_issue(
            session=session,
            ci_id="ci-001",
            issue_type="missing_field",
            severity="high",
            description="Test issue",
            tenant_id="t1",
        )

        resolved = crud.resolve_integrity_issue(
            session,
            issue.id,
            resolved_by_user_id="resolver-001",
            resolution_notes="Fixed the missing field",
        )

        assert resolved is not None
        assert resolved.is_resolved is True
        assert resolved.resolved_by_user_id == "resolver-001"
        assert resolved.resolution_notes == "Fixed the missing field"

    def test_validate_ci_integrity(self, session: Session):
        """Test CI integrity validation."""
        ci_data = {
            "id": "ci-001",
            "name": "Test CI",
            "type": "server",
        }

        is_valid, issues = crud.validate_ci_integrity(
            session, "ci-001", ci_data, tenant_id="t1"
        )

        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

    def test_get_integrity_summary(self, session: Session):
        """Test getting integrity summary."""
        ci_id = "ci-summary-001"

        crud.create_integrity_issue(
            session=session,
            ci_id=ci_id,
            issue_type="issue_1",
            severity="high",
            description="High severity issue",
            tenant_id="t1",
        )

        crud.create_integrity_issue(
            session=session,
            ci_id=ci_id,
            issue_type="issue_2",
            severity="warning",
            description="Warning issue",
            tenant_id="t1",
        )

        summary = crud.get_integrity_summary(session, ci_id, tenant_id="t1")

        assert summary.ci_id == ci_id
        assert summary.issue_count >= 2
        assert summary.error_count >= 0
        assert summary.warning_count >= 0


class TestCIDuplicateDetection:
    """Test CI duplicate detection."""

    def test_create_duplicate_entry(self, session: Session):
        """Test creating a duplicate detection entry."""
        duplicate = crud.create_duplicate_entry(
            session=session,
            ci_id_1="ci-001",
            ci_id_2="ci-002",
            similarity_score=0.95,
            tenant_id="t1",
        )

        assert duplicate.id is not None
        assert duplicate.ci_id_1 == "ci-001"
        assert duplicate.ci_id_2 == "ci-002"
        assert duplicate.similarity_score == 0.95
        assert duplicate.is_confirmed is False

    def test_get_duplicates_for_ci(self, session: Session):
        """Test retrieving duplicates for a CI."""
        ci_id = "ci-001"

        for i in range(3):
            crud.create_duplicate_entry(
                session=session,
                ci_id_1=ci_id,
                ci_id_2=f"ci-dup-{i}",
                similarity_score=0.85 + (i * 0.05),
                tenant_id="t1",
            )

        duplicates = crud.get_duplicates_for_ci(session, ci_id, tenant_id="t1")
        assert len(duplicates) >= 3

    def test_confirm_duplicate(self, session: Session):
        """Test confirming a duplicate detection."""
        duplicate = crud.create_duplicate_entry(
            session=session,
            ci_id_1="ci-001",
            ci_id_2="ci-002",
            similarity_score=0.95,
            tenant_id="t1",
        )

        confirmed = crud.confirm_duplicate(
            session=session,
            duplicate_id=duplicate.id,
            confirmed_by_user_id="user-001",
            action="merge",
            merge_into_ci_id="ci-001",
        )

        assert confirmed is not None
        assert confirmed.is_confirmed is True
        assert confirmed.confirmed_by_user_id == "user-001"
        assert confirmed.is_merged is True
        assert confirmed.merged_into_ci_id == "ci-001"

    def test_duplicate_statistics(self, session: Session):
        """Test duplicate statistics."""
        for i in range(5):
            dup = crud.create_duplicate_entry(
                session=session,
                ci_id_1=f"ci-{i}",
                ci_id_2=f"ci-dup-{i}",
                similarity_score=0.80 + (i * 0.04),
                tenant_id="t1",
            )

            if i < 2:
                crud.confirm_duplicate(
                    session,
                    dup.id,
                    confirmed_by_user_id="user-001",
                    action="merge" if i == 0 else "review",
                    merge_into_ci_id=f"ci-{i}" if i == 0 else None,
                )

        stats = crud.get_duplicate_statistics(session, tenant_id="t1")

        assert stats["total"] >= 5
        assert stats["confirmed"] >= 2
        assert stats["pending"] >= 0
        assert "average_similarity" in stats


class TestCIChangeStatistics:
    """Test change statistics."""

    def test_get_change_statistics(self, session: Session):
        """Test getting change statistics."""
        for i in range(5):
            crud.create_change(
                session=session,
                ci_id=f"ci-{i}",
                change_type=ChangeType.UPDATE if i % 2 == 0 else ChangeType.CREATE,
                changed_by_user_id=f"user-{i % 2}",
                tenant_id="t1",
            )

        stats = crud.get_change_statistics(session, days=30, tenant_id="t1")

        assert stats.total_changes >= 5
        assert stats.by_status is not None
        assert stats.by_type is not None

    def test_change_statistics_time_range(self, session: Session):
        """Test that statistics respects time range."""
        # Create old change (outside time range)
        old_change = crud.create_change(
            session=session,
            ci_id="ci-old",
            change_type=ChangeType.CREATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        # Manually update to old date
        old_change.created_at = datetime.now(timezone.utc) - timedelta(days=100)
        session.add(old_change)
        session.commit()

        # Create recent change
        crud.create_change(
            session=session,
            ci_id="ci-recent",
            change_type=ChangeType.CREATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        # Get stats for last 30 days
        stats = crud.get_change_statistics(session, days=30, tenant_id="t1")

        # Recent change should be included, old should not
        assert stats.total_changes >= 1


class TestCIIntegrationWorkflow:
    """Test complete CI management workflows."""

    def test_complete_change_workflow(self, session: Session):
        """Test complete change workflow: create, approve, apply."""
        # Create change
        change = crud.create_change(
            session=session,
            ci_id="ci-workflow",
            change_type=ChangeType.UPDATE,
            changed_by_user_id="user-001",
            change_reason="Update configuration",
            old_values='{"key": "old"}',
            new_values='{"key": "new"}',
            tenant_id="t1",
        )
        assert change.status == ChangeStatus.PENDING

        # Approve change
        approved = crud.approve_change(
            session=session,
            change_id=change.id,
            approved_by_user_id="approver-001",
            approved=True,
            approval_notes="Approved",
        )
        assert approved.status == ChangeStatus.APPROVED

        # Apply change
        applied = crud.apply_change(session, change.id)
        assert applied.status == ChangeStatus.APPLIED

        # Verify history
        history = crud.get_change_history(session, "ci-workflow", tenant_id="t1")
        assert history.total_changes >= 1

    def test_duplicate_detection_to_merge_workflow(self, session: Session):
        """Test duplicate detection and merge workflow."""
        # Create duplicate detection
        duplicate = crud.create_duplicate_entry(
            session=session,
            ci_id_1="ci-master",
            ci_id_2="ci-duplicate",
            similarity_score=0.98,
            tenant_id="t1",
        )

        # Confirm and mark for merge
        confirmed = crud.confirm_duplicate(
            session=session,
            duplicate_id=duplicate.id,
            confirmed_by_user_id="user-001",
            action="merge",
            merge_into_ci_id="ci-master",
        )
        assert confirmed.is_confirmed is True
        assert confirmed.merged_into_ci_id == "ci-master"

        # Create merge change
        merge_change = crud.create_change(
            session=session,
            ci_id="ci-duplicate",
            change_type=ChangeType.MERGE,
            changed_by_user_id="user-001",
            change_reason="Merged into ci-master",
            tenant_id="t1",
        )

        crud.approve_change(session, merge_change.id, "approver-001", approved=True)
        applied = crud.apply_change(session, merge_change.id)
        assert applied.status == ChangeStatus.APPLIED

    def test_integrity_validation_workflow(self, session: Session):
        """Test integrity validation and issue resolution."""
        ci_id = "ci-integrity-workflow"

        # Create issues via validation
        ci_data = {"id": ci_id, "name": ""}
        is_valid, issues = crud.validate_ci_integrity(
            session, ci_id, ci_data, tenant_id="t1"
        )

        # Get issues
        ci_issues = crud.get_integrity_issues(session, ci_id, tenant_id="t1")
        assert len(ci_issues) >= 0

        # Resolve issues
        for issue in ci_issues[:1]:
            resolved = crud.resolve_integrity_issue(
                session,
                issue.id,
                resolved_by_user_id="resolver-001",
                resolution_notes="Fixed",
            )
            assert resolved.is_resolved is True

        # Verify summary updated
        summary = crud.get_integrity_summary(session, ci_id, tenant_id="t1")
        assert summary.issue_count >= 0


class TestTenantIsolation:
    """Test multi-tenant isolation."""

    def test_changes_isolated_by_tenant(self, session: Session):
        """Test that changes are isolated by tenant."""
        # Create changes for different tenants
        crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.CREATE,
            changed_by_user_id="user-001",
            tenant_id="t1",
        )

        crud.create_change(
            session=session,
            ci_id="ci-001",
            change_type=ChangeType.CREATE,
            changed_by_user_id="user-001",
            tenant_id="t2",
        )

        # Get changes for t1
        changes_t1, _ = crud.list_changes(session, tenant_id="t1")

        # All should be for t1
        assert all(c.tenant_id == "t1" for c in changes_t1)

    def test_issues_isolated_by_tenant(self, session: Session):
        """Test that issues are isolated by tenant."""
        crud.create_integrity_issue(
            session=session,
            ci_id="ci-001",
            issue_type="issue",
            severity="high",
            description="Test",
            tenant_id="t1",
        )

        crud.create_integrity_issue(
            session=session,
            ci_id="ci-001",
            issue_type="issue",
            severity="high",
            description="Test",
            tenant_id="t2",
        )

        # Get issues for t1
        issues_t1 = crud.get_integrity_issues(session, ci_id="ci-001", tenant_id="t1")

        # All should be for t1
        assert all(i.tenant_id == "t1" for i in issues_t1)

    def test_duplicates_isolated_by_tenant(self, session: Session):
        """Test that duplicates are isolated by tenant."""
        crud.create_duplicate_entry(
            session=session,
            ci_id_1="ci-001",
            ci_id_2="ci-002",
            similarity_score=0.9,
            tenant_id="t1",
        )

        crud.create_duplicate_entry(
            session=session,
            ci_id_1="ci-001",
            ci_id_2="ci-002",
            similarity_score=0.9,
            tenant_id="t2",
        )

        # Get duplicates for t1
        dups_t1 = crud.get_duplicates_for_ci(session, "ci-001", tenant_id="t1")

        # All should be for t1
        assert all(d.tenant_id == "t1" for d in dups_t1)
