#!/usr/bin/env python3
"""
OPS_TEST_CASE_20 전체 모드 테스트 스크립트

이 스크립트는 docs/OPS_TEST_CASE_20.md에 정의된 20개의 테스트 케이스를
OPS 전체(all) 모드 POST /ops/ask 엔드포인트를 통해 실행하고 결과를 검증합니다.

Usage:
    python scripts/test_ops_20_cases.py
"""

import asyncio
import httpx
import json
import re
from datetime import datetime
from typing import Any

# 테스트 케이스 정의
TEST_CASES = [
    {
        "id": 1,
        "query": "What is the current system status? Tell me the total number of CIs.",
        "expected_answer": "280",
        "description": "Total CI count",
    },
    {
        "id": 2,
        "query": "What is the most common CI type in the system?",
        "expected_answer": "SW",
        "description": "Most common CI type",
    },
    {
        "id": 3,
        "query": "How many events are recorded in the system?",
        "expected_answer": "31243",
        "description": "Total event count",
    },
    {
        "id": 4,
        "query": "What is the most common event type?",
        "expected_answer": "threshold_alarm",
        "description": "Most common event type",
    },
    {
        "id": 5,
        "query": "How many events occurred in the last 24 hours?",
        "expected_answer": "0",
        "description": "Events in last 24 hours",
    },
    {
        "id": 6,
        "query": "How many metrics are defined in the system?",
        "expected_answer": "120",
        "description": "Total metrics count",
    },
    {
        "id": 7,
        "query": "How many metric data points are recorded?",
        "expected_answer": "10800000",
        "description": "Total metric data points",
    },
    {
        "id": 8,
        "query": "How many CIs are currently in active status?",
        "expected_answer": "259",
        "description": "Active CI count",
    },
    {
        "id": 9,
        "query": "How many software and hardware CIs do we have?",
        "expected_answer": "197",
        "alt_expected": "75",
        "description": "SW and HW CI counts",
    },
    {
        "id": 10,
        "query": "How many audit log entries are there?",
        "expected_answer": "733",
        "description": "Audit log count",
    },
    {
        "id": 11,
        "query": "How many system-type CIs exist?",
        "expected_answer": "8",
        "description": "System-type CI count",
    },
    {
        "id": 12,
        "query": "How many events occurred today?",
        "expected_answer": "0",
        "description": "Events today",
    },
    {
        "id": 13,
        "query": "How many metric values were recorded today?",
        "expected_answer": "0",
        "description": "Metric values today",
    },
    {
        "id": 14,
        "query": "What was the most recent event type?",
        "expected_answer": "status_change",
        "description": "Most recent event type",
    },
    {
        "id": 15,
        "query": "How many threshold alarms have occurred?",
        "expected_answer": "6291",
        "description": "Threshold alarm count",
    },
    {
        "id": 16,
        "query": "How many security alerts have been raised?",
        "expected_answer": "6286",
        "description": "Security alert count",
    },
    {
        "id": 17,
        "query": "How many health check events are there?",
        "expected_answer": "6267",
        "description": "Health check count",
    },
    {
        "id": 18,
        "query": "How many status change events have occurred?",
        "expected_answer": "6225",
        "description": "Status change count",
    },
    {
        "id": 19,
        "query": "How many deployment events have been recorded?",
        "expected_answer": "6174",
        "description": "Deployment count",
    },
    {
        "id": 20,
        "query": "How many distinct CI names are there in the system?",
        "expected_answer": "280",
        "description": "Distinct CI names",
    },
]

API_BASE_URL = "http://localhost:8000"
RESULTS_FILE = "artifacts/ops_test_20_results.json"


def extract_number_from_text(text: str) -> str | None:
    """텍스트에서 숫자를 추출합니다."""
    # 쉼표가 포함된 숫자도 처리
    matches = re.findall(r"[\d,]+", text)
    if matches:
        # 가장 큰 숫자를 반환 (일반적으로 답변의 핵심 숫자)
        numbers = [int(m.replace(",", "")) for m in matches if m.replace(",", "").isdigit()]
        if numbers:
            return str(max(numbers))
    return None


def check_answer(response_text: str, expected: str, alt_expected: str | None = None) -> tuple[bool, str]:
    """
    응답 텍스트에서 예상 답변이 포함되어 있는지 확인합니다.
    
    Returns:
        (is_correct, reason)
    """
    response_lower = response_text.lower()
    expected_lower = expected.lower()
    
    # 직접 포함 확인
    if expected_lower in response_lower:
        return True, f"Found expected value: {expected}"
    
    # 대체 예상값 확인
    if alt_expected and alt_expected.lower() in response_lower:
        return True, f"Found alt expected value: {alt_expected}"
    
    # 숫자의 경우 더 유연한 매칭
    if expected.isdigit():
        # 쉼표가 포함된 형태도 확인
        formatted_expected = f"{int(expected):,}"
        if formatted_expected in response_text:
            return True, f"Found formatted value: {formatted_expected}"
        
        # 영문 표기 (10,800,000 -> 10.8 million 등)
        if int(expected) >= 1000000:
            millions = int(expected) / 1000000
            if f"{millions}" in response_text or f"{millions:.1f}" in response_text:
                return True, f"Found value in millions: {millions}"
    
    # 추출된 숫자로 확인
    extracted = extract_number_from_text(response_text)
    if extracted and extracted == expected:
        return True, f"Found extracted value: {extracted}"
    
    return False, f"Expected '{expected}' not found in response"


