"""
LLM Call Log Models

Tracks all LLM API calls for debugging, analytics, and cost monitoring.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Column, Field, JSON, SQLModel


class LlmCallLogBase(SQLModel):
    """Base fields for LLM call log"""

    # Relations
    trace_id: str | None = Field(default=None, index=True)
    call_type: str = Field(..., description="Type of LLM call: planner, output_parser, tool, etc", index=True)
    call_index: int = Field(default=1, description="Order index for multiple calls in same trace")

    # Input (what we sent to LLM)
    system_prompt: str | None = Field(default=None, description="System prompt sent to LLM")
    user_prompt: str | None = Field(default=None, description="User prompt sent to LLM")
    context: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON), description="Context: asset versions, tools, etc")

    # Output (what we received from LLM)
    raw_response: str | None = Field(default=None, description="Full LLM response text")
    parsed_response: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON), description="Parsed result")

    # Metadata
    model_name: str = Field(..., description="Model used: gpt-4o, claude-3-5-sonnet-20241022, etc", index=True)
    provider: str | None = Field(default=None, description="LLM provider: openai, anthropic, google, etc")
    input_tokens: int = Field(default=0, description="Input tokens consumed")
    output_tokens: int = Field(default=0, description="Output tokens consumed")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    latency_ms: int = Field(default=0, description="Round-trip latency in milliseconds")

    # Timing
    request_time: datetime = Field(..., description="When request was sent")
    response_time: datetime | None = Field(default=None, description="When response was received")
    duration_ms: int = Field(default=0, description="Calculated duration in milliseconds")

    # Status
    status: str = Field(default="success", description="success, error, timeout", index=True)
    error_message: str | None = Field(default=None, description="Error message if failed")
    error_details: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON), description="Error details if failed")

    # Feature/UI context
    feature: str | None = Field(default=None, description="Feature: ops, docs, cep, etc", index=True)
    ui_endpoint: str | None = Field(default=None, description="UI endpoint: /ops/ask, /ops/query, etc")
    user_id: UUID | None = Field(default=None, description="User who made the request")

    # Analytics
    tags: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON), description="Custom tags for filtering")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TbLlmCallLog(LlmCallLogBase, table=True):
    """LLM call log table"""

    __tablename__ = "tb_llm_call_log"

    id: UUID | None = Field(default_factory=uuid4, primary_key=True)


class LlmCallLogCreate(SQLModel):
    """Schema for creating LLM call log"""

    trace_id: str | None = None
    call_type: str
    call_index: int = 1
    system_prompt: str | None = None
    user_prompt: str | None = None
    context: dict[str, Any] | None = None
    raw_response: str | None = None
    parsed_response: dict[str, Any] | None = None
    model_name: str
    provider: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    request_time: datetime
    response_time: datetime | None = None
    duration_ms: int = 0
    status: str = "success"
    error_message: str | None = None
    error_details: dict[str, Any] | None = None
    feature: str | None = None
    ui_endpoint: str | None = None
    user_id: UUID | None = None
    tags: dict[str, Any] | None = None


class LlmCallLogRead(SQLModel):
    """Schema for reading LLM call log"""

    id: UUID
    trace_id: str | None
    call_type: str
    call_index: int
    system_prompt: str | None
    user_prompt: str | None
    context: dict[str, Any] | None
    raw_response: str | None
    parsed_response: dict[str, Any] | None
    model_name: str
    provider: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    request_time: datetime
    response_time: datetime | None
    duration_ms: int
    status: str
    error_message: str | None
    error_details: dict[str, Any] | None
    feature: str | None
    ui_endpoint: str | None
    user_id: UUID | None
    tags: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LlmCallLogSummary(SQLModel):
    """Summary of LLM call log for list views"""

    id: UUID
    trace_id: str | None
    call_type: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration_ms: int
    status: str
    feature: str | None
    ui_endpoint: str | None
    request_time: datetime
    created_at: datetime


class LlmCallLogUpdate(SQLModel):
    """Schema for updating LLM call log"""

    raw_response: str | None = None
    parsed_response: dict[str, Any] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None
    response_time: datetime | None = None
    duration_ms: int | None = None
    status: str | None = None
    error_message: str | None = None
    error_details: dict[str, Any] | None = None


class LlmCallAnalytics(SQLModel):
    """Analytics summary for LLM calls"""

    total_calls: int
    successful_calls: int
    failed_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_latency_ms: float
    total_duration_ms: int
    model_breakdown: dict[str, int]  # Model name -> call count
    feature_breakdown: dict[str, int]  # Feature -> call count
    call_type_breakdown: dict[str, int]  # Call type -> call count


class LlmCallPair(SQLModel):
    """Query-Response pair for LLM calls"""

    query: LlmCallLogRead
    response: LlmCallLogRead | None = None
