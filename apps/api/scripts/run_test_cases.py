"""
Run 20 test cases against /ops/ask API and generate detailed results.
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from core.config import get_settings

# Test cases with expected answers
TEST_CASES = [
    {
        "id": 1,
        "query": "What is the current system status? Tell me the total number of CIs.",
        "expected_contains": "280",
    },
    {
        "id": 2,
        "query": "What is the most common CI type in the system?",
        "expected_contains": "SW",
    },
    {
        "id": 3,
        "query": "How many events are recorded in the system?",
        "expected_contains": "31,243",
    },
    {
        "id": 4,
        "query": "What is the most common event type?",
        "expected_contains": "threshold_alarm",
    },
    {
        "id": 5,
        "query": "How many events occurred in the last 24 hours?",
        "expected_contains": "0",
    },
    {
        "id": 6,
        "query": "How many metrics are defined in the system?",
        "expected_contains": "120",
    },
    {
        "id": 7,
        "query": "How many metric data points are recorded?",
        "expected_contains": "10,800,000",
    },
    {
        "id": 8,
        "query": "How many CIs are currently in active status?",
        "expected_contains": "259",
    },
    {
        "id": 9,
        "query": "How many software and hardware CIs do we have?",
        "expected_contains": "272",
    },
    {
        "id": 10,
        "query": "How many audit log entries are there?",
        "expected_contains": "667",
    },
    {
        "id": 11,
        "query": "How many system-type CIs exist?",
        "expected_contains": "8",
    },
    {
        "id": 12,
        "query": "How many events occurred today?",
        "expected_contains": "0",
    },
    {
        "id": 13,
        "query": "How many metric values were recorded today?",
        "expected_contains": "360,000",
    },
    {
        "id": 14,
        "query": "What was the most recent event type?",
        "expected_contains": "threshold_alarm",
    },
    {
        "id": 15,
        "query": "How many threshold alarms have occurred?",
        "expected_contains": "6,291",
    },
    {
        "id": 16,
        "query": "How many security alerts have been raised?",
        "expected_contains": "6,286",
    },
    {
        "id": 17,
        "query": "How many health check events are there?",
        "expected_contains": "6,267",
    },
    {
        "id": 18,
        "query": "How many status change events have occurred?",
        "expected_contains": "6,225",
    },
    {
        "id": 19,
        "query": "How many deployment events have been recorded?",
        "expected_contains": "6,174",
    },
    {
        "id": 20,
        "query": "How many distinct CI names are there in the system?",
        "expected_contains": "280",
    },
]


async def run_single_test(client: httpx.AsyncClient, test_case: dict, api_url: str) -> dict:
    """Run a single test case."""
    test_id = test_case["id"]
    query = test_case["query"]
    expected = test_case["expected_contains"]

    print(f"\n[Test {test_id}] {query}")
    print(f"  Expected to contain: {expected}")

    start_time = time.time()

    try:
        response = await client.post(
            api_url,
            json={"question": query},
            timeout=60.0,
        )
        response.raise_for_status()
        response_data = response.json()

        duration = time.time() - start_time

        # API returns {"data": {"answer": "...", ...}}
        inner_data = response_data.get("data", {})
        answer = inner_data.get("answer", "")
        trace_id = inner_data.get("trace", {}).get("trace_id", "")
        stages = []  # Extract from trace if needed

        # Check if answer contains expected value
        # Remove commas from both for comparison
        answer_normalized = answer.replace(",", "").lower()
        expected_normalized = expected.replace(",", "").lower()

        passed = expected_normalized in answer_normalized

        result = {
            "id": test_id,
            "query": query,
            "expected": expected,
            "answer": answer,
            "trace_id": trace_id,
            "duration": round(duration, 2),
            "passed": passed,
            "stages": stages,
        }

        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {duration:.2f}s")
        if not passed:
            print(f"  Answer: {answer[:200]}...")

        return result

    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ ERROR - {duration:.2f}s: {str(e)}")
        return {
            "id": test_id,
            "query": query,
            "expected": expected,
            "answer": f"ERROR: {str(e)}",
            "trace_id": "",
            "duration": round(duration, 2),
            "passed": False,
            "stages": [],
        }


async def run_all_tests():
    """Run all test cases."""
    get_settings()
    api_url = "http://localhost:8000/ops/ask"

    print("=" * 80)
    print("Running 20 Test Cases for Generic Orchestration")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        results = []
        for test_case in TEST_CASES:
            result = await run_single_test(client, test_case, api_url)
            results.append(result)
            # Small delay between tests
            await asyncio.sleep(0.5)

    # Calculate statistics
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pass_rate = (passed / total) * 100

    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({pass_rate:.1f}%)")
    print(f"Failed: {failed}")
    print()

    if pass_rate >= 90:
        print("✅ SUCCESS: Pass rate >= 90%")
    else:
        print(f"❌ FAILURE: Pass rate {pass_rate:.1f}% < 90%")

    # Generate detailed report
    report_path = Path(__file__).parent.parent.parent.parent / "docs" / "0129A_TEST_CASE_20_RESULT_NEW.md"
    generate_report(results, pass_rate, report_path)
    print(f"\nDetailed report saved to: {report_path}")

    return results, pass_rate


def generate_report(results: list[dict], pass_rate: float, output_path: Path):
    """Generate markdown report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    report = f"""# 📊 20개 테스트 케이스 실행 결과

**실행일시**: {timestamp}
**API**: /ops/ask
**결과**: {'✅' if pass_rate >= 90 else '❌'} {passed_count}/{total_count} (통과율: {pass_rate:.1f}%)

---

"""

    for result in results:
        test_id = result["id"]
        query = result["query"]
        expected = result["expected"]
        answer = result["answer"]
        trace_id = result["trace_id"]
        duration = result["duration"]
        passed = result["passed"]

        status = "PASS" if passed else "FAIL"

        report += f"""## Test {test_id}

**질의**: {query}

**예상 답변에 포함할 단어**: `{expected}`

**Trace ID**: {trace_id}

**응답 시간**: {duration}s

**LLM 답변**:
```
{answer}
```

**결과**: {status}

---

"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)


def main():
    """Main entry point."""
    loop = asyncio.get_event_loop()
    results, pass_rate = loop.run_until_complete(run_all_tests())

    # Exit with error code if tests failed
    if pass_rate < 90:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
