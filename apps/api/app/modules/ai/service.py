"""Screen Copilot Service - LLM integration for screen editing."""

import logging
from typing import Any

from core.db import get_session_context

from app.llm.client import LlmCallLogger, get_llm_client, is_llm_available

from .prompts import SYSTEM_PROMPT, build_user_prompt, parse_llm_response
from .schemas import JsonPatchOperation, ScreenCopilotRequest, ScreenCopilotResponse

logger = logging.getLogger(__name__)


class ScreenCopilotService:
    """Service for generating screen modifications using LLM."""
    
    async def generate_patch(
        self,
        request: ScreenCopilotRequest,
        trace_id: str | None = None,
        user_id: str | None = None,
    ) -> ScreenCopilotResponse:
        """Generate JSON Patch operations for screen modification."""
        
        # Check LLM availability
        if not is_llm_available():
            logger.warning("LLM not available for screen copilot")
            return ScreenCopilotResponse(
                patch=[],
                explanation="AI service is not available. Please check LLM configuration.",
                confidence=0.0,
                suggestions=["Check if OPENAI_API_KEY is set"]
            )
        
        # Build context
        available_handlers = request.context.available_handlers if request.context else []
        state_paths = request.context.state_paths if request.context else []
        
        # Build user prompt
        user_prompt = build_user_prompt(
            screen_schema=request.screen_schema,
            prompt=request.prompt,
            selected_component=request.selected_component,
            available_handlers=available_handlers,
            state_paths=state_paths,
        )
        
        # Get LLM client
        llm = get_llm_client()
        
        try:
            # Call LLM with logging
            async with get_session_context() as session:
                async with LlmCallLogger(
                    session=session,
                    call_type="screen_copilot",
                    model_name=llm.default_model,
                    trace_id=trace_id,
                    feature="screen_editor",
                    user_id=user_id,
                ) as log:
                    log.set_prompts(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=user_prompt
                    )
                    
                    # Make LLM call
                    response = await llm.acreate_response(
                        input=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,  # Lower temperature for more deterministic output
                    )
                    
                    # Extract response text
                    output_text = llm.get_output_text(response)
                    log.log_response(response)
            
            # Parse response
            parsed = parse_llm_response(output_text)
            
            # Build response
            patch_ops = []
            for op in parsed.get("patch", []):
                try:
                    patch_ops.append(JsonPatchOperation(**op))
                except Exception as e:
                    logger.warning(f"Invalid patch operation: {op}, error: {e}")
            
            return ScreenCopilotResponse(
                patch=patch_ops,
                explanation=parsed.get("explanation", ""),
                confidence=min(1.0, max(0.0, parsed.get("confidence", 0.5))),
                suggestions=parsed.get("suggestions", [])
            )
            
        except Exception as e:
            logger.error(f"Screen copilot LLM call failed: {e}", exc_info=True)
            return ScreenCopilotResponse(
                patch=[],
                explanation=f"AI service error: {str(e)}",
                confidence=0.0,
                suggestions=["Try again later", "Simplify your request"]
            )
    
    def validate_patch(self, patch: list[JsonPatchOperation], schema: dict[str, Any]) -> list[str]:
        """Validate patch operations against schema. Returns list of errors."""
        
        errors = []
        
        for i, op in enumerate(patch):
            # Check required fields
            if not op.op:
                errors.append(f"Operation {i}: missing 'op' field")
            elif op.op not in ["add", "remove", "replace", "move", "copy", "test"]:
                errors.append(f"Operation {i}: invalid op '{op.op}'")
            
            if not op.path:
                errors.append(f"Operation {i}: missing 'path' field")
            
            # Check value requirement
            if op.op in ["add", "replace", "test"] and op.value is None:
                errors.append(f"Operation {i}: op '{op.op}' requires 'value'")
            
            # Check from requirement
            if op.op in ["move", "copy"] and not op.from_path:
                errors.append(f"Operation {i}: op '{op.op}' requires 'from'")
        
        return errors


# Singleton instance
_service: ScreenCopilotService | None = None


def get_screen_copilot_service() -> ScreenCopilotService:
    """Get the screen copilot service instance."""
    global _service
    if _service is None:
        _service = ScreenCopilotService()
    return _service