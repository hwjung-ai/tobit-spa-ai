"""SIM Copilot Service - LLM integration for simulation assistance."""

import logging
from typing import Optional

from core.db import get_session_context

from app.llm.client import LlmCallLogger, get_llm_client, is_llm_available

from .sim_copilot_prompts import SYSTEM_PROMPT, build_user_prompt, parse_llm_response
from .sim_copilot_schemas import (
    SimAnalysisResponse,
    SimCopilotRequest,
    SimCopilotResponse,
    SimDraftResponse,
)

logger = logging.getLogger(__name__)


class SimCopilotService:
    """Service for SIM assistance using LLM."""

    async def generate_response(
        self,
        request: SimCopilotRequest,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SimCopilotResponse:
        """Generate simulation parameters or analyze results."""

        if not is_llm_available():
            logger.warning("LLM not available for SIM copilot")
            return SimCopilotResponse(
                mode="draft",
                explanation="AI service is not available.",
                confidence=0.0,
                suggestions=["Check LLM configuration"],
            )

        # Build context
        context = request.context
        available_services = context.available_services if context else None
        available_strategies = context.available_strategies if context else None

        # Build user prompt
        user_prompt = build_user_prompt(
            current_params=request.current_params,
            prompt=request.prompt,
            latest_results=request.latest_results,
            available_services=available_services,
            available_strategies=available_strategies,
        )

        llm = get_llm_client()

        try:
            async with get_session_context() as session:
                async with LlmCallLogger(
                    session=session,
                    call_type="sim_copilot",
                    model_name=llm.default_model,
                    trace_id=trace_id,
                    feature="sim_workspace",
                    user_id=user_id,
                ) as log:
                    log.set_prompts(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=user_prompt
                    )

                    response = await llm.acreate_response(
                        input=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3,
                    )

                    output_text = llm.get_output_text(response)
                    log.log_response(response)

            parsed = parse_llm_response(output_text)

            # Build response based on mode
            sim_response = SimCopilotResponse(
                mode=parsed.get("mode", "draft"),
                explanation=parsed.get("explanation", ""),
                confidence=min(1.0, max(0.0, parsed.get("confidence", 0.7))),
                suggestions=parsed.get("suggestions", []),
            )

            if parsed.get("mode") == "draft" and parsed.get("draft"):
                draft_data = parsed["draft"]
                sim_response.draft = SimDraftResponse(
                    question=draft_data.get("question", ""),
                    scenario_type=draft_data.get("scenario_type", "what_if"),
                    strategy=draft_data.get("strategy", "rule"),
                    horizon=draft_data.get("horizon", "7d"),
                    service=draft_data.get("service", ""),
                    assumptions=draft_data.get("assumptions", {}),
                )
            elif parsed.get("mode") == "analyze" and parsed.get("analysis"):
                analysis_data = parsed["analysis"]
                sim_response.analysis = SimAnalysisResponse(
                    summary=analysis_data.get("summary", ""),
                    key_findings=analysis_data.get("key_findings", []),
                    anomalies=analysis_data.get("anomalies", []),
                    comparison_with_baseline=analysis_data.get(
                        "comparison_with_baseline", ""
                    ),
                    recommendations=analysis_data.get("recommendations", []),
                    confidence_assessment=analysis_data.get(
                        "confidence_assessment", "medium"
                    ),
                )

            return sim_response

        except Exception as e:
            logger.error(f"SIM copilot error: {e}", exc_info=True)
            return SimCopilotResponse(
                mode="draft",
                explanation=f"Error: {str(e)}",
                confidence=0.0,
                suggestions=["Please try again"],
            )


# Global instance
_sim_copilot_service: Optional[SimCopilotService] = None


def get_sim_copilot_service() -> SimCopilotService:
    """Get or create SIM copilot service instance."""
    global _sim_copilot_service
    if _sim_copilot_service is None:
        _sim_copilot_service = SimCopilotService()
    return _sim_copilot_service
