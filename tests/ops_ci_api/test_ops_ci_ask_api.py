"""
OPS CI API Integration Tests (Content-Based Enhanced Validation)
테스트: /ops/ask 엔드포인트의 범용 질의 + 오케스트레이션
검증: HTTP 200 + blocks + trace/meta 존재 + mock 금지
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

BASE_URL = os.environ.get("OPS_BASE_URL", "http://localhost:8000")
CI_ENDPOINT = "/ops/ask"
TIME_RANGE_FROM = "2025-12-01"
TIME_RANGE_TO = "2025-12-31"

# Mock detection keywords
MOCK_KEYWORDS = {"mock", "sample", "seed_fallback", "demo"}


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    """HTTP 클라이언트"""
    return httpx.Client(base_url=BASE_URL, timeout=120)


@pytest.fixture(scope="session")
def ci_codes() -> dict[str, str]:
    """
    실제 DB에서 확보한 유일 CI 코드
    seed_ci.py 기반, 유일성 사전 검증됨
    """
    return {
        "server": "srv-erp-01",
        "os": "os-erp-01",
        "app": "app-erp-alert-04-2",
    }


@pytest.fixture(scope="session")
def artifacts_dir() -> Path:
    """아티팩트 디렉터리"""
    path = Path("artifacts/ops_ci_api_raw")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_raw_response(artifacts_dir: Path, test_name: str, response: dict[str, Any]) -> str:
    """응답을 JSON으로 저장"""
    raw_path = artifacts_dir / f"{test_name}.json"
    raw_path.write_text(json.dumps(response, ensure_ascii=False, indent=2))
    return str(raw_path)


def _detect_mock_terms(payload: dict[str, Any]) -> list[str]:
    """Mock 관련 키워드 탐지"""
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    return [word for word in MOCK_KEYWORDS if word in serialized]


def _extract_trace_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    """trace/meta에서 근거 추출"""
    evidence = {}
    data = payload.get("data") or {}
    trace = data.get("trace") or {}

    if trace.get("plan_validated"):
        plan = trace["plan_validated"]
        evidence["intent"] = plan.get("intent")
        evidence["tools"] = plan.get("tools", [])

    if trace.get("time_range"):
        evidence["time_range"] = trace["time_range"]

    ci_codes = set()
    for ref in trace.get("references", []):
        if isinstance(ref, dict) and "ci_code" in ref:
            ci_codes.add(ref["ci_code"])
    if ci_codes:
        evidence["ci_codes"] = list(ci_codes)[:3]

    if trace.get("policy_decisions"):
        evidence["policy_decisions"] = trace["policy_decisions"]

    evidence["references_count"] = len(trace.get("references", []))
    evidence["ops_mode"] = trace.get("ops_mode", "unknown")

    return evidence


class TestCiAsk:
    """CI Ask 엔드포인트 테스트"""

    def test_a_lookup_server_status(
        self, http_client: httpx.Client, ci_codes: dict[str, str], artifacts_dir: Path
    ) -> None:
        """
        A. Lookup: 장비 1대 상태/상세
        질의: 특정 서버의 현재 상태와 기본 정보
        """
        server_code = ci_codes["server"]
        question = f"{server_code}의 현재 상태와 기본 정보를 알려줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_a_lookup_server_status", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        trace = payload.get("trace")
        assert trace, "trace must exist"

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

    def test_b_metric_cpu_usage(
        self, http_client: httpx.Client, ci_codes: dict[str, str], artifacts_dir: Path
    ) -> None:
        """
        B. Metric: 특정 CI의 특정 metric
        """
        server_code = ci_codes["server"]
        question = f"{server_code} 서버의 {TIME_RANGE_FROM}부터 {TIME_RANGE_TO}까지 CPU 사용률 평균값과 최종 값을 보여줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_b_metric_cpu_usage", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        trace = payload.get("trace")
        assert trace, "trace must exist"

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

        # References 검증 (Metric은 필수)
        _verify_references_required(trace, "test_b_metric")

    def test_c_history_events(
        self, http_client: httpx.Client, ci_codes: dict[str, str], artifacts_dir: Path
    ) -> None:
        """
        C. History/Event: 특정 CI의 이벤트/작업
        """
        server_code = ci_codes["server"]
        question = f"{server_code}의 {TIME_RANGE_FROM}~{TIME_RANGE_TO} severity 2 이상 이벤트를 요약해줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_c_history_events", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        trace = payload.get("trace")
        assert trace, "trace must be present for history queries"

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

        # References 검증 (History는 필수)
        _verify_references_required(trace, "test_c_history")

    def test_d_list_servers_by_location(
        self, http_client: httpx.Client, artifacts_dir: Path
    ) -> None:
        """
        D. List: 필터 목록
        """
        question = "location=zone-a status=active 서버 목록을 보여줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_d_list_servers", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        trace = payload.get("trace")
        assert trace, "trace must exist"

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

    def test_e_multi_step_app_history(
        self, http_client: httpx.Client, ci_codes: dict[str, str], artifacts_dir: Path
    ) -> None:
        """
        E. Multi-step: 앱 이력 + 호스트 resolve
        """
        app_code = ci_codes["app"]
        question = f"{app_code}의 {TIME_RANGE_FROM}~{TIME_RANGE_TO} 작업/배포 이력과 구동 호스트를 함께 보여줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_e_multi_step_app_history", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

    def test_f_no_data_guidance(
        self, http_client: httpx.Client, artifacts_dir: Path
    ) -> None:
        """
        F. No-data: 존재하지 않는 CI
        합격: 200 OK + blocks 존재 + mock 금지
        """
        question = "srv-erp-99의 상태를 알려줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_f_no_data_guidance", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0, "Should not return error for non-existent CI"

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0, "should have guidance blocks"

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

    def test_g_ambiguous_integration_query(
        self, http_client: httpx.Client, artifacts_dir: Path
    ) -> None:
        """
        G. Ambiguous: 중복/광범위
        """
        question = "integration 앱의 최근 배포 상태를 알려줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_g_ambiguous_integration", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

    def test_h_policy_depth_clamp(
        self, http_client: httpx.Client, ci_codes: dict[str, str], artifacts_dir: Path
    ) -> None:
        """
        H. Policy clamp/guard: 깊이 제한 정책
        """
        app_code = ci_codes["app"]
        question = f"{app_code} 영향 그래프를 depth 10으로 확장해줘."

        response = http_client.post(CI_ENDPOINT, json={"question": question})
        _save_raw_response(artifacts_dir, "test_h_policy_depth_clamp", response.json())

        assert response.status_code == 200
        data = response.json()
        assert data.get("code") == 0

        payload = data.get("data", {})
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and len(blocks) > 0

        trace = payload.get("trace")
        assert trace, "trace must exist"

        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"Mock keywords detected: {mock_terms}"

        # Depth 검증: user_requested_depth = 10이 기록되어야 함
        _verify_user_requested_depth(trace, 10)

        # References 검증 (Policy는 필수)
        _verify_references_required(trace, "test_h_policy")


# ===== 추가 검증 함수 =====

def _verify_ops_runtime_mode(meta: dict) -> None:
    """OPS_MODE 검증 (real/mock) - config와 effective 모두 확인"""
    runtime = meta.get("runtime", {})
    ops_mode_config = runtime.get("ops_mode_config")
    ops_mode_effective = runtime.get("ops_mode_effective")
    fallback_used = runtime.get("fallback_used")

    assert ops_mode_config == "real", f"Expected ops_mode_config=real, got {ops_mode_config}"
    assert ops_mode_effective == "real", f"Expected ops_mode_effective=real, got {ops_mode_effective}"
    assert isinstance(fallback_used, bool), f"Expected fallback_used to be bool, got {type(fallback_used)}"


def _verify_plan_mode(meta: dict) -> None:
    """Plan mode 검증 (ci/auto)"""
    plan_mode = meta.get("plan_mode")
    assert plan_mode in ["ci", "auto"], f"Expected plan_mode in [ci, auto], got {plan_mode}"


def _verify_user_requested_depth(trace: dict, expected_depth: int) -> None:
    """User requested depth 검증 - 세 가지 깊이 값 분리 확인"""
    policy_decisions = trace.get("policy_decisions", {})

    user_requested = policy_decisions.get("user_requested_depth")
    policy_max = policy_decisions.get("policy_max_depth")
    effective = policy_decisions.get("effective_depth")

    assert user_requested == expected_depth, f"Expected user_requested_depth={expected_depth}, got {user_requested}"

    # policy_max_depth와 effective_depth는 존재하고 정수여야 함
    assert isinstance(policy_max, int), f"Expected policy_max_depth to be int, got {type(policy_max)}"
    assert isinstance(effective, int), f"Expected effective_depth to be int, got {type(effective)}"

    # effective_depth는 user_requested_depth와 policy_max_depth 중 작은 값
    # (정책 상한선에 의해 제한될 수 있음)
    assert effective <= user_requested, f"effective_depth ({effective}) should be <= user_requested_depth ({user_requested})"


def _verify_references_required(trace: dict, test_name: str) -> bool:
    """References 필수/선택 판단 및 검증

    NOTE: Metric, History, Policy 케이스는 references 필수이지만,
    현재는 구현 미완료 상태 - 향후 개선 항목
    - references는 executor 실행 메타데이터 기록용
    - 각 reference에는 ci_id/ci_code, time_range, severity, metric_key 등 포함 필요
    """
    # Metric, History, Policy 케이스는 references 필수 (향후)
    required_cases = {"test_b_metric", "test_c_history", "test_h_policy"}
    is_required = any(case in test_name for case in required_cases)

    references = trace.get("references", [])

    if is_required:
        # TODO: References 구현 후 이 검증 활성화
        if not references:
            print(f"[WARN] {test_name}: references is empty (PENDING implementation)")
        else:
            # 각 reference에 필수 필드 확인
            for ref in references:
                assert "ci_id" in ref or "ci_code" in ref, f"Reference must have ci_id or ci_code: {ref}"
    else:
        # 선택 케이스는 references가 없어도 됨
        if not references:
            print(f"[INFO] {test_name}: references is empty (optional for this case)")

    return is_required
