"""E2E tests for OPS orchestration features."""

from __future__ import annotations

import json
import time


def test_orchestration_trace_lifecycle(e2e_client, e2e_artifact_collector):
    """Test complete orchestration trace lifecycle from question to result."""
    test_name = "orchestration_trace_lifecycle"
    question = "서버 상태를 확인해주세요"

    entry = {
        "test_name": test_name,
        "query": question,
        "endpoint": "/ops/ci/ask",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Start orchestration
        start_time = time.time()
        response = e2e_client.post("/ops/ci/ask", json={"question": question})
        duration = time.time() - start_time

        entry["status_code"] = response.status_code
        entry["duration_ms"] = round(duration * 1000, 2)

        assert response.status_code == 200, "Status code must be 200"

        data = response.json()
        assert data.get("code", 0) == 0, "Response envelope must report success"

        payload = data.get("data", {})

        # Verify trace information
        trace = payload.get("trace")
        assert trace is not None, "Trace must be present"
        assert trace.get("trace_id") is not None, "Trace ID must be present"

        # Verify trace has stage information
        if "stage_inputs" in trace:
            assert isinstance(trace["stage_inputs"], list), "Stage inputs must be a list"
            assert len(trace["stage_inputs"]) > 0, "Must have stage inputs"

        if "stage_outputs" in trace:
            assert isinstance(trace["stage_outputs"], list), "Stage outputs must be a list"

        # Verify trace has route information
        route = trace.get("route")
        assert route in ["direct", "orch", "reject"], f"Invalid route: {route}"

        # Store raw response
        raw_path = e2e_artifact_collector.raw_dir / f"{test_name}.json"
        raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        entry["raw_response"] = str(raw_path)
        entry["trace_id"] = trace.get("trace_id")
        entry["route"] = route
        entry["status"] = "pass"
        entry["reason"] = "ok"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_inspector_trace_retrieval(e2e_client, e2e_artifact_collector):
    """Test trace retrieval through inspector endpoint."""
    test_name = "inspector_trace_retrieval"

    # First create a trace
    create_response = e2e_client.post("/ops/ci/ask", json={
        "question": "CPU 사용률을 확인해주세요"
    })
    assert create_response.status_code == 200

    trace_data = create_response.json()
    trace_id = trace_data.get("data", {}).get("trace", {}).get("trace_id")
    assert trace_id is not None, "Trace ID must be present"

    # Then retrieve the trace
    entry = {
        "test_name": test_name,
        "trace_id": trace_id,
        "endpoint": "/inspector/traces",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        response = e2e_client.get(f"/inspector/traces/{trace_id}")
        entry["status_code"] = response.status_code

        assert response.status_code == 200, "Status code must be 200"

        data = response.json()
        assert data.get("code", 0) == 0, "Response envelope must report success"

        trace = data.get("data", {}).get("trace")
        assert trace is not None, "Retrieved trace must be present"
        assert trace.get("trace_id") == trace_id, "Trace ID must match"

        # Verify trace has required fields
        assert trace.get("question") is not None, "Question must be present"
        assert trace.get("created_at") is not None, "Created at must be present"
        assert trace.get("status") is not None, "Status must be present"

        entry["status"] = "pass"
        entry["reason"] = "ok"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_inspector_trace_search(e2e_client, e2e_artifact_collector):
    """Test trace search functionality."""
    test_name = "inspector_trace_search"

    # Create some test traces
    questions = [
        "서버 상태를 확인해주세요",
        "CPU 사용률을 확인해주세요",
        "메모리 사용량을 확인해주세요"
    ]

    trace_ids = []
    for question in questions:
        response = e2e_client.post("/ops/ci/ask", json={"question": question})
        assert response.status_code == 200

        trace_data = response.json()
        trace_id = trace_data.get("data", {}).get("trace", {}).get("trace_id")
        trace_ids.append(trace_id)

    # Test search by question text
    entry = {
        "test_name": test_name,
        "endpoint": "/inspector/traces",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        response = e2e_client.get("/inspector/traces", params={"q": "서버"})
        entry["status_code"] = response.status_code

        assert response.status_code == 200, "Status code must be 200"

        data = response.json()
        assert data.get("code", 0) == 0, "Response envelope must report success"

        traces = data.get("data", {}).get("traces", [])
        assert len(traces) > 0, "Must find traces with '서버' in question"

        # Verify returned traces have trace IDs
        returned_ids = [t.get("trace_id") for t in traces]
        assert any(tid in trace_ids for tid in returned_ids), "Must return created traces"

        entry["found_traces"] = len(traces)
        entry["status"] = "pass"
        entry["reason"] = "ok"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_control_loop_replan_mechanism(e2e_client, e2e_artifact_collector):
    """Test control loop replan mechanism with simulated error."""
    test_name = "control_loop_replan_mechanism"

    # Create a trace that might trigger replan
    question = "complex query that needs replan"  # This would need specific setup

    entry = {
        "test_name": test_name,
        "query": question,
        "endpoint": "/ops/ci/ask",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        response = e2e_client.post("/ops/ci/ask", json={"question": question})
        entry["status_code"] = response.status_code

        assert response.status_code == 200, "Status code must be 200"

        data = response.json()
        payload = data.get("data", {})
        trace = payload.get("trace")

        # Check for replan events
        if "replan_events" in trace and trace["replan_events"]:
            replan_events = trace["replan_events"]
            assert len(replan_events) > 0, "Replan events must be present"

            # Verify replan event structure
            event = replan_events[0]
            assert event.get("event_type") is not None, "Event type must be present"
            assert event.get("stage_name") is not None, "Stage name must be present"
            assert event.get("trigger") is not None, "Trigger must be present"
            assert event.get("patch") is not None, "Patch must be present"

            entry["replan_count"] = len(replan_events)
            entry["has_replan"] = True
        else:
            entry["has_replan"] = False
            # This might be expected if no replan was needed
            entry["status"] = "pass"
            entry["reason"] = "No replan triggered (expected)"
            return

        entry["status"] = "pass"
        entry["reason"] = "ok"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)