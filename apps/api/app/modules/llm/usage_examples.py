"""
LLM Call Log Usage Examples

This document shows how to use LlmCallLogger in different scenarios.
"""

from app.llm.client import LlmCallLogger, get_llm_client


# =============================================================================
# Example 1: Basic Usage in Planner
# =============================================================================
async def example_planner_usage(session, trace_id, question: str):
    """Example: Logging in planner_llm.py"""
    llm = get_llm_client()

    async with LlmCallLogger(
        session=session,
        call_type="planner",
        model_name="gpt-4o",
        trace_id=trace_id,
        feature="ops",
        ui_endpoint="/ops/ask",
    ) as logger:
        # Build messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ]

        logger.set_prompts(
            system_prompt=messages[0]["content"],
            user_prompt=messages[1]["content"]
        )

        # Call LLM
        response = await llm.acreate_response(
            model="gpt-4o",
            input=messages
        )

        # Parse response
        parsed_plan = {"intent": "lookup", "ci_keywords": ["server-01"]}

        logger.log_response(
            response=response,
            parsed_response={"plan": parsed_plan}
        )

    # Log is automatically saved when exiting context


# =============================================================================
# Example 2: Output Parser Usage
# =============================================================================
async def example_output_parser_usage(session, trace_id, text: str):
    """Example: Logging output parser calls"""
    llm = get_llm_client()

    async with LlmCallLogger(
        session=session,
        call_type="output_parser",
        model_name="gpt-4o-mini",
        trace_id=trace_id,
        feature="ops",
    ) as logger:
        messages = [
            {"role": "system", "content": "Parse the user query"},
            {"role": "user", "content": text}
        ]

        logger.set_prompts(
            system_prompt=messages[0]["content"],
            user_prompt=messages[1]["content"]
        )

        response = await llm.acreate_response(
            model="gpt-4o-mini",
            input=messages,
            tools=[{"name": "create_plan", "parameters": {...}}]
        )

        logger.log_response(
            response=response,
            parsed_response={"plan": {...}}
        )


# =============================================================================
# Example 3: Tool Call Usage
# =============================================================================
async def example_tool_call_usage(session, trace_id, tool_name: str, params: dict):
    """Example: Logging tool execution calls"""
    llm = get_llm_client()

    async with LlmCallLogger(
        session=session,
        call_type="tool",
        model_name="gpt-4o",
        trace_id=trace_id,
        feature="ops",
        context={"tool_name": tool_name, "params": params},
    ) as logger:
        messages = [
            {"role": "system", "content": f"Execute tool {tool_name}"},
            {"role": "user", "content": f"Parameters: {params}"}
        ]

        logger.set_prompts(
            system_prompt=messages[0]["content"],
            user_prompt=messages[1]["content"]
        )

        response = await llm.acreate_response(
            model="gpt-4o",
            input=messages
        )

        logger.log_response(
            response=response,
            parsed_response={"tool_result": {...}}
        )


# =============================================================================
# Example 4: Error Handling
# =============================================================================
async def example_error_handling(session, trace_id, question: str):
    """Example: Logging errors"""
    llm = get_llm_client()

    try:
        async with LlmCallLogger(
            session=session,
            call_type="planner",
            model_name="gpt-4o",
            trace_id=trace_id,
            feature="ops",
        ) as logger:
            logger.set_prompts(
                system_prompt="...",
                user_prompt=question
            )

            response = await llm.acreate_response(...)
            logger.log_response(response)
    except Exception:
        # Error is automatically logged by __aexit__
        raise


# =============================================================================
# Example 5: Actual Integration in planner_llm.py
# =============================================================================
"""
In planner_llm.py, modify _call_output_parser_llm() function:

def _call_output_parser_llm(...):
    from app.llm.client import LlmCallLogger
    from core.logging import get_logger
    from core.db import get_session_context

    logger = get_logger(__name__)

    try:
        messages = _build_output_parser_messages(...)
        llm = get_llm_client()
        start = perf_counter()

        # Use LlmCallLogger
        with get_session_context() as session:
            async with LlmCallLogger(
                session=session,
                call_type="output_parser",
                model_name=OUTPUT_PARSER_MODEL,
                trace_id=None,  # or pass from context
                feature="ops",
                ui_endpoint="/ops/ask",
            ) as call_logger:
                call_logger.set_prompts(
                    system_prompt=messages[0]["content"],
                    user_prompt=messages[1]["content"]
                )

                response = llm.create_response(
                    model=OUTPUT_PARSER_MODEL,
                    input=messages,
                    tools=tools,
                    temperature=0,
                )

                # Extract and log result
                tool_call = extract_tool_call_from_response(response)
                if tool_call:
                    payload = tool_call.get("input", {})
                    elapsed = int((perf_counter() - start) * 1000)

                    logger.info("ci.planner.llm_call", extra={
                        "model": OUTPUT_PARSER_MODEL,
                        "elapsed_ms": elapsed,
                        "method": "function_calling",
                        "status": "ok",
                    })

                    call_logger.log_response(response, parsed_response={"payload": payload})
                    return payload

                # Fallback handling...
                call_logger.log_response(response, parsed_response={"fallback": True})
                # ... rest of code

    except Exception as exc:
        logger.warning("ci.planner.llm_fallback", extra={"error": str(exc)})
        return None
"""
