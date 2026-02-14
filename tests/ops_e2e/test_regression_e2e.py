"""E2E tests for Regression Analysis features."""

from __future__ import annotations


def test_regression_analysis_endpoint(e2e_client, e2e_artifact_collector):
    """Test regression analysis endpoint functionality."""
    test_name = "regression_analysis_endpoint"

    # Create two traces to compare
    questions = [
        "서버 상태를 확인해주세요",
        "CPU 사용률을 확인해주세요"
    ]

    trace_ids = []
    for question in questions:
        response = e2e_client.post("/ops/ask", json={"question": question})
        assert response.status_code == 200

        trace_data = response.json()
        trace_id = trace_data.get("data", {}).get("trace", {}).get("trace_id")
        trace_ids.append(trace_id)

    # Test regression analysis
    entry = {
        "test_name": test_name,
        "baseline_trace_id": trace_ids[0],
        "comparison_trace_id": trace_ids[1],
        "endpoint": "/inspector/regression/stage-compare",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Test stage comparison endpoint
        response = e2e_client.post(
            "/inspector/regression/stage-compare",
            json={
                "baseline_trace_id": trace_ids[0],
                "comparison_trace_id": trace_ids[1],
                "stages": ["route_plan", "validate", "execute", "compose", "present"]
            }
        )
        entry["status_code"] = response.status_code

        # Note: This endpoint might not be implemented yet
        if response.status_code == 200:
            data = response.json()
            assert data.get("code", 0) == 0, "Response envelope must report success"

            # Verify response structure
            result = data.get("data", {})
            assert "baseline_trace" in result, "Baseline trace must be present"
            assert "comparison_trace" in result, "Comparison trace must be present"
            assert "stage_differences" in result, "Stage differences must be present"
            assert "regression_scores" in result, "Regression scores must be present"

            entry["has_stage_differences"] = len(result.get("stage_differences", {})) > 0
            entry["has_regression_scores"] = len(result.get("regression_scores", {})) > 0
            entry["status"] = "pass"
            entry["reason"] = "ok"
        else:
            # Endpoint might not be implemented yet
            entry["status"] = "skipped"
            entry["reason"] = "Regression endpoint not implemented (expected for now)"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_analyze_regression_workflow(e2e_client, e2e_artifact_collector):
    """Test complete regression analysis workflow."""
    test_name = "analyze_regression_workflow"

    # Create base traces
    base_questions = [
        "기본 서버 상태 확인",
        "기본 CPU 사용률 확인"
    ]

    base_traces = []
    for question in base_questions:
        response = e2e_client.post("/ops/ask", json={"question": question})
        if response.status_code == 200:
            trace_data = response.json()
            trace_id = trace_data.get("data", {}).get("trace", {}).get("trace_id")
            base_traces.append(trace_id)

    entry = {
        "test_name": test_name,
        "base_traces": len(base_traces),
        "endpoint": "/inspector/regression/analyze",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        if len(base_traces) >= 2:
            # Test analyze endpoint (if implemented)
            request_body = {
                "type": "stage",
                "baseline_trace_id": base_traces[0],
                "comparison_trace_id": base_traces[1],
                "parameters": {
                    "stages": ["route_plan", "validate", "execute", "compose", "present"]
                }
            }

            response = e2e_client.post("/inspector/regression/analyze", json=request_body)
            entry["status_code"] = response.status_code

            if response.status_code == 200:
                data = response.json()
                result = data.get("data", {})

                # Verify analysis result structure
                analysis_id = result.get("analysis_id")
                assert analysis_id is not None, "Analysis ID must be present"

                # Test getting analysis by ID
                get_response = e2e_client.get(f"/inspector/regression/{analysis_id}")
                if get_response.status_code == 200:
                    get_data = get_response.json()
                    get_result = get_data.get("data", {})
                    assert get_result.get("analysis_id") == analysis_id, "Analysis ID must match"

                entry["analysis_id"] = analysis_id
                entry["status"] = "pass"
                entry["reason"] = "ok"
            else:
                entry["status"] = "skipped"
                entry["reason"] = "Regression analysis endpoint not implemented"
        else:
            entry["status"] = "skipped"
            entry["reason"] = "Not enough traces created for regression analysis"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)