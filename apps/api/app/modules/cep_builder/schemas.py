from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, validator


class CepRuleBase(BaseModel):
    rule_name: str
    trigger_type: Literal["metric", "event", "schedule"]
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
    trigger_type: Literal["metric", "event", "schedule"] | None = None
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
