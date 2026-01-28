#!/usr/bin/env python3
"""
Real API test execution script.
Executes 20 test queries against the actual /ops/ci/ask API endpoint
and collects detailed trace information from /inspector/traces/{trace_id}
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional
from statistics import mean, median, stdev

# Test query definitions
TEST_QUERIES = [
    # Category 1: Basic System Status (1-3)
    {
        "id": 1,
        "category": "System Status",
        "question": "What is the current system status?",
        "description": "Basic system health check",
    },
    {
        "id": 2,
        "category": "System Status",
        "question": "Show me the system information",
        "description": "System information overview",
    },
    {
        "id": 3,
        "category": "System Status",
        "question": "What services are currently running?",
        "description": "Service status check",
    },
    # Category 2: Metrics Queries (4-8)
    {
        "id": 4,
        "category": "Metrics",
        "question": "What are the key performance metrics?",
        "description": "KPI metrics retrieval",
    },
    {
        "id": 5,
        "category": "Metrics",
        "question": "Show me the last 24 hours of system metrics",
        "description": "Time-series metrics",
    },
    {
        "id": 6,
        "category": "Metrics",
        "question": "What is the current resource usage?",
        "description": "Resource utilization metrics",
    },
    {
        "id": 7,
        "category": "Metrics",
        "question": "How many records were processed today?",
        "description": "Daily processing metrics",
    },
    {
        "id": 8,
        "category": "Metrics",
        "question": "What is the average response time?",
        "description": "Response time metrics",
    },
    # Category 3: Relationship/Graph Queries (9-12)
    {
        "id": 9,
        "category": "Relationships",
        "question": "Show me the data dependencies",
        "description": "Dependency graph visualization",
    },
    {
        "id": 10,
        "category": "Relationships",
        "question": "What entities are related to users?",
        "description": "Entity relationships",
    },
    {
        "id": 11,
        "category": "Relationships",
        "question": "Display the system architecture diagram",
        "description": "System architecture visualization",
    },
    {
        "id": 12,
        "category": "Relationships",
        "question": "What are the data flow relationships?",
        "description": "Data flow mapping",
    },
    # Category 4: History Queries (13-16)
    {
        "id": 13,
        "category": "History",
        "question": "Show me the recent changes",
        "description": "Recent modification history",
    },
    {
        "id": 14,
        "category": "History",
        "question": "What happened yesterday?",
        "description": "Historical event log",
    },
    {
        "id": 15,
        "category": "History",
        "question": "Show me the audit trail for last week",
        "description": "Weekly audit trail",
    },
    {
        "id": 16,
        "category": "History",
        "question": "What was the system state 7 days ago?",
        "description": "Historical system state",
    },
    # Category 5: Advanced Queries (17-20)
    {
        "id": 17,
        "category": "Advanced",
        "question": "Compare the performance metrics across different time periods",
        "description": "Performance comparison analysis",
    },
    {
        "id": 18,
        "category": "Advanced",
        "question": "Generate a comprehensive system report",
        "description": "Comprehensive system report generation",
    },
    {
        "id": 19,
        "category": "Advanced",
        "question": "Analyze trends and provide insights",
        "description": "Trend analysis and insights",
    },
    {
        "id": 20,
        "category": "Advanced",
        "question": "What are the recommendations for system optimization?",
        "description": "System optimization recommendations",
    },
]

API_BASE_URL = "http://localhost:8000"
ASK_ENDPOINT = f"{API_BASE_URL}/ops/ci/ask"
TRACE_ENDPOINT = f"{API_BASE_URL}/inspector/traces"


def call_ask_api(question: str) -> Dict[str, Any]:
    """Call the /ops/ci/ask API endpoint."""
    payload = {
        "question": question,
        "mode": "real"
    }

    start_time = time.time()
    try:
        response = requests.post(ASK_ENDPOINT, json=payload, timeout=30)
        response_time_ms = int((time.time() - start_time) * 1000)

        if response.status_code == 200:
            envelope = response.json()
            data = envelope.get("data", {})
            trace = data.get("trace", {})
            return {
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "trace_id": trace.get("trace_id") or data.get("trace_id"),
                "answer": data.get("answer", ""),
                "blocks": data.get("blocks", []),
                "success": True,
            }
        else:
            return {
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "success": False,
                "error": f"API returned {response.status_code}",
            }
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        return {
            "status_code": 0,
            "response_time_ms": response_time_ms,
            "success": False,
            "error": str(e),
        }


def get_trace_details(trace_id: str) -> Dict[str, Any]:
    """Get detailed trace information from /inspector/traces/{trace_id}."""
    try:
        response = requests.get(f"{TRACE_ENDPOINT}/{trace_id}", timeout=10)

        if response.status_code == 200:
            envelope = response.json()
            trace = envelope.get("data", {}).get("trace", {})

            # Extract stage breakdown and timing
            stage_breakdown = {}
            total_duration = trace.get("duration_ms", 0)

            # Extract stage inputs and applied assets
            stage_inputs_count = len(trace.get("stage_inputs", []))
            applied_assets = trace.get("applied_assets", {})

            # Try to extract stage durations from stages if available
            stages = trace.get("stages", [])
            if stages:
                for stage in stages:
                    if isinstance(stage, dict):
                        stage_name = stage.get("name", "unknown")
                        duration = stage.get("duration_ms", stage.get("elapsed_ms", 0))
                        stage_breakdown[stage_name] = {
                            "duration_ms": duration,
                        }

            return {
                "success": True,
                "trace_id": trace_id,
                "total_duration_ms": total_duration,
                "stage_breakdown": stage_breakdown,
                "stage_inputs_count": stage_inputs_count,
                "applied_assets": applied_assets,
            }
        else:
            return {
                "success": False,
                "trace_id": trace_id,
                "error": f"Trace API returned {response.status_code}",
            }
    except Exception as e:
        return {
            "success": False,
            "trace_id": trace_id,
            "error": str(e),
        }


def run_test_suite() -> None:
    """Run all 20 test queries and collect detailed information."""
    print("=" * 120)
    print("REAL API TEST EXECUTION - 20 TEST QUERIES")
    print("=" * 120)
    print(f"\nExecution Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Total Tests: {len(TEST_QUERIES)}\n")

    results = []
    results_by_category = {}
    all_response_times = []
    stage_timing_stats = {}

    execution_start = time.time()

    for test_case in TEST_QUERIES:
        test_id = test_case["id"]
        question = test_case["question"]
        category = test_case["category"]

        print(f"[{test_id:2d}/20] Testing: {category} - {question}")

        # Initialize category tracking
        if category not in results_by_category:
            results_by_category[category] = {"pass": 0, "fail": 0, "total": 0, "tests": []}

        # Call the ask API
        api_response = call_ask_api(question)

        test_result = {
            "test_id": test_id,
            "question": question,
            "category": category,
            "api_response": {
                "status_code": api_response.get("status_code"),
                "response_time_ms": api_response.get("response_time_ms"),
                "trace_id": api_response.get("trace_id"),
                "answer": api_response.get("answer", ""),
                "blocks": api_response.get("blocks", []),
            },
            "trace_analysis": {},
            "validation": {
                "answer_generated": False,
                "trace_complete": False,
                "all_stages_executed": False,
                "assets_populated": False,
            },
            "result": "UNKNOWN"
        }

        # Track response time
        if api_response.get("success"):
            all_response_times.append(api_response.get("response_time_ms", 0))

            # Get trace details if we have a trace_id
            trace_id = api_response.get("trace_id")
            if trace_id:
                print(f"        Trace ID: {trace_id}")
                trace_details = get_trace_details(trace_id)

                if trace_details.get("success"):
                    test_result["trace_analysis"] = {
                        "total_duration_ms": trace_details.get("total_duration_ms"),
                        "stage_breakdown": trace_details.get("stage_breakdown", {}),
                        "stage_inputs_count": trace_details.get("stage_inputs_count"),
                        "applied_assets": trace_details.get("applied_assets", {}),
                    }

                    # Update validation checks
                    answer = api_response.get("answer", "").strip()
                    test_result["validation"]["answer_generated"] = len(answer) > 0
                    test_result["validation"]["trace_complete"] = len(trace_details.get("stage_breakdown", {})) > 0
                    test_result["validation"]["all_stages_executed"] = len(trace_details.get("stage_breakdown", {})) >= 3
                    test_result["validation"]["assets_populated"] = len(trace_details.get("applied_assets", {})) > 0

                    # Determine overall result
                    if all([
                        test_result["validation"]["answer_generated"],
                        test_result["validation"]["trace_complete"],
                    ]):
                        test_result["result"] = "PASS"
                        results_by_category[category]["pass"] += 1
                        print(f"        Result: PASS")
                    else:
                        test_result["result"] = "FAIL"
                        results_by_category[category]["fail"] += 1
                        print(f"        Result: FAIL")
                else:
                    test_result["result"] = "ERROR"
                    test_result["trace_analysis"]["error"] = trace_details.get("error")
                    results_by_category[category]["fail"] += 1
                    print(f"        Result: ERROR - {trace_details.get('error')}")
            else:
                test_result["result"] = "FAIL"
                results_by_category[category]["fail"] += 1
                print(f"        Result: FAIL - No trace_id")
        else:
            test_result["result"] = "ERROR"
            test_result["api_response"]["error"] = api_response.get("error")
            results_by_category[category]["fail"] += 1
            print(f"        Result: ERROR - {api_response.get('error')}")

        results_by_category[category]["total"] += 1
        results_by_category[category]["tests"].append(test_id)
        results.append(test_result)

        # Small delay between tests
        time.sleep(0.1)

    execution_end = time.time()
    total_execution_time = int((execution_end - execution_start) * 1000)

    # Print summary
    print("\n" + "=" * 120)
    print("EXECUTION SUMMARY")
    print("=" * 120)

    total_pass = sum(1 for r in results if r["result"] == "PASS")
    total_fail = sum(1 for r in results if r["result"] == "FAIL")
    total_error = sum(1 for r in results if r["result"] == "ERROR")

    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {total_pass} ({total_pass*100//len(results) if results else 0}%)")
    print(f"Failed: {total_fail}")
    print(f"Errors: {total_error}")
    print(f"Total Execution Time: {total_execution_time}ms")

    print("\nResults by Category:")
    for category in sorted(results_by_category.keys()):
        stats = results_by_category[category]
        pass_rate = (stats["pass"] * 100) // stats["total"] if stats["total"] > 0 else 0
        print(f"  {category:20s}: {stats['pass']:2d}/{stats['total']:2d} PASS ({pass_rate:3d}%)")

    # Calculate response time statistics
    if all_response_times:
        print(f"\nAPI Response Time Statistics:")
        print(f"  Average: {mean(all_response_times):.1f}ms")
        print(f"  Median:  {median(all_response_times):.1f}ms")
        print(f"  Min:     {min(all_response_times)}ms")
        print(f"  Max:     {max(all_response_times)}ms")
        if len(all_response_times) > 1:
            print(f"  StdDev:  {stdev(all_response_times):.1f}ms")

    # Save JSON results
    output_file = "/home/spa/tobit-spa-ai/test_execution_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "execution": {
                    "timestamp": datetime.now().isoformat(),
                    "total_duration_ms": total_execution_time,
                    "total_tests": len(results),
                    "passed": total_pass,
                    "failed": total_fail,
                    "errors": total_error,
                    "api_base_url": API_BASE_URL,
                },
                "tests": results,
                "by_category": {k: {**v, "tests": v["tests"]} for k, v in results_by_category.items()},
                "statistics": {
                    "response_times": {
                        "average_ms": mean(all_response_times) if all_response_times else 0,
                        "median_ms": median(all_response_times) if all_response_times else 0,
                        "min_ms": min(all_response_times) if all_response_times else 0,
                        "max_ms": max(all_response_times) if all_response_times else 0,
                        "stdev_ms": stdev(all_response_times) if len(all_response_times) > 1 else 0,
                    }
                }
            },
            f,
            indent=2,
        )

    print(f"\nJSON results saved to: {output_file}")
    print("=" * 120)


if __name__ == "__main__":
    run_test_suite()
