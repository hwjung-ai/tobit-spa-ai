#!/usr/bin/env python3
"""
Test script for orchestration queries.
Creates 5 complex queries designed to exercise different orchestration execution paths.
"""

import json
import requests
import time
from typing import Dict, Any, List

# API endpoint
BASE_URL = "http://localhost:8000"
CI_ASK_ENDPOINT = f"{BASE_URL}/ops/ci/ask"

# Test queries designed for orchestration
TEST_QUERIES = [
    {
        "id": "query_1_parallel",
        "description": "Parallel Execution - Query multiple independent data sources",
        "question": "location=zone-a AND location=zone-b AND location=zone-c 에서 active 상태의 서버 목록을 각각 조회해줄래. 그리고 전체 서버의 총 개수도 알려줘.",
        "notes": "This query should trigger parallel execution as it queries independent zones"
    },
    {
        "id": "query_2_sequential",
        "description": "Sequential Execution - Query with data dependencies",
        "question": "전체 active 서버 목록을 먼저 조회하고, 그 결과에서 CPU 사용률이 80% 이상인 서버들을 필터링해서 보여줘.",
        "notes": "This query requires sequential execution due to data dependencies between steps"
    },
    {
        "id": "query_3_dag_complex",
        "description": "DAG Execution - Complex dependency graph",
        "question": "database 타입의 서버들을 조회하고, 각 서버의 상세 정보를 가져온 후, 관련된 애플리케이션 목록도 함께 조회해줄래. 그리고 마지막으로 전체 시스템 상태 리포트를 작성해주세요.",
        "notes": "This query creates a complex DAG with multiple dependencies and aggregation points"
    },
    {
        "id": "query_4_mixed_execution",
        "description": "Mixed Execution - Combination of parallel and sequential steps",
        "question": "먼저 prod 환경의 모든 서버를 조회하고, 동시에 staging 환경의 서버도 조회해줘. 그 다음에 두 환경의 서버 구성을 비교해서 차이점을 분석해주세요.",
        "notes": "This query uses parallel steps (two independent queries) followed by sequential aggregation"
    },
    {
        "id": "query_5_complex_aggregation",
        "description": "Complex Aggregation - Multi-level data aggregation with transformations",
        "question": "각 지역(zone)별로 서버 상태를 조회하고, 각 지역별 평균 CPU/메모리 사용률을 계산한 후, 최종적으로 전체 인프라 health check 결과를 종합한 대시보드 정보를 만들어줄래.",
        "notes": "This query demonstrates multi-level aggregation requiring multiple tool executions with data transformations"
    }
]


def send_query(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send a single query to the ops/ci/ask endpoint."""
    request_payload = {
        "question": query_data["question"]
    }

    try:
        print(f"\n{'='*80}")
        print(f"Query: {query_data['id']} - {query_data['description']}")
        print(f"Question: {query_data['question']}")
        print(f"Notes: {query_data['notes']}")
        print(f"{'='*80}")
        print(f"Sending request to {CI_ASK_ENDPOINT}...")

        start_time = time.time()
        response = requests.post(
            CI_ASK_ENDPOINT,
            json=request_payload,
            headers={"X-User-Id": "test-user", "X-Tenant-Id": "default"},
            timeout=60
        )
        elapsed_time = time.time() - start_time

        print(f"Response status: {response.status_code}")
        print(f"Response time: {elapsed_time:.2f}s")

        if response.status_code == 200:
            result = response.json()

            # Extract trace_id
            trace_id = None
            if "data" in result:
                trace_id = result["data"].get("trace_id")
            if not trace_id and "meta" in result:
                trace_id = result["meta"].get("trace_id")

            # Check for orchestration trace
            orchestration_trace = None
            if "data" in result:
                orchestration_trace = result["data"].get("orchestration_trace")
            if not orchestration_trace and "trace" in result:
                # Look for orchestration info in trace
                trace_data = result.get("trace", {})
                if isinstance(trace_data, dict):
                    orchestration_trace = trace_data.get("orchestration_trace")

            result_summary = {
                "query_id": query_data["id"],
                "status": "success",
                "trace_id": trace_id,
                "elapsed_time": elapsed_time,
                "has_orchestration_trace": orchestration_trace is not None,
                "orchestration_strategy": None,
                "execution_groups": 0,
                "total_tools": 0
            }

            if orchestration_trace:
                result_summary["orchestration_strategy"] = orchestration_trace.get("strategy")
                result_summary["execution_groups"] = orchestration_trace.get("total_groups", 0)
                result_summary["total_tools"] = orchestration_trace.get("total_tools", 0)

                print(f"\n✓ Orchestration Trace Found!")
                print(f"  Strategy: {orchestration_trace.get('strategy', 'N/A')}")
                print(f"  Execution Groups: {orchestration_trace.get('total_groups', 0)}")
                print(f"  Total Tools: {orchestration_trace.get('total_tools', 0)}")

            print(f"Trace ID: {trace_id}")

            return result_summary
        else:
            print(f"Error: {response.text}")
            return {
                "query_id": query_data["id"],
                "status": "error",
                "error": response.text,
                "elapsed_time": elapsed_time
            }

    except Exception as e:
        print(f"Exception: {str(e)}")
        return {
            "query_id": query_data["id"],
            "status": "error",
            "error": str(e)
        }


def main():
    """Run all test queries."""
    print("\n" + "="*80)
    print("ORCHESTRATION TEST QUERIES")
    print("="*80)
    print(f"Total queries to run: {len(TEST_QUERIES)}")
    print("="*80)

    results: List[Dict[str, Any]] = []

    for query_data in TEST_QUERIES:
        result = send_query(query_data)
        results.append(result)

        # Wait between queries
        time.sleep(2)

    # Summary report
    print(f"\n\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}\n")

    successful_queries = [r for r in results if r.get("status") == "success"]
    orchestration_queries = [r for r in results if r.get("has_orchestration_trace")]

    print(f"Total queries executed: {len(results)}")
    print(f"Successful: {len(successful_queries)}")
    print(f"With orchestration traces: {len(orchestration_queries)}")

    print(f"\n{'Query ID':<20} {'Status':<10} {'Trace ID':<40} {'Strategy':<15} {'Groups':<8} {'Tools':<8}")
    print("-" * 101)

    for result in results:
        query_id = result.get("query_id", "N/A")
        status = result.get("status", "N/A")
        trace_id = result.get("trace_id", "N/A")[:36] if result.get("trace_id") else "N/A"
        strategy = result.get("orchestration_strategy", "N/A")
        groups = result.get("execution_groups", "N/A")
        tools = result.get("total_tools", "N/A")

        print(f"{query_id:<20} {status:<10} {trace_id:<40} {strategy:<15} {groups:<8} {tools:<8}")

    # Save results to file
    output_file = "/tmp/orchestration_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {output_file}")

    # Print next steps
    print(f"\n{'='*80}")
    print("NEXT STEPS:")
    print("="*80)
    print("1. Open Inspector UI at: http://localhost:3000/admin/inspector")
    print("2. Use the trace_ids above to view orchestration traces")
    print("3. Check OPS menu > Query History to verify trace_ids are now being logged")
    print("4. Verify orchestration visualization displays correctly for each trace")
    print("="*80)


if __name__ == "__main__":
    main()
