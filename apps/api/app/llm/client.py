from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from uuid import UUID

from app.modules.operation_settings.crud import get_setting_effective_value
from app.llm.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerManager
from app.core.exceptions import CircuitOpenError
from core.config import AppSettings, get_settings
from core.db import get_session_context
from openai import AsyncOpenAI, OpenAI
from sqlmodel import Session


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off", ""}:
            return False
    return default


def _get_runtime_llm_settings() -> dict[str, Any]:
    settings = get_settings()
    defaults = {
        "provider": settings.llm_provider or "openai",
        "base_url": settings.llm_base_url,
        "default_model": settings.llm_default_model or settings.chat_model,
        "fallback_model": settings.llm_fallback_model,
        "timeout_seconds": settings.llm_timeout_seconds or 120,
        "max_retries": settings.llm_max_retries or 2,
        "enable_fallback": settings.llm_enable_fallback,
        "routing_policy": settings.llm_routing_policy or "default",
        "openai_api_key": settings.openai_api_key,
        "internal_api_key": settings.llm_internal_api_key,
    }
    try:
        with get_session_context() as session:
            published_provider = get_setting_effective_value(
                session,
                "llm_provider",
                default_value=defaults["provider"],
                env_value=defaults["provider"],
            )["value"]
            published_base_url = get_setting_effective_value(
                session,
                "llm_base_url",
                default_value=defaults["base_url"] or "",
                env_value=defaults["base_url"] or "",
            )["value"]
            published_default_model = get_setting_effective_value(
                session,
                "llm_default_model",
                default_value=defaults["default_model"],
                env_value=defaults["default_model"],
            )["value"]
            published_fallback_model = get_setting_effective_value(
                session,
                "llm_fallback_model",
                default_value=defaults["fallback_model"] or "",
                env_value=defaults["fallback_model"] or "",
            )["value"]
            published_timeout = get_setting_effective_value(
                session,
                "llm_timeout_seconds",
                default_value=defaults["timeout_seconds"],
                env_value=defaults["timeout_seconds"],
            )["value"]
            published_retries = get_setting_effective_value(
                session,
                "llm_max_retries",
                default_value=defaults["max_retries"],
                env_value=defaults["max_retries"],
            )["value"]
            published_enable_fallback = get_setting_effective_value(
                session,
                "llm_enable_fallback",
                default_value=defaults["enable_fallback"],
                env_value=defaults["enable_fallback"],
            )["value"]
            published_routing_policy = get_setting_effective_value(
                session,
                "llm_routing_policy",
                default_value=defaults["routing_policy"],
                env_value=defaults["routing_policy"],
            )["value"]
    except Exception as exc:
        logging.warning("Failed to load operation settings for LLM runtime: %s", exc)
        return defaults

    return {
        "provider": str(published_provider or defaults["provider"]).strip().lower(),
        "base_url": str(published_base_url).strip() or None,
        "default_model": str(published_default_model or defaults["default_model"]).strip(),
        "fallback_model": str(published_fallback_model).strip() or None,
        "timeout_seconds": int(published_timeout or defaults["timeout_seconds"]),
        "max_retries": int(published_retries or defaults["max_retries"]),
        "enable_fallback": _as_bool(
            published_enable_fallback, defaults["enable_fallback"]
        ),
        "routing_policy": str(published_routing_policy or defaults["routing_policy"]).strip(),
        "openai_api_key": defaults["openai_api_key"],
        "internal_api_key": defaults["internal_api_key"],
    }


def _settings_to_runtime(settings: AppSettings) -> dict[str, Any]:
    return {
        "provider": (settings.llm_provider or "openai").strip().lower(),
        "base_url": settings.llm_base_url,
        "default_model": settings.llm_default_model or settings.chat_model,
        "fallback_model": settings.llm_fallback_model,
        "timeout_seconds": settings.llm_timeout_seconds or 120,
        "max_retries": settings.llm_max_retries or 2,
        "enable_fallback": settings.llm_enable_fallback,
        "routing_policy": settings.llm_routing_policy or "default",
        "openai_api_key": settings.openai_api_key,
        "internal_api_key": settings.llm_internal_api_key,
    }


def is_llm_available(settings: AppSettings | None = None) -> bool:
    runtime = _settings_to_runtime(settings) if settings else _get_runtime_llm_settings()
    provider = runtime["provider"]
    if provider == "openai":
        return bool(runtime["openai_api_key"])
    if provider == "internal":
        return True
    return False


