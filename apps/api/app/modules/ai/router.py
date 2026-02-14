"""Screen Copilot API Router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.deps import get_current_user
from core.db import get_session
from core.response import ResponseEnvelope
from models.user import TbUser

from .schemas import ScreenCopilotRequest, ScreenCopilotResponse
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
            trace_id=None,  # Could extract from request context
            user_id=str(current_user.user_id) if current_user else None,
        )
        
        # Validate patch
        if response.patch:
            errors = service.validate_patch(response.patch, request.screen_schema)
            if errors:
                logger.warning(f"Patch validation errors: {errors}")
                # Still return the patch but with warnings
                response.suggestions = response.suggestions + [f"Warning: {e}" for e in errors]
        
        return ResponseEnvelope.success(
            data=response.model_dump(),
            message=response.explanation or "Patch generated successfully"
        )
        
    except Exception as e:
        logger.error(f"Screen copilot error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to generate patch: {str(e)}",
            error_code="AI_SERVICE_ERROR"
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
        service = get_screen_copilot_service()
        
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
                "suggestions": suggestions
            }
        )
        
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Validation failed: {str(e)}",
            error_code="VALIDATION_ERROR"
        )