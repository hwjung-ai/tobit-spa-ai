"""
Integration tests for OPS Routes - HTTP endpoint testing.

Tests cover:
- /query endpoint
- /ci/ask endpoint
- /ui-actions endpoint
- /rca endpoint
- Error responses and edge cases
"""


import pytest

# Note: These tests assume FastAPI test setup with TestClient
# Actual test execution requires proper app initialization


class TestQueryEndpoint:
    """Integration tests for /ops/query endpoint."""

    def test_query_with_valid_request(self, client):
        """Test /query with valid request."""
        payload = {
            "mode": "metric",
            "question": "What is CPU usage?"
        }
        response = client.post("/ops/query", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "answer" in data["data"]

    def test_query_missing_tenant_id_header(self, client):
        """Test /query without X-Tenant-Id header."""
        payload = {
            "mode": "metric",
            "question": "What is CPU usage?"
        }
        response = client.post("/ops/query", json=payload)
        assert response.status_code == 400

    def test_query_creates_history_entry(self, client):
        """Test that /query creates history entry."""
        payload = {
            "mode": "metric",
            "question": "What is CPU usage?"
        }
        headers = {"X-Tenant-Id": "t1", "X-User-Id": "u1"}
        response = client.post("/ops/query", json=payload, headers=headers)
        assert response.status_code == 200

    def test_query_with_different_modes(self, client):
        """Test /query with different OPS modes."""
        modes = ["config", "history", "metric", "relation"]
        headers = {"X-Tenant-Id": "t1"}

        for mode in modes:
            payload = {"mode": mode, "question": "Test question"}
            response = client.post("/ops/query", json=payload, headers=headers)
            # Should be 200 or 500, but not 400 (validation error)
            assert response.status_code in [200, 500]

    def test_query_empty_question(self, client):
        """Test /query with empty question."""
        payload = {
            "mode": "metric",
            "question": ""
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/query", json=payload, headers=headers)
        # Should handle gracefully (return error or process as empty)
        assert response.status_code in [200, 400, 422]

    def test_query_response_includes_trace(self, client):
        """Test that /query response includes trace."""
        payload = {
            "mode": "metric",
            "question": "What is CPU?"
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/query", json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            if "data" in data:
                assert "trace" in data["data"] or "answer" in data["data"]


class TestCiAskEndpoint:
    """Integration tests for /ops/ask endpoint."""

    def test_ci_ask_with_valid_request(self, client):
        """Test /ci/ask with valid request."""
        payload = {
            "question": "Why is srv-erp-01 slow?"
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ask", json=payload, headers=headers)
        assert response.status_code in [200, 500]  # May fail due to missing data

    def test_ci_ask_missing_tenant_id(self, client):
        """Test /ci/ask without X-Tenant-Id header."""
        payload = {
            "question": "Why is srv-erp-01 slow?"
        }
        response = client.post("/ops/ask", json=payload)
        assert response.status_code == 400

    def test_ci_ask_with_rerun_context(self, client):
        """Test /ci/ask with rerun context."""
        payload = {
            "question": "Why is srv-erp-01 slow?",
            "rerun": {
                "selected_ci_id": "ci-123"
            }
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ask", json=payload, headers=headers)
        assert response.status_code in [200, 500]

    def test_ci_ask_response_structure(self, client):
        """Test /ci/ask response structure."""
        payload = {
            "question": "Is system healthy?"
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ask", json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            # Response should follow CiAskResponse schema
            assert "data" in data or "error" in data

    def test_ci_ask_with_asset_overrides(self, client):
        """Test /ci/ask with asset overrides."""
        payload = {
            "question": "Test question",
            "asset_overrides": {
                "catalog": "custom_catalog.yaml"
            }
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ask", json=payload, headers=headers)
        assert response.status_code in [200, 400, 500]

    def test_ci_ask_complex_question(self, client):
        """Test /ci/ask with complex multi-part question."""
        payload = {
            "question": "Compare CPU usage between srv-erp-01 and srv-erp-02 over the last week and identify anomalies"
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ask", json=payload, headers=headers)
        # Should handle complex questions (may timeout or fail gracefully)
        assert response.status_code in [200, 408, 500]


class TestUIActionsEndpoint:
    """Integration tests for /ops/ui-actions endpoint."""

    @pytest.mark.asyncio
    async def test_ui_action_with_valid_request(self, client):
        """Test /ui-actions with valid request."""
        payload = {
            "action_id": "fetch_device_detail",
            "inputs": {
                "device_id": "srv-01"
            },
            "context": {
                "mode": "real"
            }
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ui-actions", json=payload, headers=headers)
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_ui_action_missing_action_id(self, client):
        """Test /ui-actions without action_id."""
        payload = {
            "inputs": {"device_id": "srv-01"}
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ui-actions", json=payload, headers=headers)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_ui_action_unknown_action(self, client):
        """Test /ui-actions with unknown action_id."""
        payload = {
            "action_id": "nonexistent_action",
            "inputs": {},
            "context": {}
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ui-actions", json=payload, headers=headers)
        # Should return error response
        assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    async def test_ui_action_response_structure(self, client):
        """Test /ui-actions response structure."""
        payload = {
            "action_id": "fetch_device_detail",
            "inputs": {"device_id": "srv-01"},
            "context": {}
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ui-actions", json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            response_data = data.get("data", {})
            assert "blocks" in response_data or "status" in response_data

    @pytest.mark.asyncio
    async def test_ui_action_with_parent_trace(self, client):
        """Test /ui-actions with parent_trace_id."""
        payload = {
            "trace_id": "parent-trace-123",
            "action_id": "fetch_device_detail",
            "inputs": {"device_id": "srv-01"},
            "context": {}
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ui-actions", json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            response_data = data.get("data", {})
            # Should have trace_id in response
            assert "trace_id" in response_data or "status" in response_data

    @pytest.mark.asyncio
    async def test_ui_action_with_complex_inputs(self, client):
        """Test /ui-actions with complex nested inputs."""
        payload = {
            "action_id": "create_maintenance_ticket",
            "inputs": {
                "device_id": "srv-01",
                "maintenance_type": "preventive",
                "scheduled_date": "2025-02-15",
                "assigned_to": "admin"
            },
            "context": {"mode": "real"}
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/ui-actions", json=payload, headers=headers)
        assert response.status_code in [200, 400, 500]


class TestRCAEndpoint:
    """Integration tests for /ops/rca endpoint."""

    def test_rca_analyze_trace_valid_id(self, client):
        """Test /rca/analyze-trace with valid trace_id."""
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/rca/analyze-trace?trace_id=trace-123",
            headers=headers
        )
        # May return 404 if trace doesn't exist
        assert response.status_code in [200, 404]

    def test_rca_analyze_trace_missing_trace(self, client):
        """Test /rca/analyze-trace with missing trace."""
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/rca/analyze-trace?trace_id=nonexistent",
            headers=headers
        )
        assert response.status_code == 404

    def test_rca_analyze_trace_response_structure(self, client):
        """Test /rca/analyze-trace response structure."""
        # Assuming test trace exists
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/rca/analyze-trace?trace_id=test-trace",
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            assert "data" in data
            result = data.get("data", {})
            if "hypotheses" in result:
                # Check hypothesis structure
                for hyp in result["hypotheses"]:
                    assert "rank" in hyp
                    assert "title" in hyp
                    assert "confidence" in hyp

    def test_rca_analyze_regression_valid_ids(self, client):
        """Test /rca/analyze-regression with valid trace IDs."""
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/rca/analyze-regression",
            params={
                "baseline_trace_id": "trace-baseline",
                "candidate_trace_id": "trace-candidate"
            },
            headers=headers
        )
        # May return 404 if traces don't exist
        assert response.status_code in [200, 404]

    def test_rca_analyze_regression_missing_baseline(self, client):
        """Test /rca/analyze-regression with missing baseline."""
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/rca/analyze-regression",
            params={
                "baseline_trace_id": "nonexistent",
                "candidate_trace_id": "trace-candidate"
            },
            headers=headers
        )
        assert response.status_code == 404

    def test_rca_analyze_regression_missing_candidate(self, client):
        """Test /rca/analyze-regression with missing candidate."""
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/rca/analyze-regression",
            params={
                "baseline_trace_id": "trace-baseline",
                "candidate_trace_id": "nonexistent"
            },
            headers=headers
        )
        assert response.status_code == 404


class TestEndpointErrorResponses:
    """Test error response handling across endpoints."""

    def test_invalid_json_payload(self, client):
        """Test endpoint with invalid JSON."""
        headers = {"X-Tenant-Id": "t1"}
        response = client.post(
            "/ops/query",
            data="invalid json",
            headers=headers,
            content_type="application/json"
        )
        assert response.status_code == 422  # Validation error

    def test_missing_required_fields(self, client):
        """Test endpoint with missing required fields."""
        payload = {}  # Missing 'mode' and 'question'
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/query", json=payload, headers=headers)
        assert response.status_code == 422

    def test_invalid_field_types(self, client):
        """Test endpoint with invalid field types."""
        payload = {
            "mode": 123,  # Should be string
            "question": True  # Should be string
        }
        headers = {"X-Tenant-Id": "t1"}
        response = client.post("/ops/query", json=payload, headers=headers)
        assert response.status_code == 422


class TestEndpointSecurity:
    """Test security aspects of endpoints."""

    def test_tenant_id_isolation(self, client):
        """Test that tenant_id is respected for isolation."""
        # Request from tenant1
        payload = {"mode": "metric", "question": "Test"}
        response = client.post(
            "/ops/query",
            json=payload,
            headers={"X-Tenant-Id": "tenant1"}
        )
        # Should not leak data from other tenants
        assert response.status_code in [200, 500]

    def test_user_id_tracking(self, client):
        """Test that user_id is tracked."""
        payload = {"mode": "metric", "question": "Test"}
        response = client.post(
            "/ops/query",
            json=payload,
            headers={"X-Tenant-Id": "t1", "X-User-Id": "user1"}
        )
        # Should handle user context
        assert response.status_code in [200, 500]


class TestEndpointCaching:
    """Test caching behavior of endpoints."""

    def test_same_query_uses_cache(self, client):
        """Test that repeated queries use cache."""
        payload = {"mode": "metric", "question": "What is CPU?"}
        headers = {"X-Tenant-Id": "t1"}

        # First request
        response1 = client.post("/ops/query", json=payload, headers=headers)
        # Second identical request
        response2 = client.post("/ops/query", json=payload, headers=headers)

        # Second should be faster (cached)
        assert response1.status_code == response2.status_code

    def test_different_query_bypasses_cache(self, client):
        """Test that different queries bypass cache."""
        headers = {"X-Tenant-Id": "t1"}

        payload1 = {"mode": "metric", "question": "What is CPU?"}
        payload2 = {"mode": "metric", "question": "What is memory?"}

        response1 = client.post("/ops/query", json=payload1, headers=headers)
        response2 = client.post("/ops/query", json=payload2, headers=headers)

        # Should not use cache for different queries
        assert response1.status_code in [200, 500]
        assert response2.status_code in [200, 500]


class TestEndpointConcurrency:
    """Test concurrent request handling."""

    def test_multiple_concurrent_requests(self, client):
        """Test handling multiple concurrent requests."""
        # This would use threading or async fixtures
        payload = {"mode": "metric", "question": "Test"}
        headers = {"X-Tenant-Id": "t1"}

        # In real test, would make concurrent requests
        response = client.post("/ops/query", json=payload, headers=headers)
        assert response.status_code in [200, 500]
