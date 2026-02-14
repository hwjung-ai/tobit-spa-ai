"""Performance profiling tests for OPS orchestration system."""

from __future__ import annotations

import statistics
import time
from typing import List

import pytest

from tests.ops_e2e.conftest import E2EArtifactCollector


class PerformanceProfiler:
    """Utility class for performance profiling."""

    def __init__(self, e2e_artifact_collector: E2EArtifactCollector):
        self.collector = e2e_artifact_collector
        self.measurements: List[float] = []

    def measure_endpoint(self, client, endpoint: str, payload: dict, iterations: int = 5) -> dict:
        """Measure endpoint performance over multiple iterations."""
        durations = []

        for i in range(iterations):
            start_time = time.time()
            response = client.post(endpoint, json=payload)
            end_time = time.time()

            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            durations.append(duration)

            # Verify response
            assert response.status_code == 200, f"Status code must be 200, got {response.status_code}"
            data = response.json()
            assert data.get("code", 0) == 0, "Response envelope must report success"

        # Calculate statistics
        stats = {
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "min": min(durations),
            "max": max(durations),
            "stddev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "p95": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            "measurements": durations
        }

        return stats


@pytest.fixture
def profiler(e2e_artifact_collector) -> PerformanceProfiler:
    """Performance profiler fixture."""
    return PerformanceProfiler(e2e_artifact_collector)


def test_ci_ask_endpoint_performance(e2e_client, profiler, e2e_artifact_collector):
    """Test CI ask endpoint performance."""
    test_name = "ci_ask_endpoint_performance"
    question = "서버 상태를 확인해주세요"

    entry = {
        "test_name": test_name,
        "endpoint": "/ops/ask",
        "iterations": 5,
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Measure performance
        stats = profiler.measure_endpoint(
            e2e_client,
            "/ops/ask",
            {"question": question},
            iterations=5
        )

        # Performance criteria
        mean_duration = stats["mean"]
        p95_duration = stats["p95"]
        max_duration = stats["max"]

        # Assert performance requirements (adjust thresholds as needed)
        assert mean_duration < 5000, f"Mean duration {mean_duration}ms exceeds 5000ms limit"
        assert p95_duration < 10000, f"P95 duration {p95_duration}ms exceeds 10000ms limit"
        assert max_duration < 15000, f"Max duration {max_duration}ms exceeds 15000ms limit"

        # Record performance metrics
        entry.update(stats)
        entry["mean_duration_ms"] = round(mean_duration, 2)
        entry["p95_duration_ms"] = round(p95_duration, 2)
        entry["max_duration_ms"] = round(max_duration, 2)
        entry["performance_profile"] = "acceptable"
        entry["status"] = "pass"
        entry["reason"] = "Performance requirements met"

        # Check if performance needs optimization
        if mean_duration > 3000:
            entry["performance_profile"] = "warning"
            entry["reason"] = "Performance could be improved"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_inspector_traces_performance(e2e_client, profiler, e2e_artifact_collector):
    """Test inspector traces endpoint performance."""
    test_name = "inspector_traces_performance"

    # First create some traces
    for i in range(3):
        response = e2e_client.post("/ops/ask", json={
            "question": f"Test query {i} for performance testing"
        })
        assert response.status_code == 200

    entry = {
        "test_name": test_name,
        "endpoint": "/inspector/traces",
        "iterations": 3,
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Measure list traces performance
        stats = profiler.measure_endpoint(
            e2e_client,
            "/inspector/traces",
            {},
            iterations=3
        )

        # Performance criteria for listing traces
        mean_duration = stats["mean"]
        p95_duration = stats["p95"]

        # Assert performance requirements
        assert mean_duration < 2000, f"Mean duration {mean_duration}ms exceeds 2000ms limit"
        assert p95_duration < 3000, f"P95 duration {p95_duration}ms exceeds 3000ms limit"

        # Record metrics
        entry.update(stats)
        entry["mean_duration_ms"] = round(mean_duration, 2)
        entry["p95_duration_ms"] = round(p95_duration, 2)
        entry["performance_profile"] = "acceptable"
        entry["status"] = "pass"
        entry["reason"] = "Performance requirements met"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_memory_usage_profiling(e2e_client, e2e_artifact_collector):
    """Test memory usage during orchestration."""
    test_name = "memory_usage_profiling"

    # Note: This is a basic test that checks response size as a proxy for memory usage
    entry = {
        "test_name": test_name,
        "endpoint": "/ops/ask",
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Test with simple question
        response = e2e_client.post("/ops/ask", json={"question": "Simple query"})
        data = response.json()

        # Calculate response size
        response_size = len(str(data).encode('utf-8'))  # Size in bytes

        # Check response size (less than 1MB)
        assert response_size < 1024 * 1024, f"Response size {response_size} bytes exceeds 1MB limit"

        # Test with complex question that might generate larger responses
        response = e2e_client.post("/ops/ask", json={
            "question": "複雑なクエリで詳細なレポートを生成してください"
        })
        data = response.json()
        complex_response_size = len(str(data).encode('utf-8'))

        # Check complex response size (less than 5MB)
        assert complex_response_size < 5 * 1024 * 1024, f"Complex response size {complex_response_size} bytes exceeds 5MB limit"

        entry["simple_response_size_bytes"] = response_size
        entry["complex_response_size_bytes"] = complex_response_size
        entry["status"] = "pass"
        entry["reason"] = "Memory usage within limits"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)


def test_concurrent_requests_performance(e2e_client, e2e_artifact_collector):
    """Test system performance under concurrent requests."""
    test_name = "concurrent_requests_performance"

    import asyncio
    import concurrent.futures

    async def make_request(client, question: str):
        """Make a single request."""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.post("/ops/ask", json={"question": question})
        )
        return response

    entry = {
        "test_name": test_name,
        "concurrent_count": 5,
        "pass": False,
        "reason": "",
        "status": "pending"
    }

    try:
        # Test concurrent requests
        questions = [f"Concurrent query {i}" for i in range(5)]

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    lambda q: e2e_client.post("/ops/ask", json={"question": q}),
                    question
                )
                for question in questions
            ]

            responses = [future.result() for future in futures]

        end_time = time.time()
        total_duration = (end_time - start_time) * 1000

        # Verify all requests succeeded
        for i, response in enumerate(responses):
            assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"

        # Calculate average duration per request
        avg_duration = total_duration / len(questions)

        # Performance criteria for concurrent requests
        assert total_duration < 10000, f"Total duration {total_duration}ms exceeds 10000ms limit"
        assert avg_duration < 3000, f"Average duration {avg_duration}ms exceeds 3000ms limit"

        entry["total_duration_ms"] = round(total_duration, 2)
        entry["average_duration_ms"] = round(avg_duration, 2)
        entry["concurrent_count"] = len(questions)
        entry["status"] = "pass"
        entry["reason"] = "Concurrent performance requirements met"

    except Exception as e:
        entry["reason"] = str(e)
        entry["status"] = "fail"
        raise

    finally:
        e2e_artifact_collector.add_entry(entry)