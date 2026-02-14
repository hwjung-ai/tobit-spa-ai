"""API Manager export endpoints for exporting APIs to Tools and managing linkage."""

import logging
from datetime import datetime

from core.auth import get_current_user
from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException
from models.api_definition import ApiDefinition
from pydantic import BaseModel, Field
from schemas import ResponseEnvelope
from sqlmodel import Session

from app.modules.auth.models import TbUser

from ..crud import _parse_api_uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api-manager", tags=["api-manager"])


class ExportApiToToolsRequest(BaseModel):
    """Request to export API to Tools"""

    export: bool = Field(default=True, description="Mark as ready for export")


@router.get("/apis/{api_id}/export-options", response_model=ResponseEnvelope)
async def get_api_export_options(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Get export options for an API.

    This endpoint allows checking if an API can be exported to Tools
    and provides information about existing Tool linkage.
    """
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        # Check if already linked to a tool
        linked_tool = None
        if api.linked_to_tool_id:
            linked_tool = {
                "tool_id": str(api.linked_to_tool_id),
                "tool_name": api.linked_to_tool_name,
                "linked_at": api.linked_at.isoformat() if api.linked_at else None
            }

        return ResponseEnvelope.success(data={
            "api_id": str(api.id),
            "api_name": api.name,
            "can_export_to_tools": True,
            "linked_tool": linked_tool,
            "available_export_targets": ["tools"],
            "export_url": f"/asset-registry/tools/import-from-api-manager/{api_id}"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get export options failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/apis/{api_id}/export-to-tools", response_model=ResponseEnvelope)
async def export_api_to_tools(
    api_id: str,
    request: ExportApiToToolsRequest,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Export API to Tools by marking it as ready for import.

    This endpoint only sets the export flag. Actual Tool creation happens
    in Tools module via the import endpoint.

    After calling this endpoint, users should navigate to Tools section
    to complete the import process.
    """
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        if not request.export:
            # Cancel export - clear export flag
            api.linked_to_tool_name = None
            api.linked_at = None
            session.add(api)
            session.commit()

            return ResponseEnvelope.success(data={
                "api_id": str(api.id),
                "api_name": api.name,
                "export_status": "cancelled",
                "message": "API export cancelled. No longer available for import in Tools."
            })

        if api.linked_to_tool_id:
            # Already imported - return link info
            return ResponseEnvelope.success(data={
                "api_id": str(api.id),
                "api_name": api.name,
                "export_status": "already_imported",
                "message": f"API already imported as tool: {api.linked_to_tool_name}",
                "linked_tool": {
                    "tool_id": str(api.linked_to_tool_id),
                    "tool_name": api.linked_to_tool_name,
                    "linked_at": api.linked_at.isoformat() if api.linked_at else None
                }
            })

        # Set export flag (actual tool_id will be set during import)
        api.linked_to_tool_name = f"Imported from API: {api.name}"
        api.linked_at = datetime.utcnow()
        session.add(api)
        session.commit()

        return ResponseEnvelope.success(data={
            "api_id": str(api.id),
            "api_name": api.name,
            "export_status": "ready",
            "message": "API ready for export. Complete import in Tools section.",
            "import_url": f"/asset-registry/tools/import-from-api-manager/{api_id}"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export to tools failed: {str(e)}")
        raise HTTPException(500, str(e))


@router.post("/apis/{api_id}/unlink-from-tool", response_model=ResponseEnvelope)
async def unlink_api_from_tool(
    api_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Unlink API from Tool (remove linkage).

    This removes the connection between API and Tool.
    Both systems become independent again.
    """
    try:
        api = session.get(ApiDefinition, _parse_api_uuid(api_id))
        if not api or api.deleted_at:
            raise HTTPException(status_code=404, detail="API not found")

        if not api.linked_to_tool_id:
            raise HTTPException(
                status_code=400,
                detail="API is not linked to any tool"
            )

        # Store info before clearing
        previous_tool_name = api.linked_to_tool_name
        previous_linked_at = api.linked_at

        # Clear linkage
        api.linked_to_tool_id = None
        api.linked_to_tool_name = None
        api.linked_at = None
        session.add(api)
        session.commit()

        return ResponseEnvelope.success(data={
            "api_id": str(api.id),
            "api_name": api.name,
            "message": f"Unlinked from tool: {previous_tool_name}",
            "previous_link": {
                "tool_name": previous_tool_name,
                "linked_at": previous_linked_at.isoformat() if previous_linked_at else None
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unlink from tool failed: {str(e)}")
        raise HTTPException(500, str(e))
