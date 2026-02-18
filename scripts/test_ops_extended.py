#!/usr/bin/env python3
"""
OPS_TEST_CASE_EXTENDED (60개) 전체 모드 테스트 스크립트
"""

import asyncio
import httpx
import json
import re
from datetime import datetime
from typing import Any

# 60개 테스트 케이스
TEST_CASES = [
    # A. 개수 세기 (1-10)
    {"id": 1, "query": "What is the total number of CIs in the system?", "expected": "280", "category": "count"},
    {"id": 2, "query": "How many CIs are currently active?", "expected": "259", "category": "count"},
    {"id": 3, "query": "How many CIs are in monitoring status?", "expected": "21", "category": "count"},
    {"id": 4, "query": "How many software CIs are there?", "expected": "197", "category": "count"},
    {"id": 5, "query": "How many hardware CIs are there?", "expected": "75", "category": "count"},
    {"id": 6, "query": "How many events are recorded in total?", "expected": "31243", "category": "count"},
    {"id": 7, "query": "How many documents are stored in the system?", "expected": "132", "category": "count"},
    {"id": 8, "query": "How many work history entries exist?", "expected": "1731", "category": "count"},
    {"id": 9, "query": "How many maintenance activities have been performed?", "expected": "1478", "category": "count"},
    {"id": 10, "query": "How many audit log entries are there?", "expected": "733", "category": "count"},
    
    # B. 값 확인 (11-20)
    {"id": 11, "query": "What is the size of the largest document?", "expected": "8080776", "category": "value"},
    {"id": 12, "query": "What is the name of the largest document in the system?", "expected": "레드햇리눅스7", "category": "value"},
    {"id": 13, "query": "How many PDF documents are there?", "expected": "78", "category": "count"},
    {"id": 14, "query": "How many plain text documents are there?", "expected": "54", "category": "count"},
    {"id": 15, "query": "What is the most common event type?", "expected": "threshold_alarm", "category": "value"},
    {"id": 16, "query": "What is the most common CI type?", "expected": "SW", "category": "value"},
    {"id": 17, "query": "How many metrics are defined?", "expected": "120", "category": "count"},
    {"id": 18, "query": "How many metric data points are recorded?", "expected": "10800000", "category": "count"},
    {"id": 19, "query": "What document categories exist?", "expected": "manual", "category": "value"},
    {"id": 20, "query": "What is the most common work type?", "expected": "audit", "category": "value"},
    
    # C. 분포/비율 (21-25)
    {"id": 21, "query": "Show me the distribution of CI types.", "expected": "197", "category": "distribution"},
    {"id": 22, "query": "What is the distribution of event types?", "expected": "6291", "category": "distribution"},
    {"id": 23, "query": "Show the distribution of CI statuses.", "expected": "259", "category": "distribution"},
    {"id": 24, "query": "What percentage of work items succeeded?", "expected": "74.9", "category": "percentage"},
    {"id": 25, "query": "What is the success rate of maintenance activities?", "expected": "76.1", "category": "percentage"},
    
    # D. 최근/이전 (26-32)
    {"id": 26, "query": "What was the most recent event?", "expected": "status_change", "category": "recent"},
    {"id": 27, "query": "What type of event occurred most recently?", "expected": "status_change", "category": "recent"},
    {"id": 28, "query": "How many events occurred in the last 24 hours?", "expected": "0", "category": "count"},
    {"id": 29, "query": "How many events occurred today?", "expected": "0", "category": "count"},
    {"id": 30, "query": "How many metric values were recorded today?", "expected": "0", "category": "count"},
    {"id": 31, "query": "What was the second most recent event type?", "expected": "deployment", "category": "recent"},
    {"id": 32, "query": "When did the most recent security alert occur?", "expected": "2026-01-01", "category": "recent"},
    
    # E. 상태 확인 (33-38)
    {"id": 33, "query": "What is the status of ERP System?", "expected": "active", "category": "status"},
    {"id": 34, "query": "What is the current status of ERP Server 01?", "expected": "monitoring", "category": "status"},
    {"id": 35, "query": "Which CIs are in monitoring status?", "expected": "ERP Server", "category": "status"},
    {"id": 36, "query": "Are there any inactive CIs?", "expected": "no", "category": "status"},
    {"id": 37, "query": "How many documents are successfully processed?", "expected": "132", "category": "count"},
    {"id": 38, "query": "Are there any documents that failed to process?", "expected": "no", "category": "status"},
    
    # F. 이력 조회 (39-44)
    {"id": 39, "query": "What types of work have been performed?", "expected": "audit", "category": "history"},
    {"id": 40, "query": "What types of maintenance have been performed?", "expected": "capacity", "category": "history"},
    {"id": 41, "query": "How many deployment work items have been executed?", "expected": "420", "category": "count"},
    {"id": 42, "query": "How many work items completed successfully?", "expected": "1297", "category": "count"},
    {"id": 43, "query": "How many work items resulted in degraded status?", "expected": "434", "category": "count"},
    {"id": 44, "query": "How many reboot maintenance activities have been done?", "expected": "347", "category": "count"},
    
    # G. 특정 대상 (45-50)
    {"id": 45, "query": "Tell me about ERP System.", "expected": "SYSTEM", "category": "specific"},
    {"id": 46, "query": "What can you tell me about ERP Server 01?", "expected": "ERP Server 01", "category": "specific"},
    {"id": 47, "query": "List all CIs related to ERP.", "expected": "ERP", "category": "specific"},
    {"id": 48, "query": "Find documents about Linux.", "expected": "레드햇리눅스", "category": "specific"},
    {"id": 49, "query": "How many events have severity level 5?", "expected": "3134", "category": "count"},
    {"id": 50, "query": "How many events have severity level 1?", "expected": "6310", "category": "count"},
    
    # H. 비교/순위 (51-55)
    {"id": 51, "query": "Which event type occurs most frequently?", "expected": "threshold_alarm", "category": "rank"},
    {"id": 52, "query": "What are the top 3 most common event types?", "expected": "threshold_alarm", "category": "rank"},
    {"id": 53, "query": "Which maintenance type has the highest success rate?", "expected": "success", "category": "rank"},
    {"id": 54, "query": "Which work type is most common?", "expected": "audit", "category": "rank"},
    {"id": 55, "query": "Rank event counts by severity level.", "expected": "12427", "category": "rank"},
    
    # I. 복합 질의 (56-60)
    {"id": 56, "query": "Give me a summary of the overall system status.", "expected": "280", "category": "complex"},
    {"id": 57, "query": "Tell me everything about ERP System including its type and status.", "expected": "ERP System", "category": "complex"},
    {"id": 58, "query": "Summarize the event status by type and severity.", "expected": "31243", "category": "complex"},
    {"id": 59, "query": "Summarize work and maintenance activities.", "expected": "1731", "category": "complex"},
    {"id": 60, "query": "Give me a summary of the document management status.", "expected": "132", "category": "complex"},
]

