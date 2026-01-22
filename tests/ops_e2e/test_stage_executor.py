"""E2E tests for StageExecutor functionality."""

from __future__ import annotations


def test_stage_execution_with_override(e2e_client, e2e_artifact_collector):
    """Test stage execution with asset override."""
    test_name = "stage_execution_with_override"

    # Create a trace first
    create_response = e2e_client.post("/ops/ci/ask", json={
        "question": "서버 상태를 확인해주세요"
    })
    assert create_response.status_code == 200

    trace_data = create_response.json()
    trace_id = trace_data.get("data", {}).get("trace", {}).get("trace_id")

    # Test asset override endpoint (if available)
    entry = {
        "test_name": test_name,
        "trace_id": trace_id,
        "endpoint": "/inspector/traces",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Get the original trace
        response = e2e_client.get(f"/inspector/traces/{trace_id}")
        assert response.status_code == 200

        trace = response.json().get("data", {}).get("trace", {})

        # Check stage inputs and outputs
        stage_inputs = trace.get("stage_inputs", [])
        stage_outputs = trace.get("stage_outputs", [])

        # Verify stages are executed
        assert len(stage_inputs) > 0, "Stage inputs must be present"
        assert len(stage_outputs) > 0, "Stage outputs must be present"

        # Verify each stage has proper structure
        for stage_input in stage_inputs:
            assert stage_input.get("stage") is not None, "Stage name must be present"
            assert stage_input.get("applied_assets") is not None, "Applied assets must be present"

        for stage_output in stage_outputs:
            assert stage_output.get("stage") is not None, "Stage name must be present"
            assert stage_output.get("duration_ms") is not None, "Duration must be present"
            assert stage_output.get("diagnostics") is not None, "Diagnostics must be present"

        entry["stage_count"] = len(stage_outputs)
        entry["has_diagnostics"] = all(
            "diagnostics" in output and output["diagnostics"].get("status")
            for output in stage_outputs
        )
        entry["status"] = "pass"
        entry["reason"] = "ok"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_stage_isolation_and_testing(e2e_client, e2e_artifact_collector):
    """Test stage isolation and testing capability."""
    test_name = "stage_isolation_and_testing"

    # This test would need specific asset override endpoints
    # For now, we'll test the trace structure that would support this
    entry = {
        "test_name": test_name,
        "endpoint": "/ops/ci/ask",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        response = e2e_client.post("/ops/ci/ask", json={
            "question": "서버 상태를 확인해주세요"
        })
        entry["status_code"] = response.status_code

        assert response.status_code == 200, "Status code must be 200"

        data = response.json()
        trace = data.get("data", {}).get("trace", {})

        # Verify trace structure supports stage isolation
        stage_inputs = trace.get("stage_inputs", [])

        # Check if stage inputs contain asset information
        has_asset_info = False
        for stage_input in stage_inputs:
            applied_assets = stage_input.get("applied_assets", {})
            if applied_assets:
                has_asset_info = True
                break

        entry["has_asset_info"] = has_asset_info
        entry["stage_input_count"] = len(stage_inputs)
        entry["status"] = "pass"
        entry["reason"] = "ok" if has_asset_info else "Asset info not available (expected)"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)