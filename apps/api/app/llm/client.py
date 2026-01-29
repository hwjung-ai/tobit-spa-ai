from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from core.config import get_settings
from openai import AsyncOpenAI, OpenAI


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
