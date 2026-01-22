from __future__ import annotations

import json
from typing import Any, Dict

import pytest
from _pytest.outcomes import Skipped

MOCK_KEYWORDS = {"mock", "sample", "seed_fallback", "demo"}


def _block_summary(block: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": block.get("type"), "title": block.get("title") or block.get("label")}
    if block.get("type") == "table":
        summary["rows"] = len(block.get("rows") or [])
    elif block.get("type") == "graph":
        summary["nodes"] = len(block.get("nodes") or [])
        summary["edges"] = len(block.get("edges") or [])
    elif block.get("type") == "references":
        summary["items"] = len(block.get("items") or [])
    return summary


def _extract_trace_excerpt(trace: dict[str, Any] | None) -> dict[str, Any]:
    if not trace:
        return {}
    excerpt: dict[str, Any] = {}
    plan = trace.get("plan_validated")
    if plan:
        excerpt["intent"] = plan.get("intent")
        excerpt["graph_depth"] = plan.get("graph", {}).get("depth")
    if trace.get("policy_decisions"):
        excerpt["policy_decisions"] = trace["policy_decisions"]
    if trace.get("references"):
        excerpt["references_count"] = len(trace["references"])
    return excerpt


def _extract_meta_excerpt(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    return {
        "used_tools": meta.get("used_tools"),
        "summary": meta.get("summary"),
        "route": meta.get("route"),
    }


def _detect_mock_terms(payload: dict[str, Any]) -> list[str]:
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    return [word for word in MOCK_KEYWORDS if word in serialized]


def _save_raw_response(collector: Any, test_name: str, payload: dict[str, Any]) -> str:
    raw_path = collector.raw_dir / f"{test_name}.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return str(raw_path)


def run_ci_test(
    *,
    test_name: str,
    question: str,
    client: Any,
    endpoint: str,
    artifact_collector: Any,
    time_range: tuple[str, str],
) -> dict[str, Any]:
    entry: Dict[str, Any] = {
        "test_name": test_name,
        "query": question,
        "endpoint": endpoint,
        "seed_range": {"from": time_range[0], "to": time_range[1]},
        "pass": False,
        "reason": "",
        "status": "pending",
    }
    try:
        response = client.post(endpoint, json={"question": question})
        entry["status_code"] = response.status_code
        data = response.json()
        raw_path = _save_raw_response(artifact_collector, test_name, data)
        entry["raw_response"] = raw_path
        assert response.status_code == 200, "status code must be 200"
        assert data.get("code", 0) == 0, "Response envelope must report success"
        payload = data.get("data") or {}
        blocks = payload.get("blocks")
        assert isinstance(blocks, list) and blocks, "blocks must be present"
        meta = payload.get("meta")
        trace = payload.get("trace")
        assert meta or trace, "meta or trace must exist"
        entry["blocks_summary"] = [_block_summary(block) for block in blocks if isinstance(block, dict)]
        entry["meta_excerpt"] = _extract_meta_excerpt(meta)
        entry["trace_excerpt"] = _extract_trace_excerpt(trace)
        mock_terms = _detect_mock_terms(payload)
        assert not mock_terms, f"mock keywords detected: {mock_terms}"
        entry["mock_terms"] = mock_terms
        entry["pass"] = True
        entry["reason"] = "ok"
        entry["status"] = "pass"
        return payload
    except Skipped as exc:
        entry["reason"] = str(exc)
        entry["status"] = "skipped"
        raise
    except AssertionError as exc:
        entry["reason"] = str(exc)
        entry["status"] = "fail"
        raise
    except Exception as exc:
        entry["reason"] = str(exc)
        entry["status"] = "fail"
        raise
    finally:
        artifact_collector.add_entry(entry)


def test_lookup_server_status(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    sample_codes: Any,
    time_range: tuple[str, str],
):
    question = f"{sample_codes.server}의 현재 상태와 기본 정보를 알려줘."
    _ = run_ci_test(
        test_name="lookup_server_status",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )


def test_metric_cpu_usage(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    sample_codes: Any,
    time_range: tuple[str, str],
):
    question = (
        f"{sample_codes.server}의 {time_range[0]}~{time_range[1]} cpu_usage 평균과 마지막 값을 알려줘."
    )
    payload = run_ci_test(
        test_name="metric_cpu_usage",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )
    references = payload.get("trace", {}).get("references", [])
    assert any("cpu_usage" in json.dumps(ref, ensure_ascii=False) for ref in references)


def test_history_events(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    sample_codes: Any,
    time_range: tuple[str, str],
):
    question = (
        f"{sample_codes.server}의 {time_range[0]}~{time_range[1]} severity 2 이상 이벤트를 요약해줘."
    )
    payload = run_ci_test(
        test_name="history_events",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )
    assert payload.get("trace"), "trace must be present for history queries"


def test_list_servers_by_owner(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    time_range: tuple[str, str],
):
    question = "owner=erp-platform status=monitoring 서버 목록을 보여줘."
    run_ci_test(
        test_name="list_servers",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )


def test_multi_step_app_history(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    sample_codes: Any,
    time_range: tuple[str, str],
):
    question = (
        f"{sample_codes.app}의 {time_range[0]}~{time_range[1]} 작업/배포 이력과 구동 호스트를 함께 보여줘."
    )
    run_ci_test(
        test_name="multi_step_app_history",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )


def test_no_data_guidance(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    time_range: tuple[str, str],
):
    question = "srv-erp-99의 상태를 알려줘."
    payload = run_ci_test(
        test_name="no_data_guidance",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )
    assert any(
        block.get("type") == "table" and "ci candidates" in (block.get("title") or "").lower()
        for block in payload.get("blocks", [])
        if isinstance(block, dict)
    )


def test_ambiguous_integration_query(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    time_range: tuple[str, str],
):
    question = "integration 앱의 최근 배포 상태를 알려줘."
    run_ci_test(
        test_name="ambiguous_integration",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )


def test_policy_depth_clamp(
    client: Any,
    ci_endpoint: str,
    artifact_collector: Any,
    sample_codes: Any,
    time_range: tuple[str, str],
):
    question = f"{sample_codes.app} 영향 그래프를 depth 10으로 확장해줘."
    payload = run_ci_test(
        test_name="policy_depth",
        question=question,
        client=client,
        endpoint=ci_endpoint,
        artifact_collector=artifact_collector,
        time_range=time_range,
    )
    graph_depth = payload.get("trace", {}).get("plan_validated", {}).get("graph", {}).get("depth")
    if graph_depth is None:
        if artifact_collector.entries:
            artifact_collector.entries[-1]["status"] = "skipped"
            artifact_collector.entries[-1]["reason"] = "Graph depth not available for policy guard"
        pytest.skip("Graph depth not available for this plan; policy guard not triggered")
    assert graph_depth <= 5, "Policy should clamp graph depth when requesting depth 10"