API_BASE_URL = "http://localhost:8000"
RESULTS_FILE = "artifacts/ops_test_extended_results.json"


def check_answer(response_text: str, expected: str) -> tuple[bool, str]:
    """응답 텍스트에서 예상 답변이 포함되어 있는지 확인"""
    response_lower = response_text.lower()
    expected_lower = expected.lower()
    
    # 직접 포함 확인
    if expected_lower in response_lower:
        return True, f"Found: {expected}"
    
    # 쉼표 포함 형태
    formatted = f"{int(expected):,}" if expected.isdigit() else None
    if formatted and formatted in response_text:
        return True, f"Found formatted: {formatted}"
    
    # 숫자 추출 시도
    numbers = re.findall(r'[\d,]+', response_text)
    for num in numbers:
        if num.replace(',', '') == expected:
            return True, f"Found number: {num}"
    
    return False, f"Expected '{expected}' not found"


async def run_test(client: httpx.AsyncClient, test_case: dict, headers: dict) -> dict:
    """단일 테스트 실행"""
    result = {
        "id": test_case["id"],
        "query": test_case["query"],
        "category": test_case["category"],
        "expected": test_case["expected"],
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "response_text": "",
        "reason": "",
        "response_time_ms": 0,
    }
    
    try:
        payload = {"question": test_case["query"], "mode": "all"}
        
        start_time = datetime.now()
        response = await client.post(
            f"{API_BASE_URL}/ops/ask",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        end_time = datetime.now()
        
        result["response_time_ms"] = int((end_time - start_time).total_seconds() * 1000)
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            data = response.json()
            
            # 응답에서 텍스트 추출
            if "data" in data:
                inner_data = data["data"]
                if "blocks" in inner_data:
                    blocks = inner_data["blocks"]
                    text_parts = []
                    for block in blocks:
                        if block.get("type") == "markdown":
                            text_parts.append(block.get("content", ""))
                        elif block.get("type") == "text":
                            text_parts.append(block.get("content", ""))
                    response_text = " ".join(text_parts)
                elif "answer" in inner_data:
                    response_text = inner_data["answer"]
                else:
                    response_text = json.dumps(inner_data)
            else:
                response_text = json.dumps(data)
            
            result["response_text"] = response_text[:500]
            
            is_correct, reason = check_answer(response_text, test_case["expected"])
            result["success"] = is_correct
            result["reason"] = reason
        else:
            result["reason"] = f"HTTP {response.status_code}"
    
    except httpx.TimeoutException:
        result["reason"] = "Timeout (120s)"
    except Exception as e:
        result["reason"] = f"Error: {str(e)}"
    
    return result


async def main():
    """메인 테스트 실행"""
    print("=" * 80)
    print("OPS_TEST_CASE_EXTENDED (60개) - 전체 모드 테스트")
    print("=" * 80)
    print(f"시작: {datetime.now().isoformat()}")
    print(f"API: {API_BASE_URL}")
    print(f"테스트: {len(TEST_CASES)}개\n")
    
    results = []
    passed = 0
    failed = 0
    
    async with httpx.AsyncClient() as client:
        headers = {"Content-Type": "application/json", "X-Tenant-Id": "default"}
        
        for test_case in TEST_CASES:
            print(f"[{test_case['id']}/{len(TEST_CASES)}] {test_case['query'][:50]}...")
            
            result = await run_test(client, test_case, headers)
            results.append(result)
            
            if result["success"]:
                passed += 1
                print(f"  ✅ {result['reason']} ({result['response_time_ms']}ms)")
            else:
                failed += 1
                print(f"  ❌ {result['reason']} ({result['response_time_ms']}ms)")
            
            # 카테고리별 통계
            if result["success"]:
                print(f"  응답: {result['response_text'][:100]}...")
            print()
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"총: {len(TEST_CASES)}, 성공: {passed}, 실패: {failed}")
    print(f"성공률: {passed / len(TEST_CASES) * 100:.1f}%")
    
    # 카테고리별 결과
    print("\n카테고리별 결과:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0}
        if r["success"]:
            categories[cat]["passed"] += 1
        else:
            categories[cat]["failed"] += 1
    
    for cat, stats in categories.items():
        total = stats["passed"] + stats["failed"]
        rate = stats["passed"] / total * 100 if total > 0 else 0
        print(f"  {cat}: {stats['passed']}/{total} ({rate:.0f}%)")
    
    # 저장
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "success_rate": round(passed / len(TEST_CASES) * 100, 1),
        "categories": categories,
        "results": results,
    }
    
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 저장: {RESULTS_FILE}")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(main())