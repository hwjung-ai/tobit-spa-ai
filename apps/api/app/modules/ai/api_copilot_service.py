"""API Manager Copilot Service - LLM integration for API generation and modification."""

import json
import logging
from typing import Any, Optional

from app.llm.client import get_llm_client, is_llm_available
from app.llm.client import LlmCallLogger
from core.db import get_session_context

from .api_copilot_prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    parse_llm_response,
    generate_example_request,
    generate_example_response,
)
from .api_copilot_schemas import (
    ApiCopilotRequest,
    ApiCopilotResponse,
    HttpSpecGeneration,
)

logger = logging.getLogger(__name__)


class ApiCopilotService:
    """Service for generating and improving APIs using LLM."""

    async def generate_api(
        self,
        request: ApiCopilotRequest,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ApiCopilotResponse:
        """Generate or improve an API based on user prompt."""

        # Check LLM availability
        if not is_llm_available():
            logger.warning("LLM not available for API copilot")
            return ApiCopilotResponse(
                api_draft={},
                explanation="AI service is not available. Please check LLM configuration.",
                confidence=0.0,
                suggestions=["Check if OPENAI_API_KEY or Claude API key is set"],
            )

        # Build user prompt
        context = request.context or None
        user_prompt = build_user_prompt(
            prompt=request.prompt,
            logic_type=request.logic_type,
            api_draft=request.api_draft,
            available_databases=(
                context.available_databases if context else None
            ),
            common_headers=context.common_headers if context else None,
        )

        # Get LLM client
        llm = get_llm_client()

        try:
            # Call LLM with logging
            async with get_session_context() as session:
                async with LlmCallLogger(
                    session=session,
                    call_type="api_copilot",
                    model_name=llm.default_model,
                    trace_id=trace_id,
                    feature="api_manager",
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

            # Validate api_draft
            api_draft = parsed.get("api_draft", {})
            if not api_draft.get("api_name"):
                api_draft["api_name"] = "Untitled API"

            if not api_draft.get("endpoint"):
                api_draft["endpoint"] = "/api/endpoint"

            if not api_draft.get("method"):
                api_draft["method"] = "GET"

            if not api_draft.get("logic_type"):
                api_draft["logic_type"] = request.logic_type or "sql"

            if not api_draft.get("logic_body"):
                api_draft["logic_body"] = ""

            # Generate HTTP spec if it's an HTTP API
            http_spec = None
            if api_draft.get("logic_type") == "http":
                http_spec = self._generate_http_spec(api_draft, parsed)

            # Generate fallback examples if not provided
            request_example = parsed.get("request_example")
            response_example = parsed.get("response_example")

            if not request_example:
                request_example = generate_example_request(api_draft)

            if not response_example:
                response_example = generate_example_response(api_draft)

            # Build response
            return ApiCopilotResponse(
                api_draft=api_draft,
                explanation=parsed.get("explanation", "API generated successfully"),
                confidence=min(1.0, max(0.0, parsed.get("confidence", 0.7))),
                suggestions=parsed.get("suggestions", []),
                http_spec=http_spec,
                request_example=request_example,
                response_example=response_example,
            )

        except Exception as e:
            logger.error(f"API copilot error: {e}", exc_info=True)
            return ApiCopilotResponse(
                api_draft={},
                explanation=f"Error generating API: {str(e)}",
                confidence=0.0,
                suggestions=["Please try again with a different request"],
            )

    def _generate_http_spec(
        self,
        api_draft: dict[str, Any],
        parsed_response: dict[str, Any],
    ) -> Optional[HttpSpecGeneration]:
        """Generate HTTP spec from api_draft and parsed response."""

        try:
            logic_body = api_draft.get("logic_body", "{}")

            # Try to parse as JSON
            if isinstance(logic_body, str):
                try:
                    http_spec_dict = json.loads(logic_body)
                except (json.JSONDecodeError, ValueError):
                    http_spec_dict = {}
            else:
                http_spec_dict = logic_body

            # Build HTTP spec
            http_spec_dict.setdefault("method", "GET")
            http_spec_dict.setdefault("headers", {})
            http_spec_dict.setdefault("params", {})

            return HttpSpecGeneration(
                url=http_spec_dict.get("url", "https://api.example.com/endpoint"),
                method=http_spec_dict.get("method", "GET"),
                headers=http_spec_dict.get("headers", {}),
                body=http_spec_dict.get("body"),
                params=http_spec_dict.get("params", {}),
                examples=parsed_response.get("http_spec", {}).get("examples", []),
            )

        except Exception as e:
            logger.warning(f"Failed to generate HTTP spec: {e}")
            return None

    def validate_api_draft(
        self,
        api_draft: dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        """Validate an API draft and return errors and warnings."""

        errors = []
        warnings = []

        # Check required fields
        if not api_draft.get("api_name"):
            errors.append("API name is required")

        if not api_draft.get("endpoint"):
            errors.append("Endpoint is required")

        if not api_draft.get("method"):
            errors.append("HTTP method is required")

        if not api_draft.get("logic_type"):
            errors.append("Logic type is required")

        # Logic-specific validation
        logic_type = api_draft.get("logic_type")

        if logic_type == "sql":
            logic_body = api_draft.get("logic_body", "").strip()
            if not logic_body:
                errors.append("SQL query is required")
            elif not logic_body.upper().startswith(("SELECT", "WITH")):
                errors.append("SQL query must start with SELECT or WITH")

        elif logic_type == "http":
            try:
                logic_body = api_draft.get("logic_body", "{}")
                if isinstance(logic_body, str):
                    http_spec = json.loads(logic_body)
                else:
                    http_spec = logic_body

                if not http_spec.get("url"):
                    errors.append("HTTP URL is required")
            except (json.JSONDecodeError, ValueError):
                errors.append("HTTP logic body must be valid JSON")

        # Warnings
        param_schema = api_draft.get("param_schema", {})
        if not param_schema:
            warnings.append("No parameters defined - consider adding parameters for flexibility")

        return errors, warnings


# Global instance
_api_copilot_service: Optional[ApiCopilotService] = None


def get_api_copilot_service() -> ApiCopilotService:
    """Get or create API copilot service instance."""

    global _api_copilot_service

    if _api_copilot_service is None:
        _api_copilot_service = ApiCopilotService()

    return _api_copilot_service