async def run_test(
    client: httpx.AsyncClient, test_case: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    """단일 테스트 케이스를 실행합니다."""
    test_id = test_case["id"]
    query = test_case["query"]
    expected = test_case["expected_answer"]
    alt_expected = test_case.get("alt_expected")
    
    result = {
        "id": test_id,
        "query": query,
        "description": test_case["description"],
        "expected": expected,
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "response_text": "",
        "reason": "",
        "response_time_ms": 0,
    }
    
    try:
        # OPS 전체(all) 모드 호출 - POST /ops/ask
        payload = {
            "question": query,
            "mode": "all",
        }
        
        start_time = datetime.now()
        response = await client.post(
            f"{API_BASE_URL}/ops/ask",
            json=payload,
            headers=headers,
            timeout=60.0,  # LLM 호출 시 시간이 걸릴 수 있음
        )
        end_time = datetime.now()
        
        result["response_time_ms"] = int((end_time - start_time).total_seconds() * 1000)
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            data = response.json()
            
            # 응답 구조에서 텍스트 추출
            # ResponseEnvelope: { time, code, message, data: {...} }
            if "data" in data:
                inner_data = data["data"]
                
                # Answer blocks에서 텍스트 추출
                if "blocks" in inner_data:
                    blocks = inner_data["blocks"]
                    text_parts = []
                    for block in blocks:
                        if block.get("type") == "markdown":
                            text_parts.append(block.get("content", ""))
                        elif block.get("type") == "text":
                            text_parts.append(block.get("content", ""))
                        elif block.get("type") == "table":
                            # 테이블 데이터도 텍스트로 변환
                            rows = block.get("rows", [])
                            for row in rows:
                                text_parts.append(" ".join(str(cell) for cell in row))
                    
                    response_text = " ".join(text_parts)
                elif "answer" in inner_data:
                    response_text = inner_data["answer"]
                elif "text" in inner_data:
                    response_text = inner_data["text"]
                elif "message" in inner_data:
                    response_text = inner_data["message"]
                else:
                    response_text = json.dumps(inner_data)
            else:
                response_text = json.dumps(data)
            
            result["response_text"] = response_text[:500]  # 처음 500자만 저장
            
            # 답변 검증
            is_correct, reason = check_answer(response_text, expected, alt_expected)
            result["success"] = is_correct
            result["reason"] = reason
            
        else:
            result["reason"] = f"HTTP {response.status_code}: {response.text[:200]}"
    
    except httpx.TimeoutException:
        result["reason"] = "Request timeout (60s)"
    except Exception as e:
        result["reason"] = f"Error: {str(e)}"
    
    return result


async def get_auth_token(client: httpx.AsyncClient) -> str | None:
    """인증 토큰을 가져옵니다."""
    # 개발 환경에서는 인증이 필요 없을 수 있음
    # 먼저 인증 없이 시도하고, 401이면 로그인 시도
    return None


async def main():
    """메인 테스트 실행 함수."""
    print("=" * 80)
    print("OPS_TEST_CASE_20 - 전체 모드 테스트")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().isoformat()}")
    print(f"API 서버: {API_BASE_URL}")
    print(f"테스트 케이스: {len(TEST_CASES)}개")
    print("=" * 80)
    
    results = []
    passed = 0
    failed = 0
    
    async with httpx.AsyncClient() as client:
        # 인증 토큰 가져오기 (필요한 경우)
        token = await get_auth_token(client)
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # 헤더 설정
        headers["Content-Type"] = "application/json"
        headers["X-Tenant-Id"] = "default"  # 테넌트 ID 설정
        
        # 각 테스트 케이스 실행
        for i, test_case in enumerate(TEST_CASES):
            print(f"\n[{test_case['id']}/{len(TEST_CASES)}] {test_case['description']}")
            print(f"  질의: {test_case['query']}")
            print(f"  예상: {test_case['expected_answer']}")
            
            result = await run_test(client, test_case, headers)
            results.append(result)
            
            if result["success"]:
                passed += 1
                print(f"  ✅ 성공: {result['reason']}")
            else:
                failed += 1
                print(f"  ❌ 실패: {result['reason']}")
            
            print(f"  응답 시간: {result['response_time_ms']}ms")
            
            # 응답 텍스트 미리보기
            if result.get("response_text"):
                preview = result["response_text"][:200]
                print(f"  응답 미리보기: {preview}...")
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    print(f"총 테스트: {len(TEST_CASES)}")
    print(f"성공: {passed}")
    print(f"실패: {failed}")
    print(f"성공률: {passed / len(TEST_CASES) * 100:.1f}%")
    
    # 결과 저장
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "success_rate": round(passed / len(TEST_CASES) * 100, 1),
        "results": results,
    }
    
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 저장됨: {RESULTS_FILE}")
    
    # 실패한 테스트 목록
    if failed > 0:
        print("\n실패한 테스트:")
        for r in results:
            if not r["success"]:
                print(f"  - Test {r['id']}: {r['description']}")
                print(f"    이유: {r['reason']}")
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(main())
    exit(0 if failed == 0 else 1)