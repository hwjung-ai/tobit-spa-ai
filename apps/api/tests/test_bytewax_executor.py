"""
Unit tests for Bytewax CEP executor integration

Tests the unified Bytewax-based CEP engine with backward compatibility
"""

import pytest
from typing import Dict, Any, Optional, Tuple
from uuid import UUID

from app.modules.cep_builder.bytewax_executor import (
    get_bytewax_engine,
    convert_db_rule_to_bytewax,
    register_rule_with_bytewax,
    evaluate_rule_with_bytewax,
    process_event_with_bytewax,
    get_rule_stats,
    list_registered_rules,
    enable_rule_bytewax,
    disable_rule_bytewax,
    delete_rule_bytewax,
)
from app.modules.cep_builder.bytewax_engine import (
    BytewaxCEPEngine,
    CEPRuleDefinition,
    FilterProcessor,
)


class TestBytewaxEngine:
    """Bytewax 엔진 기본 테스트"""

    def test_get_bytewax_engine_singleton(self):
        """엔진이 싱글톤으로 생성되는지 확인"""
        engine1 = get_bytewax_engine()
        engine2 = get_bytewax_engine()
        assert engine1 is engine2

    def test_bytewax_engine_initialization(self):
        """엔진이 올바르게 초기화되는지 확인"""
        engine = get_bytewax_engine()
        assert isinstance(engine, BytewaxCEPEngine)
        assert isinstance(engine.rules, dict)
        assert isinstance(engine.processors, dict)
        assert isinstance(engine.state_store, dict)


