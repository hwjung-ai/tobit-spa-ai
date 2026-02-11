"""
LLM Module - LLM Call Logging

Tracks all LLM API calls for debugging, analytics, and cost monitoring.
"""

from .models import (
    TbLlmCallLog,
    LlmCallLogCreate,
    LlmCallLogRead,
    LlmCallLogSummary,
    LlmCallLogUpdate,
    LlmCallAnalytics,
    LlmCallPair,
)
from .crud import (
    create_llm_call_log,
    get_llm_call_log,
    list_llm_call_logs,
    get_llm_call_logs_by_trace,
    get_llm_analytics,
    get_llm_call_pairs,
    to_read_model,
    to_summary_model,
)
from app.llm.client import LlmClient, get_llm_client, LlmCallLogger

__all__ = [
    # Models
    "TbLlmCallLog",
    "LlmCallLogCreate",
    "LlmCallLogRead",
    "LlmCallLogSummary",
    "LlmCallLogUpdate",
    "LlmCallAnalytics",
    "LlmCallPair",
    # CRUD
    "create_llm_call_log",
    "get_llm_call_log",
    "list_llm_call_logs",
    "get_llm_call_logs_by_trace",
    "get_llm_analytics",
    "get_llm_call_pairs",
    "to_read_model",
    "to_summary_model",
    # Client
    "LlmClient",
    "get_llm_client",
    "LlmCallLogger",
]
