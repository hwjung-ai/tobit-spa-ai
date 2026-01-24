"""Tests for audit log CRUD operations."""

import uuid

from app.modules.audit_log.crud import (
    create_audit_log,
    get_audit_logs_by_parent_trace,
    get_audit_logs_by_resource,
    get_audit_logs_by_trace,
)


def test_list_audit_logs_returns_matching_entries(session):
    """Test listing audit logs filters correctly."""
    # Create test data
    trace_id = str(uuid.uuid4())
    parent_trace_id = str(uuid.uuid4())
    resource_type = "settings"
    resource_id = "ops_mode"

    create_audit_log(
        session=session,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action="update",
        actor="test-suite",
        changes={"value": "test"},
    )
    session.commit()

    # Test CRUD directly
    result = get_audit_logs_by_resource(
        session=session,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=5,
        offset=0,
    )

    assert result is not None
    assert len(result) >= 1
    assert any(log.trace_id == trace_id for log in result)


def test_get_audit_logs_by_trace_and_parent(session):
    """Test retrieving audit logs by trace and parent trace."""
    # Create test data
    trace_id = str(uuid.uuid4())
    parent_trace_id = str(uuid.uuid4())
    resource_type = "settings"
    resource_id = "ops_mode"

    create_audit_log(
        session=session,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action="update",
        actor="test-suite",
        changes={"value": "test"},
    )
    session.commit()

    # Test by trace
    trace_result = get_audit_logs_by_trace(session=session, trace_id=trace_id)
    assert trace_result is not None
    assert len(trace_result) >= 1
    assert any(log.trace_id == trace_id for log in trace_result)

    # Test by parent trace
    parent_result = get_audit_logs_by_parent_trace(
        session=session, parent_trace_id=parent_trace_id
    )
    assert parent_result is not None
    assert len(parent_result) >= 1
    assert any(log.parent_trace_id == parent_trace_id for log in parent_result)