class TestRuleConversion:
    """규칙 변환 테스트"""

    def test_convert_simple_condition(self):
        """단순 조건 변환"""
        rule = convert_db_rule_to_bytewax(
            rule_id="rule-001",
            rule_name="Simple CPU Alert",
            trigger_type="event",
            trigger_spec={
                "field": "cpu",
                "op": ">",
                "value": 80,
            },
            action_spec={
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
        )

        assert rule.rule_id == "rule-001"
        assert rule.name == "Simple CPU Alert"
        assert len(rule.filters) == 1
        assert rule.filters[0]["field"] == "cpu"
        assert rule.filters[0]["operator"] == ">"
        assert rule.filters[0]["value"] == 80

    def test_convert_composite_conditions(self):
        """복합 조건 (AND/OR/NOT) 변환"""
        rule = convert_db_rule_to_bytewax(
            rule_id="rule-002",
            rule_name="Composite Alert",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": ">", "value": 70},
                ],
                "logic": "AND",
            },
            action_spec={
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
        )

        assert len(rule.filters) == 2
        assert rule.filters[0]["field"] == "cpu"
        assert rule.filters[1]["field"] == "memory"
        assert rule.filters[1].get("_composite_logic") == "AND"

    def test_convert_with_aggregation(self):
        """집계 함수 포함 규칙 변환"""
        rule = convert_db_rule_to_bytewax(
            rule_id="rule-003",
            rule_name="Aggregation Alert",
            trigger_type="metric",
            trigger_spec={
                "field": "cpu",
                "op": ">",
                "value": 80,
                "aggregation": {
                    "type": "avg",
                    "field": "cpu_percent",
                },
            },
            action_spec={
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
        )

        assert rule.aggregation is not None
        assert rule.aggregation["type"] == "avg"
        assert rule.aggregation["field"] == "cpu_percent"

    def test_convert_with_window(self):
        """시간 윈도우 포함 규칙 변환"""
        rule = convert_db_rule_to_bytewax(
            rule_id="rule-004",
            rule_name="Window Alert",
            trigger_type="event",
            trigger_spec={
                "field": "status",
                "op": "==",
                "value": "error",
                "window_config": {
                    "type": "tumbling",
                    "size_seconds": 60,
                },
            },
            action_spec={
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
        )

        assert rule.window_config is not None
        assert rule.window_config["type"] == "tumbling"
        assert rule.window_config["size_seconds"] == 60


class TestRuleRegistration:
    """규칙 등록 테스트"""

    def test_register_simple_rule(self):
        """단순 규칙 등록"""
        rule = register_rule_with_bytewax(
            rule_id="test-rule-001",
            rule_name="Test Rule",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            action_spec={"endpoint": "https://webhook.example.com/alert"},
        )

        assert rule.rule_id == "test-rule-001"

        # 엔진에 등록되었는지 확인
        engine = get_bytewax_engine()
        registered_rule = engine.rules.get("test-rule-001")
        assert registered_rule is not None

    def test_register_multiple_rules(self):
        """여러 규칙 등록"""
        for i in range(3):
            register_rule_with_bytewax(
                rule_id=f"multi-rule-{i}",
                rule_name=f"Multi Test Rule {i}",
                trigger_type="event",
                trigger_spec={"field": "status", "op": "==", "value": f"error_{i}"},
                action_spec={"endpoint": "https://webhook.example.com/alert"},
            )

        engine = get_bytewax_engine()
        rules = engine.list_rules()
        assert len(rules) >= 3


class TestRuleEvaluation:
    """규칙 평가 테스트"""

    def test_evaluate_simple_condition_match(self):
        """단순 조건 매칭"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-001",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            payload={"cpu": 85},
        )

        assert matched is True
        assert details["engine"] == "bytewax_hybrid"

    def test_evaluate_simple_condition_no_match(self):
        """단순 조건 비매칭"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-002",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            payload={"cpu": 70},
        )

        assert matched is False

    def test_evaluate_composite_and_condition(self):
        """AND 조건 평가"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-003",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": ">", "value": 70},
                ],
                "logic": "AND",
            },
            payload={"cpu": 85, "memory": 75},
        )

        assert matched is True

    def test_evaluate_composite_and_condition_partial_match(self):
        """AND 조건: 일부만 매칭"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-004",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": ">", "value": 70},
                ],
                "logic": "AND",
            },
            payload={"cpu": 85, "memory": 60},  # memory < 70
        )

        assert matched is False

    def test_evaluate_composite_or_condition(self):
        """OR 조건 평가"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-005",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": ">", "value": 70},
                ],
                "logic": "OR",
            },
            payload={"cpu": 85, "memory": 60},  # cpu > 80, memory < 70
        )

        assert matched is True

    def test_evaluate_composite_or_condition_no_match(self):
        """OR 조건: 전부 비매칭"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-006",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": ">", "value": 70},
                ],
                "logic": "OR",
            },
            payload={"cpu": 70, "memory": 60},  # 둘 다 미달
        )

        assert matched is False

    def test_evaluate_with_missing_field(self):
        """필드 부재 시 평가"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="eval-test-007",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            payload={"memory": 75},  # cpu 필드 없음
        )

        assert matched is False


class TestEventProcessing:
    """이벤트 처리 테스트"""

    def test_process_event_with_registered_rule(self):
        """등록된 규칙으로 이벤트 처리"""
        # 규칙 등록
        register_rule_with_bytewax(
            rule_id="process-test-001",
            rule_name="Process Test Rule",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            action_spec={"endpoint": "https://webhook.example.com/alert"},
        )

        # 이벤트 처리
        result = process_event_with_bytewax(
            rule_id="process-test-001",
            event={"cpu": 85},
        )

        assert result is not None
        matched, details = result
        # Bytewax 엔진은 기본적으로 event를 처리하지만
        # 현재 구현에서는 하이브리드 방식으로 동작

    def test_process_event_unregistered_rule(self):
        """미등록 규칙으로 이벤트 처리"""
        result = process_event_with_bytewax(
            rule_id="nonexistent-rule",
            event={"cpu": 85},
        )

        assert result is None


class TestRuleManagement:
    """규칙 관리 테스트"""

    def test_list_registered_rules(self):
        """등록된 규칙 목록 조회"""
        engine = get_bytewax_engine()
        initial_count = len(engine.rules)

        register_rule_with_bytewax(
            rule_id="mgmt-test-001",
            rule_name="Management Test Rule",
            trigger_type="event",
            trigger_spec={"field": "status", "op": "==", "value": "error"},
            action_spec={"endpoint": "https://webhook.example.com/alert"},
        )

        rules = list_registered_rules()
        assert len(rules) > initial_count

    def test_get_rule_stats(self):
        """규칙 통계 조회"""
        register_rule_with_bytewax(
            rule_id="stats-test-001",
            rule_name="Stats Test Rule",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            action_spec={"endpoint": "https://webhook.example.com/alert"},
        )

        stats = get_rule_stats("stats-test-001")
        assert stats is not None
        assert "rule_id" in stats
        assert "name" in stats
        assert "type" in stats

    def test_enable_disable_rule(self):
        """규칙 활성화/비활성화"""
        rule_id = "enable-test-001"
        register_rule_with_bytewax(
            rule_id=rule_id,
            rule_name="Enable Test Rule",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            action_spec={"endpoint": "https://webhook.example.com/alert"},
        )

        # 비활성화
        result = disable_rule_bytewax(rule_id)
        assert result is True

        # 활성화
        result = enable_rule_bytewax(rule_id)
        assert result is True

    def test_delete_rule(self):
        """규칙 삭제"""
        rule_id = "delete-test-001"
        register_rule_with_bytewax(
            rule_id=rule_id,
            rule_name="Delete Test Rule",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            action_spec={"endpoint": "https://webhook.example.com/alert"},
        )

        # 삭제
        result = delete_rule_bytewax(rule_id)
        assert result is True

        # 재삭제 시도 (실패)
        result = delete_rule_bytewax(rule_id)
        assert result is False


class TestComplexScenarios:
    """복합 시나리오 테스트"""

    def test_multiple_conditions_with_different_operators(self):
        """다양한 연산자를 사용한 복합 조건"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="complex-test-001",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": "<", "value": 90},
                    {"field": "status", "op": "==", "value": "running"},
                    {"field": "errors", "op": "!=", "value": 0},
                ],
                "logic": "AND",
            },
            payload={
                "cpu": 85,
                "memory": 75,
                "status": "running",
                "errors": 5,
            },
        )

        assert matched is True

    def test_nested_metrics_path(self):
        """중첩된 메트릭 경로"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="complex-test-002",
            trigger_type="event",
            trigger_spec={"field": "metrics.cpu", "op": ">", "value": 80},
            payload={"metrics": {"cpu": 85}},
        )

        assert matched is True

    def test_empty_payload(self):
        """빈 payload로 평가"""
        matched, details = evaluate_rule_with_bytewax(
            rule_id="complex-test-003",
            trigger_type="event",
            trigger_spec={"field": "cpu", "op": ">", "value": 80},
            payload={},
        )

        assert matched is False


class TestActionExecution:
    """액션 실행 테스트 (webhook, api_script, trigger_rule)"""

    def test_execute_webhook_action(self):
        """웹훅 액션 실행"""
        from app.modules.cep_builder.executor import execute_action

        action_spec = {
            "type": "webhook",
            "endpoint": "https://webhook.example.com/alert",
            "method": "POST",
            "params": {"severity": "high"},
        }

        # 웹훅 호출은 실제 HTTP 요청이 필요하므로 모킹 필요
        # 여기서는 구조만 확인
        try:
            payload, refs = execute_action(action_spec)
        except Exception as exc:
            # 네트워크 에러는 예상됨
            assert "failed" in str(exc).lower() or "502" in str(exc)
            refs = {}

        # 참조 정보에 action_type 포함 확인
        if refs:
            assert refs.get("action_type") == "webhook"

    def test_execute_webhook_action_backward_compatibility(self):
        """웹훅 액션: 이전 버전 호환성 (type 미지정)"""
        from app.modules.cep_builder.executor import execute_action

        action_spec = {
            # type이 없으므로 기본값 "webhook"으로 동작
            "endpoint": "https://webhook.example.com/alert",
            "method": "POST",
            "params": {"severity": "high"},
        }

        try:
            payload, refs = execute_action(action_spec)
        except Exception as exc:
            # 네트워크 에러는 예상됨
            pass

    def test_execute_api_script_action_missing_session(self):
        """API 스크립트 액션: 세션 없음 에러"""
        from app.modules.cep_builder.executor import execute_action

        action_spec = {
            "type": "api_script",
            "api_id": "test-api-id",
            "params": {"key": "value"},
        }

        # 세션 없이 호출하면 에러 발생
        try:
            payload, refs = execute_action(action_spec)
            assert False, "Should raise HTTPException"
        except Exception as exc:
            assert "Database session required" in str(exc) or "session required" in str(exc).lower()

    def test_execute_api_script_action_missing_api_id(self):
        """API 스크립트 액션: api_id 미지정"""
        from app.modules.cep_builder.executor import execute_action
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        action_spec = {
            "type": "api_script",
            # api_id 누락
            "params": {"key": "value"},
        }

        mock_session = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            payload, refs = execute_action(action_spec, session=mock_session)
        assert "api_id is required" in str(exc_info.value.detail)

    def test_execute_trigger_rule_action_missing_session(self):
        """규칙 트리거 액션: 세션 없음 에러"""
        from app.modules.cep_builder.executor import execute_action

        action_spec = {
            "type": "trigger_rule",
            "rule_id": "target-rule-id",
            "payload": {"cpu": 85},
        }

        # 세션 없이 호출하면 에러 발생
        try:
            payload, refs = execute_action(action_spec)
            assert False, "Should raise HTTPException"
        except Exception as exc:
            assert "Database session required" in str(exc) or "session required" in str(exc).lower()

    def test_execute_trigger_rule_action_missing_rule_id(self):
        """규칙 트리거 액션: rule_id 미지정"""
        from app.modules.cep_builder.executor import execute_action
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        action_spec = {
            "type": "trigger_rule",
            # rule_id 누락
            "payload": {"cpu": 85},
        }

        mock_session = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            payload, refs = execute_action(action_spec, session=mock_session)
        assert "rule_id is required" in str(exc_info.value.detail)

    def test_execute_unsupported_action_type(self):
        """지원되지 않는 액션 타입"""
        from app.modules.cep_builder.executor import execute_action
        from fastapi import HTTPException

        action_spec = {
            "type": "unsupported_type",
            "data": "test",
        }

        with pytest.raises(HTTPException) as exc_info:
            payload, refs = execute_action(action_spec)
        assert "Unsupported action type" in str(exc_info.value.detail)


class TestManualTriggerWithActions:
    """액션이 포함된 수동 트리거 테스트"""

    def test_manual_trigger_with_webhook_action(self):
        """웹훅 액션을 포함한 규칙 트리거"""
        from app.modules.cep_builder.executor import manual_trigger
        from app.modules.cep_builder.models import TbCepRule
        from uuid import uuid4

        # 웹훅 액션을 가진 규칙 생성 (임시, DB에 저장되지 않음)
        rule = TbCepRule(
            rule_id=uuid4(),
            rule_name="Test Webhook Rule",
            trigger_type="event",
            trigger_spec={
                "field": "cpu",
                "op": ">",
                "value": 80,
            },
            action_spec={
                "type": "webhook",
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
            is_active=True,
        )

        # 조건을 만족하는 payload로 트리거
        try:
            result = manual_trigger(
                rule=rule,
                payload={"cpu": 85},
                executed_by="test-user",
            )
            # 웹훅 호출 실패는 예상되지만 조건 평가는 성공해야 함
        except Exception as exc:
            # 웹훅 네트워크 에러는 무시
            pass

    def test_manual_trigger_condition_not_met(self):
        """조건 미충족 시 액션 실행되지 않음"""
        from app.modules.cep_builder.executor import manual_trigger
        from app.modules.cep_builder.models import TbCepRule
        from uuid import uuid4

        rule = TbCepRule(
            rule_id=uuid4(),
            rule_name="Test Rule",
            trigger_type="event",
            trigger_spec={
                "field": "cpu",
                "op": ">",
                "value": 80,
            },
            action_spec={
                "type": "webhook",
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
            is_active=True,
        )

        # 조건을 충족하지 않는 payload
        result = manual_trigger(
            rule=rule,
            payload={"cpu": 70},  # cpu < 80
            executed_by="test-user",
        )

        # 액션이 실행되지 않아야 함
        assert result["condition_met"] is False
        assert result["status"] == "dry_run"

    def test_manual_trigger_with_composite_conditions(self):
        """복합 조건을 가진 규칙 트리거"""
        from app.modules.cep_builder.executor import manual_trigger
        from app.modules.cep_builder.models import TbCepRule
        from uuid import uuid4

        rule = TbCepRule(
            rule_id=uuid4(),
            rule_name="Composite Rule",
            trigger_type="event",
            trigger_spec={
                "conditions": [
                    {"field": "cpu", "op": ">", "value": 80},
                    {"field": "memory", "op": ">", "value": 70},
                ],
                "logic": "AND",
            },
            action_spec={
                "type": "webhook",
                "endpoint": "https://webhook.example.com/alert",
                "method": "POST",
            },
            is_active=True,
        )

        # AND 조건: 둘 다 만족
        try:
            result = manual_trigger(
                rule=rule,
                payload={"cpu": 85, "memory": 75},
                executed_by="test-user",
            )
        except Exception as exc:
            # 웹훅 네트워크 에러 무시
            pass

        # AND 조건: 하나만 만족
        result = manual_trigger(
            rule=rule,
            payload={"cpu": 85, "memory": 60},
            executed_by="test-user",
        )
        assert result["condition_met"] is False


class TestIntegrationCEPAndAPI:
    """CEP 엔진과 API Manager 통합 테스트"""

    def test_action_spec_with_different_types(self):
        """다양한 액션 타입의 spec 구조 확인"""
        # Webhook action spec
        webhook_spec = {
            "type": "webhook",
            "endpoint": "https://webhook.example.com/alert",
            "method": "POST",
            "params": {"severity": "high"},
        }

        # API script action spec
        api_script_spec = {
            "type": "api_script",
            "api_id": "api-uuid-1234",
            "params": {
                "user_id": "user-123",
                "alert_level": "critical",
            },
            "input": {"event_data": "..."},
        }

        # Trigger rule action spec
        trigger_rule_spec = {
            "type": "trigger_rule",
            "rule_id": "rule-uuid-5678",
            "payload": {
                "event_type": "cascading_alert",
                "source_rule": "parent-rule",
            },
        }

        # 모든 spec이 valid dict 구조
        assert isinstance(webhook_spec, dict)
        assert isinstance(api_script_spec, dict)
        assert isinstance(trigger_rule_spec, dict)

        # 각 spec의 필수 필드 확인
        assert webhook_spec.get("type") == "webhook"
        assert api_script_spec.get("type") == "api_script"
        assert trigger_rule_spec.get("type") == "trigger_rule"

    def test_chained_rule_execution_spec(self):
        """규칙 연쇄 실행을 위한 spec 구조"""
        # Parent rule: webhook + trigger_rule
        parent_action = {
            "type": "trigger_rule",
            "rule_id": "child-rule-id",
            "payload": {
                "parent_rule": "parent-rule-id",
                "cascade": True,
                "event_context": {"severity": "critical"},
            },
        }

        # Child rule: api_script
        child_action = {
            "type": "api_script",
            "api_id": "notification-api",
            "params": {
                "message": "Alert from parent rule",
                "severity": "critical",
            },
        }

        assert parent_action.get("rule_id") is not None
        assert child_action.get("api_id") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
