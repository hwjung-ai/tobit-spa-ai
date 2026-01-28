"""
Tool Asset Router for Generic Orchestration System.

This module provides CRUD endpoints for Tool Asset management.
"""

from __future__ import annotations

from core.auth import get_current_user
from core.db import get_session, get_session_context
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from schemas.common import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.asset_registry.crud import (
    create_asset as create_registry_asset,
    delete_asset,
    get_asset,
    list_assets as list_registry_assets,
    publish_asset,
)
from app.modules.asset_registry.crud import (
    create_tool_asset,
    get_tool_asset,
)
from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.asset_registry.schemas import (
    ToolAssetCreate,
    ToolAssetRead,
    ToolAssetUpdate,
)
from app.modules.auth.models import TbUser

router = APIRouter(prefix="/ops/tool-assets")


def _serialize_tool_asset(asset: TbAssetRegistry) -> dict[str, Any]:
    """Serialize tool asset to dict format."""
    return {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "tool_type": asset.tool_type,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "tool_config": asset.tool_config,
        "tool_input_schema": asset.tool_input_schema,
        "tool_output_schema": asset.tool_output_schema,
        "tags": asset.tags,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


@router.post("", response_model=ResponseEnvelope)
def create_tool_asset_endpoint(
    payload: ToolAssetCreate,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create a new tool asset in draft status."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        asset = create_tool_asset(
            session=session,
            name=payload.name,
            description=payload.description,
            tool_type=payload.tool_type,
            tool_config=payload.tool_config,
            tool_input_schema=payload.tool_input_schema,
            tool_output_schema=payload.tool_output_schema,
            tags=payload.tags,
            created_by=current_user.id,
        )

        return ResponseEnvelope.success(
            data={
                "asset": ToolAssetRead(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    tool_type=asset.tool_type,
                    name=asset.name,
                    description=asset.description,
                    version=asset.version,
                    status=asset.status,
                    tool_config=asset.tool_config,
                    tool_input_schema=asset.tool_input_schema,
                    tool_output_schema=asset.tool_output_schema,
                    tags=asset.tags,
                    created_by=asset.created_by,
                    published_by=asset.published_by,
                    published_at=asset.published_at,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                )
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool asset: {str(e)}",
        )


@router.get("", response_model=ResponseEnvelope)
def list_tool_assets(
    status: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List tool assets with optional filters."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        assets = list_registry_assets(
            session=session,
            asset_type="tool",
            status=status,
        )

        data = [_serialize_tool_asset(a) for a in assets]

        if limit is not None:
            data = data[offset : offset + limit]
        elif offset is not None:
            data = data[offset:]

        return ResponseEnvelope.success(
            data={
                "assets": data,
                "total": len(assets),
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tool assets: {str(e)}",
        )


@router.get("/{asset_id}", response_model=ResponseEnvelope)
def get_tool_asset_endpoint(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get a tool asset by ID."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        asset = get_tool_asset(session=session, asset_id=asset_id)

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool asset not found: {asset_id}",
            )

        if asset.asset_type != "tool":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset is not a tool asset: {asset_id}",
            )

        return ResponseEnvelope.success(
            data={
                "asset": ToolAssetRead(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    tool_type=asset.tool_type,
                    name=asset.name,
                    description=asset.description,
                    version=asset.version,
                    status=asset.status,
                    tool_config=asset.tool_config,
                    tool_input_schema=asset.tool_input_schema,
                    tool_output_schema=asset.tool_output_schema,
                    tags=asset.tags,
                    created_by=asset.created_by,
                    published_by=asset.published_by,
                    published_at=asset.published_at,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                )
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool asset: {str(e)}",
        )


@router.patch("/{asset_id}", response_model=ResponseEnvelope)
def update_tool_asset_endpoint(
    asset_id: str,
    payload: ToolAssetUpdate,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Update a draft tool asset."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        asset = get_tool_asset(session=session, asset_id=asset_id)

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool asset not found: {asset_id}",
            )

        if asset.asset_type != "tool":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset is not a tool asset: {asset_id}",
            )

        if asset.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update published asset. Create a new version first.",
            )

        updates = payload.model_dump(exclude_unset=True)
        from app.modules.asset_registry.crud import update_asset

        updated_asset = update_asset(
            session=session,
            asset=asset,
            updates=updates,
            updated_by=current_user.id,
        )

        return ResponseEnvelope.success(
            data={
                "asset": ToolAssetRead(
                    asset_id=str(updated_asset.asset_id),
                    asset_type=updated_asset.asset_type,
                    tool_type=updated_asset.tool_type,
                    name=updated_asset.name,
                    description=updated_asset.description,
                    version=updated_asset.version,
                    status=updated_asset.status,
                    tool_config=updated_asset.tool_config,
                    tool_input_schema=updated_asset.tool_input_schema,
                    tool_output_schema=updated_asset.tool_output_schema,
                    tags=updated_asset.tags,
                    created_by=updated_asset.created_by,
                    published_by=updated_asset.published_by,
                    published_at=updated_asset.published_at,
                    created_at=updated_asset.created_at,
                    updated_at=updated_asset.updated_at,
                )
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool asset: {str(e)}",
        )


@router.delete("/{asset_id}", response_model=ResponseEnvelope)
def delete_tool_asset_endpoint(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete a tool asset."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        asset = get_tool_asset(session=session, asset_id=asset_id)

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool asset not found: {asset_id}",
            )

        if asset.asset_type != "tool":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset is not a tool asset: {asset_id}",
            )

        from app.modules.asset_registry.crud import delete_asset

        delete_asset(session=session, asset=asset)

        return ResponseEnvelope.success(
            data={
                "message": f"Tool asset deleted successfully: {asset_id}",
                "asset_id": asset_id,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool asset: {str(e)}",
        )


@router.post("/{asset_id}/publish", response_model=ResponseEnvelope)
def publish_tool_asset_endpoint(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Publish a draft tool asset."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        asset = get_tool_asset(session=session, asset_id=asset_id)

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool asset not found: {asset_id}",
            )

        if asset.asset_type != "tool":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset is not a tool asset: {asset_id}",
            )

        if asset.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft assets can be published",
            )

        from app.modules.asset_registry.crud import publish_asset

        published_asset = publish_asset(
            session=session,
            asset=asset,
            published_by=current_user.id,
        )

        return ResponseEnvelope.success(
            data={
                "asset": ToolAssetRead(
                    asset_id=str(published_asset.asset_id),
                    asset_type=published_asset.asset_type,
                    tool_type=published_asset.tool_type,
                    name=published_asset.name,
                    description=published_asset.description,
                    version=published_asset.version,
                    status=published_asset.status,
                    tool_config=published_asset.tool_config,
                    tool_input_schema=published_asset.tool_input_schema,
                    tool_output_schema=published_asset.tool_output_schema,
                    tags=published_asset.tags,
                    created_by=published_asset.created_by,
                    published_by=published_asset.published_by,
                    published_at=published_asset.published_at,
                    created_at=published_asset.created_at,
                    updated_at=published_asset.updated_at,
                )
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish tool asset: {str(e)}",
        )
