"""
CEP Rule Form Data Converter

폼 기반 규칙 데이터를 Legacy 형식으로 변환하는 유틸리티 함수들
"""

from typing import Any, Dict

from .schemas import CepRuleFormData


def convert_form_to_trigger_spec(form_data: CepRuleFormData) -> Dict[str, Any]:
    """
    폼 기반 규칙 데이터를 trigger_spec으로 변환

    Form → Legacy trigger_spec 변환

    Args:
        form_data: CepRuleFormData 객체

    Returns:
        Legacy trigger_spec dict
    """
    spec = form_data.trigger_spec.copy() if form_data.trigger_spec else {}

    # 복합 조건이 있으면 추가
    if form_data.composite_condition:
        spec["conditions"] = [
            {
                "field": c.field,
                "op": c.op,
                "value": c.value,
            }
            for c in form_data.composite_condition.conditions
        ]
        spec["logic"] = form_data.composite_condition.logic

    # 윈도우 설정이 있으면 추가
    if form_data.window_config:
        spec["window_config"] = form_data.window_config.model_dump(exclude_none=True)

    # 집계 설정이 있으면 추가
    if form_data.aggregation:
        spec["aggregation"] = form_data.aggregation.model_dump(exclude_none=True)

    # 보강 설정이 있으면 추가
    if form_data.enrichments:
        spec["enrichments"] = [
            e.model_dump(exclude_none=True) for e in form_data.enrichments
        ]

    return spec


def convert_form_to_action_spec(form_data: CepRuleFormData) -> Dict[str, Any]:
    """
    폼 기반 규칙 데이터를 action_spec으로 변환

    Form actions → Legacy action_spec 변환

    Args:
        form_data: CepRuleFormData 객체

    Returns:
        Legacy action_spec dict
    """
    if not form_data.actions:
        return {}

    if len(form_data.actions) == 1:
        # 단일 액션: 기존 형식 유지
        action = form_data.actions[0]
        spec = action.model_dump(exclude_none=True)
        return spec
    else:
        # 다중 액션: 새 형식 (다중 액션 지원)
        return {
            "type": "multi_action",
            "actions": [
                a.model_dump(exclude_none=True) for a in form_data.actions
            ],
        }


def convert_trigger_spec_to_form(
    trigger_spec: Dict[str, Any],
    trigger_type: str,
) -> Dict[str, Any]:
    """
    Legacy trigger_spec을 폼 데이터로 변환

    JSON → Form 변환

    Args:
        trigger_spec: Legacy trigger_spec dict
        trigger_type: Trigger type (metric, event, schedule)

    Returns:
        Form-compatible dict with extracted fields
    """
    form_data = {
        "trigger_type": trigger_type,
        "trigger_spec": trigger_spec.copy(),
        "composite_condition": None,
        "window_config": None,
        "aggregation": None,
        "enrichments": [],
    }

    # 복합 조건 추출
    if "conditions" in trigger_spec and isinstance(
        trigger_spec.get("conditions"), list
    ):
        form_data["composite_condition"] = {
            "conditions": trigger_spec["conditions"],
            "logic": trigger_spec.get("logic", "AND"),
        }

    # 윈도우 설정 추출
    if "window_config" in trigger_spec:
        form_data["window_config"] = trigger_spec["window_config"]

    # 집계 설정 추출
    if "aggregation" in trigger_spec:
        form_data["aggregation"] = trigger_spec["aggregation"]

    # 보강 설정 추출
    if "enrichments" in trigger_spec and isinstance(
        trigger_spec.get("enrichments"), list
    ):
        form_data["enrichments"] = trigger_spec["enrichments"]

    return form_data


def convert_action_spec_to_form(action_spec: Dict[str, Any]) -> list[Dict[str, Any]]:
    """
    Legacy action_spec을 폼 actions로 변환

    JSON → Form actions 변환

    Args:
        action_spec: Legacy action_spec dict

    Returns:
        List of action dicts compatible with form
    """
    if not action_spec:
        return []

    # 다중 액션 형식
    if action_spec.get("type") == "multi_action":
        return action_spec.get("actions", [])

    # 단일 액션 형식
    return [action_spec]


# ============================================================================
# Frontend Conversion Functions (for JSON ↔ Form sync)
# ============================================================================


def serialize_form_state(
    rule_name: str,
    trigger_type: str,
    trigger_spec: Dict[str, Any],
    action_spec: Dict[str, Any],
    composite_condition: Dict[str, Any] | None = None,
    window_config: Dict[str, Any] | None = None,
    aggregation: Dict[str, Any] | None = None,
    enrichments: list[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    폼 상태를 JSON으로 직렬화 (로컬 스토리지용)

    폼의 모든 상태를 하나의 JSON으로 직렬화하여
    로컬 스토리지에 저장하거나 다른 컴포넌트로 전달할 수 있도록 함

    Args:
        rule_name: 규칙명
        trigger_type: 트리거 타입
        trigger_spec: 트리거 스펙
        action_spec: 액션 스펙
        composite_condition: 복합 조건
        window_config: 윈도우 설정
        aggregation: 집계 스펙
        enrichments: 보강 스펙 목록

    Returns:
        직렬화된 폼 상태
    """
    return {
        "rule_name": rule_name,
        "trigger_type": trigger_type,
        "trigger_spec": trigger_spec,
        "action_spec": action_spec,
        "composite_condition": composite_condition,
        "window_config": window_config,
        "aggregation": aggregation,
        "enrichments": enrichments or [],
    }


def deserialize_form_state(
    serialized: Dict[str, Any],
) -> Dict[str, Any]:
    """
    직렬화된 폼 상태를 복원

    로컬 스토리지에서 불러온 폼 상태를 복원

    Args:
        serialized: 직렬화된 폼 상태

    Returns:
        복원된 폼 상태 dict
    """
    return {
        "rule_name": serialized.get("rule_name", ""),
        "trigger_type": serialized.get("trigger_type", "metric"),
        "trigger_spec": serialized.get("trigger_spec", {}),
        "action_spec": serialized.get("action_spec", {}),
        "composite_condition": serialized.get("composite_condition"),
        "window_config": serialized.get("window_config"),
        "aggregation": serialized.get("aggregation"),
        "enrichments": serialized.get("enrichments", []),
    }
