from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from uuid import UUID

from core.config import get_settings
from openai import AsyncOpenAI, OpenAI
from sqlmodel import Session


class LlmClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.default_model = settings.chat_model
        if not self.api_key:
            logging.warning("OpenAI API key is missing. LLM calls will fail.")

        # Set reasonable timeout to prevent hanging indefinitely
        # timeout: 60 seconds for connection, 120 seconds for read
        self.client = OpenAI(api_key=self.api_key, timeout=120.0)
        self.async_client = AsyncOpenAI(api_key=self.api_key, timeout=120.0)

    def create_response(
        self,
        input: Union[List[Dict[str, str]], str],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Any:
        """
        Synchronous wrapper for client.responses.create
        """
        model = model or self.default_model
        logging.debug(
            "LLM create_response: model=%s, input=%s", model, str(input)[:100]
        )
        return self.client.responses.create(
            model=model,
            input=input,
            tools=tools,
            stream=False,
            **kwargs,
        )

    async def acreate_response(
        self,
        input: Union[List[Dict[str, str]], str],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Any:
        """
        Asynchronous wrapper for client.responses.create
        """
        model = model or self.default_model
        logging.debug(
            "LLM acreate_response: model=%s, input=%s", model, str(input)[:100]
        )
        return await self.async_client.responses.create(
            model=model,
            input=input,
            tools=tools,
            stream=False,
            **kwargs,
        )

    async def stream_response(
        self,
        input: Union[List[Dict[str, str]], str],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generator for streaming responses using the Responses API.
        Yields raw events from the stream.
        """
        model = model or self.default_model
        logging.debug(
            "LLM stream_response: model=%s, input=%s", model, str(input)[:100]
        )

        # Note: openai-python SDK handles the SSE iteration automatically
        async with await self.async_client.responses.create(
            model=model,
            input=input,
            tools=tools,
            stream=True,
            **kwargs,
        ) as stream:
            async for event in stream:
                # Use event.to_dict() or model_dump() to ensure we have a dictionary
                if hasattr(event, "model_dump"):
                    yield event.model_dump()
                elif hasattr(event, "to_dict"):
                    yield event.to_dict()
                else:
                    yield event

    def embed(
        self, input: Union[str, List[str]], model: Optional[str] = None, **kwargs
    ) -> Any:
        """
        Embeddings still use the /v1/embeddings endpoint.
        """
        settings = get_settings()
        model = model or settings.embed_model
        return self.client.embeddings.create(input=input, model=model, **kwargs)

    @staticmethod
    def get_output_text(response: Any) -> str:
        """
        Extract output_text from a Responses API response object or dict.
        """
        if hasattr(response, "output_text"):
            return response.output_text or ""
        if isinstance(response, dict):
            return response.get("output_text") or ""
        return ""

    async def chat_completion(self, messages: List[Dict[str, str]], model: str = None, temperature: float = 0.5, **kwargs) -> Dict[str, Any]:
        """
        Chat completion interface (wrapper around acreate_response).
        """
        model = model or self.default_model
        input_data = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        response = await self.acreate_response(input=input_data, model=model, **kwargs)
        return {"content": self.get_output_text(response)}

    @staticmethod
    def get_output_items(response: Any) -> List[Dict[str, Any]]:
        """
        Extract output_items (including tool calls) from a response object or dict.
        """
        items = []
        if hasattr(response, "output_items"):
            items = response.output_items or []
        elif isinstance(response, dict):
            items = response.get("output_items") or []

        # Ensure all items are dicts
        processed = []
        for item in items:
            if hasattr(item, "model_dump"):
                processed.append(item.model_dump())
            elif hasattr(item, "to_dict"):
                processed.append(item.to_dict())
            else:
                processed.append(item)
        return processed


_instance: Optional[LlmClient] = None


def get_llm_client() -> LlmClient:
    global _instance
    if _instance is None:
        _instance = LlmClient()
    return _instance


# =============================================
# LLM Call Logging
# =============================================

class LlmCallLogger:
    """
    Context manager for logging LLM calls

    Usage:
        async with LlmCallLogger(
            session=session,
            call_type="planner",
            model_name="gpt-4o",
            trace_id=trace_id,
            feature="ops",
        ) as logger:
            response = await llm.acreate_response(...)
            logger.log_response(response)
    """

    def __init__(
        self,
        session: Session,
        call_type: str,
        model_name: str,
        trace_id: UUID | None = None,
        feature: str | None = None,
        ui_endpoint: str | None = None,
        user_id: UUID | None = None,
        context: dict[str, Any] | None = None,
        provider: str | None = None,
    ):
        self.session = session
        self.call_type = call_type
        self.model_name = model_name
        self.trace_id = trace_id
        self.feature = feature
        self.ui_endpoint = ui_endpoint
        self.user_id = user_id
        self.context = context or {}
        self.provider = provider or self._detect_provider(model_name)

        self.request_time = datetime.utcnow()
        self.response_time: datetime | None = None
        self.duration_ms = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

        self.system_prompt: str | None = None
        self.user_prompt: str | None = None
        self.raw_response: str | None = None
        self.parsed_response: dict[str, Any] | None = None

        self.status = "success"
        self.error_message: str | None = None
        self.error_details: dict[str, Any] | None = None

    def _detect_provider(self, model_name: str) -> str:
        """Detect LLM provider from model name"""
        model_lower = model_name.lower()
        if "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower or "vertex" in model_lower:
            return "google"
        else:
            return "unknown"

    def set_prompts(self, system_prompt: str | None = None, user_prompt: str | None = None):
        """Set the prompts that were sent to LLM"""
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

    def log_response(
        self,
        response: Any,
        parsed_response: dict[str, Any] | None = None,
    ):
        """
        Log the LLM response and calculate metrics

        Args:
            response: Raw LLM response object
            parsed_response: Parsed response (Plan, tool_calls, etc)
        """
        self.response_time = datetime.utcnow()
        self.duration_ms = int((self.response_time - self.request_time).total_seconds() * 1000)
        self.parsed_response = parsed_response

        # Extract token usage from response
        if hasattr(response, "usage"):
            usage = response.usage
            self.input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0))
            self.output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0))
            self.total_tokens = getattr(usage, "total_tokens", self.input_tokens + self.output_tokens)
        elif isinstance(response, dict):
            usage = response.get("usage", {})
            self.input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            self.output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
            self.total_tokens = usage.get("total_tokens", self.input_tokens + self.output_tokens)

        # Extract raw response text
        if hasattr(response, "model_dump"):
            self.raw_response = json.dumps(response.model_dump(), ensure_ascii=False)
        elif isinstance(response, dict):
            self.raw_response = json.dumps(response, ensure_ascii=False)
        else:
            self.raw_response = str(response)

    def log_error(self, error: Exception):
        """Log an error during LLM call"""
        self.response_time = datetime.utcnow()
        self.duration_ms = int((self.response_time - self.request_time).total_seconds() * 1000)
        self.status = "error"
        self.error_message = str(error)
        self.error_details = {
            "error_type": type(error).__name__,
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.log_error(exc_val)

        # Save to database (non-blocking)
        try:
            from .models import LlmCallLogCreate

            log_create = LlmCallLogCreate(
                trace_id=self.trace_id,
                call_type=self.call_type,
                system_prompt=self.system_prompt,
                user_prompt=self.user_prompt,
                context=self.context,
                raw_response=self.raw_response,
                parsed_response=self.parsed_response,
                model_name=self.model_name,
                provider=self.provider,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                total_tokens=self.total_tokens,
                latency_ms=self.duration_ms,
                request_time=self.request_time,
                response_time=self.response_time,
                duration_ms=self.duration_ms,
                status=self.status,
                error_message=self.error_message,
                error_details=self.error_details,
                feature=self.feature,
                ui_endpoint=self.ui_endpoint,
                user_id=self.user_id,
            )

            from .crud import create_llm_call_log
            create_llm_call_log(self.session, log_create)

        except Exception as log_exc:
            logging.warning(f"Failed to log LLM call: {log_exc}")

    def __enter__(self):
        # For synchronous context
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.log_error(exc_val)

        # Save to database (synchronous)
        try:
            from .models import LlmCallLogCreate

            log_create = LlmCallLogCreate(
                trace_id=self.trace_id,
                call_type=self.call_type,
                system_prompt=self.system_prompt,
                user_prompt=self.user_prompt,
                context=self.context,
                raw_response=self.raw_response,
                parsed_response=self.parsed_response,
                model_name=self.model_name,
                provider=self.provider,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                total_tokens=self.total_tokens,
                latency_ms=self.duration_ms,
                request_time=self.request_time,
                response_time=self.response_time,
                duration_ms=self.duration_ms,
                status=self.status,
                error_message=self.error_message,
                error_details=self.error_details,
                feature=self.feature,
                ui_endpoint=self.ui_endpoint,
                user_id=self.user_id,
            )

            from .crud import create_llm_call_log
            create_llm_call_log(self.session, log_create)

        except Exception as log_exc:
            logging.warning(f"Failed to log LLM call: {log_exc}")
