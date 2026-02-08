from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, validator


class CepRuleBase(BaseModel):
    rule_name: str
    trigger_type: Literal["metric", "event", "schedule", "anomaly"]
    trigger_spec: Dict[str, Any] = Field(default_factory=dict)
    action_spec: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_by: str | None = None

    @validator("trigger_spec", "action_spec", pre=True, always=True)
    def ensure_dict(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        raise ValueError("must be a JSON object")


class CepRuleCreate(CepRuleBase):
    pass


class CepRuleUpdate(BaseModel):
    rule_name: str | None = None
    trigger_type: Literal["metric", "event", "schedule", "anomaly"] | None = None
    trigger_spec: Dict[str, Any] | None = None
    action_spec: Dict[str, Any] | None = None
    is_active: bool | None = None
    created_by: str | None = None

    @validator("trigger_spec", "action_spec", pre=True, always=True)
    def ensure_dict_or_none(cls, value: Any) -> Dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        raise ValueError("must be a JSON object")


class CepRuleRead(CepRuleBase):
    rule_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @validator("rule_id", pre=True, always=True)
    def normalize_rule_id(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value


class CepSimulateRequest(BaseModel):
    test_payload: Dict[str, Any] | None = None


class CepSimulateResponse(BaseModel):
    condition_evaluated: bool
    would_execute: bool
    resolved_action: Dict[str, Any]
    references: Dict[str, Any]


class CepTriggerRequest(BaseModel):
    payload: Dict[str, Any] | None = None
    executed_by: str | None = None


class CepTriggerResponse(BaseModel):
    status: str
    result: Dict[str, Any] | None = None
    references: Dict[str, Any]


class CepExecLogRead(BaseModel):
    exec_id: str
    rule_id: str
    triggered_at: datetime
    status: str
    duration_ms: int
    error_message: str | None
    references: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

    @validator("exec_id", "rule_id", pre=True, always=True)
    def normalize_exec_ids(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value


class CepNotificationBase(BaseModel):
    name: str
    channel: Literal["webhook"]
    webhook_url: str
    rule_id: str | None = None
    headers: Dict[str, Any] = Field(default_factory=dict)
    trigger: Dict[str, Any] = Field(default_factory=dict)
    policy: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @validator("headers", "trigger", "policy", pre=True, always=True)
    def ensure_dict(cls, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        raise ValueError("must be a JSON object")


class CepNotificationCreate(CepNotificationBase):
    pass


class CepNotificationUpdate(BaseModel):
    name: str | None = None
    channel: Literal["webhook"] | None = None
    webhook_url: str | None = None
    headers: Dict[str, Any] | None = None
    trigger: Dict[str, Any] | None = None
    policy: Dict[str, Any] | None = None
    is_active: bool | None = None

    @validator("headers", "trigger", "policy", pre=True, always=True)
    def ensure_dict_or_none(cls, value: Any) -> Dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        raise ValueError("must be a JSON object")


class CepNotificationRead(CepNotificationBase):
    notification_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @validator("notification_id", pre=True, always=True)
    def normalize_notification_id(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value


class CepNotificationLogRead(BaseModel):
    log_id: str
    notification_id: str
    fired_at: datetime
    status: str
    reason: str | None
    payload: Dict[str, Any]
    response_status: int | None
    response_body: str | None
    dedup_key: str | None
    ack: bool
    ack_at: datetime | None
    ack_by: str | None

    model_config = ConfigDict(from_attributes=True)

    @validator("log_id", "notification_id", pre=True, always=True)
    def normalize_notification_ids(cls, value: Any) -> str:
        if isinstance(value, uuid.UUID):
            return str(value)
        return value


class CepEventRead(BaseModel):
    event_id: str
    triggered_at: datetime
    status: str
    summary: str
    severity: str
    ack: bool
    ack_at: datetime | None = None
    rule_id: str | None
    rule_name: str | None
    notification_id: str


class CepEventDetail(BaseModel):
    event_id: str
    triggered_at: datetime
    status: str
    reason: str | None
    summary: str
    severity: str
    ack: bool
    ack_at: datetime | None
    ack_by: str | None
    notification_id: str
    rule_id: str | None
    rule_name: str | None
    payload: Dict[str, Any]
    condition_evaluated: bool | None = None
    extracted_value: Any | None = None
    exec_log: Dict[str, Any] | None = None


class CepEventSummary(BaseModel):
    unacked_count: int
    by_severity: Dict[str, int]


# ============================================================================
# Phase 2: Form-based UI Schemas
# ============================================================================


class ConditionSpec(BaseModel):
    """단일 조건 명세"""
    field: str
    op: Literal["==", "!=", ">", ">=", "<", "<=", "in", "contains"]
    value: Any
    case_sensitive: bool = True


class CompositeCondition(BaseModel):
    """복합 조건 (AND/OR/NOT)"""
    conditions: list[ConditionSpec]
    logic: Literal["AND", "OR", "NOT"] = "AND"


class WindowConfig(BaseModel):
    """시간 윈도우 설정"""
    type: Literal["tumbling", "sliding", "session"]
    size_seconds: int
    slide_seconds: int | None = None  # sliding window용
    gap_seconds: int | None = None    # session window용


class AggregationSpec(BaseModel):
    """집계 명세"""
    type: Literal["count", "sum", "avg", "min", "max", "std", "percentile"]
    group_by: str | None = None
    field: str | None = None
    percentile_value: float | None = None


class EnrichmentSpec(BaseModel):
    """데이터 보강 명세"""
    type: Literal["lookup", "calculate", "api_call"]
    name: str
    source: str  # "database", "cache", "api"
    key: str
    table: str | None = None
    endpoint: str | None = None
    formula: str | None = None


class ActionSpecV2(BaseModel):
    """액션 명세 (V2: 다중 액션 타입 지원)"""
    type: Literal["notify", "store", "trigger", "webhook"]
    endpoint: str | None = None
    method: Literal["GET", "POST", "PUT", "DELETE"] | None = None
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    body: Dict[str, Any] | None = None
    channels: list[str] | None = None
    message: str | None = None
    target_rule_id: str | None = None


class CepRuleFormData(BaseModel):
    """폼 기반 규칙 데이터"""
    rule_name: str
    description: str | None = None
    is_active: bool = True
    trigger_type: Literal["metric", "event", "schedule", "anomaly"]
    trigger_spec: Dict[str, Any]

    # 복합 조건 (선택사항)
    composite_condition: CompositeCondition | None = None

    # 기타 설정
    window_config: WindowConfig | None = None
    aggregation: AggregationSpec | None = None
    enrichments: list[EnrichmentSpec] = Field(default_factory=list)
    actions: list[ActionSpecV2] = Field(min_length=1)


class ValidationResult(BaseModel):
    """검증 결과"""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class PreviewResult(BaseModel):
    """규칙 미리보기 결과"""
    condition_matched: bool
    matched_conditions: list[str] = Field(default_factory=list)
    failed_conditions: list[str] = Field(default_factory=list)
    condition_evaluation_tree: Dict[str, Any] | None = None
    would_execute: bool
    references: Dict[str, Any] = Field(default_factory=dict)


class FieldInfo(BaseModel):
    """필드 정보 (자동완성용)"""
    name: str
    description: str | None = None
    type: str
    examples: list[Any] = Field(default_factory=list)


class ConditionTemplate(BaseModel):
    """조건 템플릿"""
    id: str
    name: str
    description: str
    operator: str
    example_value: Any
    category: str
