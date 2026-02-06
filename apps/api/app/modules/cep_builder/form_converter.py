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
