"""Tests for the audit log read endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.modules.audit_log.crud import create_audit_log
from core.db import get_session_context
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def _seed_audit_log_entry() -> tuple[str, str, str, str]:
    trace_id = str(uuid.uuid4())
    parent_trace_id = str(uuid.uuid4())
    resource_type = "settings"
    resource_id = "ops_mode"
    with get_session_context() as session:
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
    return trace_id, parent_trace_id, resource_type, resource_id


def test_list_audit_logs_returns_matching_entries(client: TestClient):
    trace_id, _, resource_type, resource_id = _seed_audit_log_entry()
    response = client.get(
        "/audit-log",
        params={"resource_type": resource_type, "resource_id": resource_id, "limit": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("data")
    data = payload["data"]
    assert data["paging"]["limit"] == 5
    assert data["paging"]["offset"] == 0
    audit_logs = data["audit_logs"]
    assert any(log["trace_id"] == trace_id for log in audit_logs)


def test_get_audit_logs_by_trace_and_parent(client: TestClient):
    trace_id, parent_trace_id, _, _ = _seed_audit_log_entry()

    trace_response = client.get(f"/audit-log/by-trace/{trace_id}")
    assert trace_response.status_code == 200
    trace_data = trace_response.json()["data"]
    assert trace_data["trace_id"] == trace_id
    assert trace_data["count"] >= 1

    parent_response = client.get(f"/audit-log/by-parent-trace/{parent_trace_id}")
    assert parent_response.status_code == 200
    parent_data = parent_response.json()["data"]
    assert parent_data["parent_trace_id"] == parent_trace_id
    assert parent_data["count"] >= 1