class LlmClient:
    def __init__(self):
        runtime = _get_runtime_llm_settings()
        self.provider = runtime["provider"]
        self.default_model = runtime["default_model"]
        self.fallback_model = runtime["fallback_model"]
        self.enable_fallback = runtime["enable_fallback"]
        self.routing_policy = runtime["routing_policy"]
        timeout_seconds = float(runtime["timeout_seconds"])

        api_key: str | None
        if self.provider == "openai":
            api_key = runtime["openai_api_key"]
            if not api_key:
                logging.warning("OpenAI API key is missing. LLM calls will fail.")
        else:
            # Many internal OpenAI-compatible gateways accept dummy keys.
            api_key = runtime["internal_api_key"] or "internal-llm"

        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_seconds}
        if runtime["base_url"]:
            kwargs["base_url"] = runtime["base_url"]
        kwargs["max_retries"] = int(runtime["max_retries"])

        self.client = OpenAI(**kwargs)
        self.async_client = AsyncOpenAI(**kwargs)

        # Initialize circuit breaker for resilience
        self._circuit_breaker = CircuitBreakerManager.get_or_create(
            "llm_client",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                success_threshold=2,
                expected_exception=Exception,
            ),
        )

    def create_response(
        self,
        input: Union[List[Dict[str, str]], str],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Any:
        """
        Synchronous wrapper for client.responses.create with circuit breaker protection
        """
        # Check circuit breaker first
        if self._circuit_breaker.is_open():
            logging.error(
                "LLM circuit breaker is OPEN - fast-failing request to prevent cascading failures"
            )
            raise CircuitOpenError("llm_client")

        model = model or self.default_model
        logging.debug(
            "LLM create_response: model=%s, input=%s", model, str(input)[:100]
        )
        try:
            response = self.client.responses.create(
                model=model,
                input=input,
                tools=tools,
                stream=False,
                **kwargs,
            )
            # Record success
            self._circuit_breaker.record_success()
            return response
        except Exception as e:
            # Record failure
            self._circuit_breaker.record_failure()

            if self.enable_fallback and self.fallback_model and model != self.fallback_model:
                logging.warning(
                    "LLM primary model failed, retrying with fallback model=%s",
                    self.fallback_model,
                )
                try:
                    response = self.client.responses.create(
                        model=self.fallback_model,
                        input=input,
                        tools=tools,
                        stream=False,
                        **kwargs,
                    )
                    # Record success on fallback
                    self._circuit_breaker.record_success()
                    return response
                except Exception as fallback_error:
                    # Fallback also failed, record another failure
                    self._circuit_breaker.record_failure()
                    logging.error(
                        "LLM fallback model also failed: %s", str(fallback_error)
                    )
                    raise fallback_error from e
            raise

    async def acreate_response(
        self,
        input: Union[List[Dict[str, str]], str],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Any:
        """
        Asynchronous wrapper for client.responses.create with circuit breaker protection
        """
        # Check circuit breaker first
        if self._circuit_breaker.is_open():
            logging.error(
                "LLM circuit breaker is OPEN - fast-failing request to prevent cascading failures"
            )
            raise CircuitOpenError("llm_client")

        model = model or self.default_model
        logging.debug(
            "LLM acreate_response: model=%s, input=%s", model, str(input)[:100]
        )
        try:
            response = await self.async_client.responses.create(
                model=model,
                input=input,
                tools=tools,
                stream=False,
                **kwargs,
            )
            # Record success
            self._circuit_breaker.record_success()
            return response
        except Exception as e:
            # Record failure
            self._circuit_breaker.record_failure()

            if self.enable_fallback and self.fallback_model and model != self.fallback_model:
                logging.warning(
                    "LLM async primary model failed, retrying with fallback model=%s",
                    self.fallback_model,
                )
                try:
                    response = await self.async_client.responses.create(
                        model=self.fallback_model,
                        input=input,
                        tools=tools,
                        stream=False,
                        **kwargs,
                    )
                    # Record success on fallback
                    self._circuit_breaker.record_success()
                    return response
                except Exception as fallback_error:
                    # Fallback also failed, record another failure
                    self._circuit_breaker.record_failure()
                    logging.error(
                        "LLM fallback model also failed: %s", str(fallback_error)
                    )
                    raise fallback_error from e
            raise

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


def reset_llm_client() -> None:
    global _instance
    _instance = None


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
