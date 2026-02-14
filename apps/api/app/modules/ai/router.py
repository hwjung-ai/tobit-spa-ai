"""AI Copilot API Router - Screen and API Manager copilots."""

import logging
import uuid as _uuid

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.auth.models import TbUser

from .api_copilot_schemas import ApiCopilotRequest
from .api_copilot_service import get_api_copilot_service
from .schemas import ScreenCopilotRequest
from .service import get_screen_copilot_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/screen-copilot", response_model=ResponseEnvelope)
async def generate_screen_patch(
    request: ScreenCopilotRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Generate JSON Patch operations for screen modification using AI.

    Takes a screen schema and natural language prompt, returns JSON Patch
    operations that can be applied to modify the screen.

    Requires authentication.
    """
    try:
        # Get service
        service = get_screen_copilot_service()

        # Generate patch
        response = await service.generate_patch(
            request=request,
            trace_id=str(_uuid.uuid4()),
            user_id=str(current_user.id) if current_user else None,
        )

        # Validate patch
        if response.patch:
            errors = service.validate_patch(response.patch, request.screen_schema)
            if errors:
                logger.warning(f"Patch validation errors: {errors}")
                # Still return the patch but with warnings
                response.suggestions = response.suggestions + [
                    f"Warning: {e}" for e in errors
                ]

        return ResponseEnvelope.success(
            data=response.model_dump(),
            message=response.explanation or "Patch generated successfully",
        )

    except Exception as e:
        logger.error(f"Screen copilot error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to generate patch: {str(e)}", error_code="AI_SERVICE_ERROR"
        )


@router.post("/screen-copilot/validate", response_model=ResponseEnvelope)
async def validate_screen_patch(
    request: ScreenCopilotRequest,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Validate a screen schema without generating patches.

    Returns validation result and suggestions for improvement.
    """
    try:
        # Basic validation
        schema = request.screen_schema
        errors = []
        suggestions = []

        # Check required fields
        if not schema.get("screen_id"):
            errors.append("Missing required field: screen_id")

        if not schema.get("components"):
            errors.append("Missing or empty components array")

        if not schema.get("layout"):
            errors.append("Missing required field: layout")

        # Check component IDs
        component_ids = set()
        for i, comp in enumerate(schema.get("components", [])):
            comp_id = comp.get("id")
            if not comp_id:
                errors.append(f"Component at index {i} missing id")
            elif comp_id in component_ids:
                errors.append(f"Duplicate component id: {comp_id}")
            else:
                component_ids.add(comp_id)

        # Generate suggestions
        if not errors:
            suggestions.append("Schema looks valid!")
        else:
            suggestions.append("Fix the validation errors above")

        return ResponseEnvelope.success(
            data={
                "valid": len(errors) == 0,
                "errors": errors,
                "suggestions": suggestions,
            }
        )

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Validation failed: {str(e)}", error_code="VALIDATION_ERROR"
        )


@router.post("/api-copilot", response_model=ResponseEnvelope)
async def generate_api(
    request: ApiCopilotRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Generate or improve an API using AI.

    Takes a natural language prompt and optionally an existing API draft,
    returns a complete API definition with HTTP spec, examples, and suggestions.

    Requires authentication.
    """
    try:
        # Get service
        service = get_api_copilot_service()

        # Generate API
        response = await service.generate_api(
            request=request,
            trace_id=str(_uuid.uuid4()),
            user_id=str(current_user.id) if current_user else None,
        )

        # Validate draft
        if response.api_draft:
            errors, warnings = service.validate_api_draft(response.api_draft)
            if errors:
                logger.warning(f"API draft validation errors: {errors}")
                response.suggestions = response.suggestions + [
                    f"Error: {e}" for e in errors
                ]
            if warnings:
                response.suggestions = response.suggestions + [
                    f"Warning: {w}" for w in warnings
                ]

        return ResponseEnvelope.success(
            data=response.model_dump(),
            message=response.explanation or "API generated successfully",
        )

    except Exception as e:
        logger.error(f"API copilot error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to generate API: {str(e)}", error_code="AI_SERVICE_ERROR"
        )


@router.post("/api-copilot/validate", response_model=ResponseEnvelope)
async def validate_api_draft(
    api_draft: dict,
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """
    Validate an API draft without generating modifications.

    Returns validation result and suggestions for improvement.
    """
    try:
        service = get_api_copilot_service()

        # Validate draft
        errors, warnings = service.validate_api_draft(api_draft)

        return ResponseEnvelope.success(
            data={
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "suggestions": [
                    "Fix these errors" if errors else "API draft looks good!"
                ],
            }
        )

    except Exception as e:
        logger.error(f"API validation error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Validation failed: {str(e)}", error_code="VALIDATION_ERROR"
        )
