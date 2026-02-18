"""CEP Copilot Service - LLM integration for CEP rule generation."""

import logging
from typing import Any, Optional

from core.db import get_session_context

from app.llm.client import LlmCallLogger, get_llm_client, is_llm_available

from .cep_copilot_prompts import SYSTEM_PROMPT, build_user_prompt, parse_llm_response
from .cep_copilot_schemas import CepCopilotRequest, CepCopilotResponse

logger = logging.getLogger(__name__)


class CepCopilotService:
    """Service for generating CEP rules using LLM."""

    async def generate_rule(
        self,
        request: CepCopilotRequest,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> CepCopilotResponse:
        """Generate or modify a CEP rule based on user prompt."""

        if not is_llm_available():
            logger.warning("LLM not available for CEP copilot")
            return CepCopilotResponse(
                rule_draft={},
                explanation="AI service is not available. Please check LLM configuration.",
                confidence=0.0,
                suggestions=["Check if OPENAI_API_KEY or Claude API key is set"],
            )

        # Build context
        context = request.context
        available_trigger_types = context.available_trigger_types if context else None
        available_actions = context.available_actions if context else None

        # Build user prompt
        user_prompt = build_user_prompt(
            rule_spec=request.rule_spec,
            prompt=request.prompt,
            selected_field=request.selected_field,
            available_trigger_types=available_trigger_types,
            available_actions=available_actions,
        )

        llm = get_llm_client()

        try:
            async with get_session_context() as session:
                async with LlmCallLogger(
                    session=session,
                    call_type="cep_copilot",
                    model_name=llm.default_model,
                    trace_id=trace_id,
                    feature="cep_builder",
                    user_id=user_id,
                ) as log:
                    log.set_prompts(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

                    response = await llm.acreate_response(
                        input=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                    )

                    output_text = llm.get_output_text(response)
                    log.log_response(response)

            parsed = parse_llm_response(output_text)

            return CepCopilotResponse(
                rule_draft=parsed.get("rule_draft", {}),
                patch=parsed.get("patch", []),
                explanation=parsed.get("explanation", "CEP rule generated"),
                confidence=min(1.0, max(0.0, parsed.get("confidence", 0.7))),
                suggestions=parsed.get("suggestions", []),
                warnings=parsed.get("warnings", []),
            )

        except Exception as e:
            logger.error(f"CEP copilot error: {e}", exc_info=True)
            return CepCopilotResponse(
                rule_draft={},
                explanation=f"Error generating CEP rule: {str(e)}",
                confidence=0.0,
                suggestions=["Please try again with a different request"],
            )

    def validate_rule_draft(self, rule_draft: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Validate a CEP rule draft and return errors and warnings."""
        errors = []
        warnings = []

        if not rule_draft.get("rule_name"):
            errors.append("Rule name is required")

        if not rule_draft.get("trigger_type"):
            errors.append("Trigger type is required")

        trigger_spec = rule_draft.get("trigger_spec", {})
        if rule_draft.get("trigger_type") == "metric":
            if not trigger_spec.get("metric_name"):
                errors.append("Metric name is required for metric triggers")
            if trigger_spec.get("threshold") is None:
                errors.append("Threshold is required for metric triggers")

        actions = rule_draft.get("actions", [])
        if not actions:
            warnings.append("No actions defined - rule will not trigger any response")

        return errors, warnings


# Global instance
_cep_copilot_service: Optional[CepCopilotService] = None


def get_cep_copilot_service() -> CepCopilotService:
    """Get or create CEP copilot service instance."""
    global _cep_copilot_service
    if _cep_copilot_service is None:
        _cep_copilot_service = CepCopilotService()
    return _cep_copilot_service
