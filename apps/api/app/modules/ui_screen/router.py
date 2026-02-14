"""
Screen Editor API Router
Provides REST API endpoints for screen management.
"""

from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from schemas import ResponseEnvelope
from sqlmodel import Session

from core.auth import get_current_user
from core.db import get_session
from app.modules.auth.models import TbUser

from .models import (
    ScreenCreateRequest,
    ScreenUpdateRequest,
    ScreenPublishRequest,
    ScreenRollbackRequest,
    ScreenResponse,
    ScreenListResponse,
    ScreenVersionResponse,
)
from .screen_router import (
    create_screen,
    get_screen,
    list_screens,
    update_screen,
    publish_screen,
    unpublish_screen,
    rollback_screen,
    delete_screen,
    get_screen_versions,
    get_screen_version,
    ScreenNotFoundError,
    ScreenVersionConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screens", tags=["screen-editor"])


def get_client_info(request: Request) -> tuple:
    """Extract client IP and user agent from request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    return ip_address, user_agent


@router.post("", response_model=ResponseEnvelope)
async def api_create_screen(
    request_body: ScreenCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Create a new screen."""
    try:
        ip_address, user_agent = get_client_info(request)
        screen = create_screen(
            session=session,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            request=request_body,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ResponseEnvelope.success(
            data=ScreenResponse(**screen.model_dump()),
            message=f"Screen '{screen.screen_name}' created successfully"
        )
    except Exception as e:
        logger.error(f"Failed to create screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to create screen: {str(e)}",
            error_code="CREATE_ERROR"
        )


@router.get("", response_model=ResponseEnvelope)
async def api_list_screens(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    screen_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_published: Optional[bool] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """List screens with filtering and pagination."""
    try:
        tag_list = tags.split(",") if tags else None
        result = list_screens(
            session=session,
            tenant_id=str(current_user.tenant_id),
            page=page,
            page_size=page_size,
            search=search,
            screen_type=screen_type,
            is_active=is_active,
            is_published=is_published,
            tags=tag_list,
        )
        return ResponseEnvelope.success(data=result.model_dump())
    except Exception as e:
        logger.error(f"Failed to list screens: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to list screens: {str(e)}",
            error_code="LIST_ERROR"
        )


@router.get("/{screen_id}", response_model=ResponseEnvelope)
async def api_get_screen(
    screen_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Get a screen by ID."""
    try:
        screen = get_screen(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
        )
        return ResponseEnvelope.success(data=ScreenResponse(**screen.model_dump()))
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to get screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to get screen: {str(e)}",
            error_code="GET_ERROR"
        )


@router.put("/{screen_id}", response_model=ResponseEnvelope)
async def api_update_screen(
    screen_id: str,
    request_body: ScreenUpdateRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Update an existing screen."""
    try:
        ip_address, user_agent = get_client_info(request)
        screen = update_screen(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            request=request_body,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ResponseEnvelope.success(
            data=ScreenResponse(**screen.model_dump()),
            message=f"Screen updated to version {screen.version}"
        )
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to update screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to update screen: {str(e)}",
            error_code="UPDATE_ERROR"
        )


@router.post("/{screen_id}/publish", response_model=ResponseEnvelope)
async def api_publish_screen(
    screen_id: str,
    request_body: ScreenPublishRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Publish a screen."""
    try:
        ip_address, user_agent = get_client_info(request)
        screen = publish_screen(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            change_summary=request_body.change_summary,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ResponseEnvelope.success(
            data=ScreenResponse(**screen.model_dump()),
            message=f"Screen '{screen.screen_name}' published successfully"
        )
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to publish screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to publish screen: {str(e)}",
            error_code="PUBLISH_ERROR"
        )


@router.post("/{screen_id}/unpublish", response_model=ResponseEnvelope)
async def api_unpublish_screen(
    screen_id: str,
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Unpublish a screen."""
    try:
        ip_address, user_agent = get_client_info(request)
        screen = unpublish_screen(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ResponseEnvelope.success(
            data=ScreenResponse(**screen.model_dump()),
            message=f"Screen '{screen.screen_name}' unpublished"
        )
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to unpublish screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to unpublish screen: {str(e)}",
            error_code="UNPUBLISH_ERROR"
        )


@router.post("/{screen_id}/rollback", response_model=ResponseEnvelope)
async def api_rollback_screen(
    screen_id: str,
    request_body: ScreenRollbackRequest,
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Rollback screen to a specific version."""
    try:
        ip_address, user_agent = get_client_info(request)
        screen = rollback_screen(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            target_version=request_body.target_version,
            reason=request_body.reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ResponseEnvelope.success(
            data=ScreenResponse(**screen.model_dump()),
            message=f"Screen rolled back to version {request_body.target_version}"
        )
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except ScreenVersionConflictError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="VERSION_CONFLICT"
        )
    except Exception as e:
        logger.error(f"Failed to rollback screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to rollback screen: {str(e)}",
            error_code="ROLLBACK_ERROR"
        )


@router.delete("/{screen_id}", response_model=ResponseEnvelope)
async def api_delete_screen(
    screen_id: str,
    request: Request,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Delete a screen (soft delete)."""
    try:
        ip_address, user_agent = get_client_info(request)
        delete_screen(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
            user_id=str(current_user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ResponseEnvelope.success(
            data={"screen_id": screen_id},
            message="Screen deleted successfully"
        )
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to delete screen: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to delete screen: {str(e)}",
            error_code="DELETE_ERROR"
        )


@router.get("/{screen_id}/versions", response_model=ResponseEnvelope)
async def api_get_screen_versions(
    screen_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Get version history for a screen."""
    try:
        versions = get_screen_versions(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
        )
        return ResponseEnvelope.success(
            data=[v.model_dump() for v in versions]
        )
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to get screen versions: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to get screen versions: {str(e)}",
            error_code="VERSION_ERROR"
        )


@router.get("/{screen_id}/versions/{version}", response_model=ResponseEnvelope)
async def api_get_screen_version(
    screen_id: str,
    version: int,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
) -> ResponseEnvelope:
    """Get a specific version of a screen."""
    try:
        version_obj = get_screen_version(
            session=session,
            screen_id=screen_id,
            tenant_id=str(current_user.tenant_id),
            version=version,
        )
        return ResponseEnvelope.success(data=version_obj.model_dump())
    except ScreenNotFoundError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="NOT_FOUND"
        )
    except ScreenVersionConflictError as e:
        return ResponseEnvelope.error(
            message=str(e),
            error_code="VERSION_NOT_FOUND"
        )
    except Exception as e:
        logger.error(f"Failed to get screen version: {e}", exc_info=True)
        return ResponseEnvelope.error(
            message=f"Failed to get screen version: {str(e)}",
            error_code="VERSION_ERROR"
        )
