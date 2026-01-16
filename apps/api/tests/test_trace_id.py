"""Test trace_id handling in API responses"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_ops_query_includes_trace_id(client):
    """Test that /ops/query response always includes trace_id in headers"""
    response = client.post(
        "/ops/query",
        json={
            "mode": "config",
            "question": "테스트 질문",
        },
    )
    assert response.status_code == 200

    # Response headers should contain trace ID
    assert "x-trace-id" in response.headers, "trace_id should always be present in response headers"
    trace_id = response.headers.get("x-trace-id")
    assert trace_id is not None and trace_id != "", "trace_id should be a non-empty value"


def test_ops_ci_ask_includes_trace_id(client):
    """Test that /ops/ci/ask response includes trace_id headers"""
    response = client.post(
        "/ops/ci/ask",
        json={
            "question": "CI 테스트 질문",
        },
    )
    # Response should have trace_id header (even if endpoint has issues)
    assert "x-trace-id" in response.headers
    trace_id = response.headers.get("x-trace-id")
    assert trace_id is not None and trace_id != "", "trace_id should always be in headers"


def test_trace_id_persists_across_requests(client):
    """Test that custom trace_id is preserved from request headers"""
    custom_trace_id = "test-trace-123456"
    response = client.post(
        "/ops/query",
        json={
            "mode": "config",
            "question": "테스트 질문",
        },
        headers={
            "X-Trace-ID": custom_trace_id,
        },
    )
    assert response.status_code == 200

    # Response header should echo back the trace ID
    assert response.headers.get("x-trace-id") == custom_trace_id, "Custom trace_id from header should be preserved"


def test_parent_trace_id_in_response(client):
    """Test that parent_trace_id is included in response when provided"""
    custom_trace_id = "test-trace-123456"
    custom_parent_trace_id = "parent-trace-789"

    response = client.post(
        "/ops/query",
        json={
            "mode": "config",
            "question": "테스트 질문",
        },
        headers={
            "X-Trace-ID": custom_trace_id,
            "X-Parent-Trace-ID": custom_parent_trace_id,
        },
    )
    assert response.status_code == 200

    # Response headers should echo back the trace IDs
    assert response.headers.get("x-trace-id") == custom_trace_id
    assert response.headers.get("x-parent-trace-id") == custom_parent_trace_id, "Parent trace ID from header should be preserved"
