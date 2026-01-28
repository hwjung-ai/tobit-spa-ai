"""
Tool Asset API Router.

Provides CRUD endpoints for Tool Assets and tool testing functionality.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlmodel import Session, select

from core.auth import get_current_user
from core.db import get_session, get_session_context
from schemas.common import ResponseEnvelope

from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.asset_registry.schemas import (
    ToolAssetCreate,
    ToolAssetRead,
    ToolAssetUpdate,
)
from app.modules.auth.models import TbUser

router = APIRouter(prefix="/asset-registry/tools", tags=["tool-assets"])


def _serialize_tool_asset(asset: TbAssetRegistry) -> dict[str, Any]:
    """Serialize tool asset to dict."""
    return {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "tool_type": asset.tool_type,
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


@router.get("", response_model=ResponseEnvelope)
def list_tools(
    status: str | None = Query(None, description="Filter by status (draft/published)"),
    tool_type: str | None = Query(None, description="Filter by tool_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_builtin: bool = Query(True, description="Include built-in tools (CI, Graph, Metric, etc)"),
    current_user: TbUser = Depends(get_current_user),
):
    """List all tool assets (both database and built-in tools)."""
    with get_session_context() as session:
        # Get tools from database
        query = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")

        if status:
            query = query.where(TbAssetRegistry.status == status)
        if tool_type:
            query = query.where(TbAssetRegistry.tool_type == tool_type)

        query = query.order_by(TbAssetRegistry.updated_at.desc())

        db_assets = session.exec(query).all()
        db_tools = [_serialize_tool_asset(a) for a in db_assets]

        # Get built-in tools from registry if requested
        builtin_tools = []
        if include_builtin:
            from app.modules.ops.services.ci.tools.base import get_tool_registry

            registry = get_tool_registry()
            builtin_tool_instances = registry.get_available_tools()

            for tool_name, tool_instance in builtin_tool_instances.items():
                # Skip if already in DB (avoid duplicates)
                if any(t["name"] == tool_name for t in db_tools):
                    continue

                # Convert built-in tool to asset format
                builtin_tool = {
                    "asset_id": f"builtin_{tool_name}",  # Virtual ID
                    "asset_type": "tool",
                    "name": tool_name,
                    "description": getattr(tool_instance, "description", f"{tool_name.capitalize()} Tool"),
                    "version": 1,
                    "status": "published",  # Built-in tools are always published
                    "tool_type": "builtin",
                    "tool_config": {},
                    "tool_input_schema": getattr(tool_instance, "input_schema", {}),
                    "tool_output_schema": None,
                    "tags": {"builtin": True},
                    "created_by": "system",
                    "published_by": "system",
                    "published_at": None,
                    "created_at": None,
                    "updated_at": None,
                }

                # Apply status filter (only if it's not "all")
                if status and status != "published":
                    continue

                # Apply tool_type filter (only if specified)
                if tool_type and tool_type != "builtin":
                    continue

                builtin_tools.append(builtin_tool)

        # Combine and sort all tools
        all_tools = db_tools + builtin_tools

        # Sort by updated_at or created_at, with None values sorted to the end
        # Use offset-aware datetime.min for comparison to handle both naive and aware datetimes
        def sort_key(x):
            timestamp = x.get("updated_at") or x.get("created_at")
            if timestamp is None:
                # Return a very old datetime (offset-aware to match DB datetimes)
                return datetime.min.replace(tzinfo=timezone.utc)
            # If timestamp is naive, make it aware for consistent comparison
            if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=timezone.utc)
            return timestamp

        all_tools.sort(key=sort_key, reverse=True)

        # Apply pagination
        total = len(all_tools)
        offset = (page - 1) * page_size
        paginated_tools = all_tools[offset : offset + page_size]

        return ResponseEnvelope.success(
            data={
                "assets": paginated_tools,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )


@router.post("", response_model=ResponseEnvelope)
def create_tool(
    payload: ToolAssetCreate,
    current_user: TbUser = Depends(get_current_user),
):
    """Create a new tool asset."""
    with get_session_context() as session:
        # Check for existing tool with same name
        existing = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "tool")
            .where(TbAssetRegistry.name == payload.name)
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Tool with name '{payload.name}' already exists",
            )

        # Create tool asset
        asset = TbAssetRegistry(
            asset_type="tool",
            name=payload.name,
            description=payload.description,
            tool_type=payload.tool_type,
            tool_config=payload.tool_config,
            tool_input_schema=payload.tool_input_schema,
            tool_output_schema=payload.tool_output_schema,
            tags=payload.tags,
            created_by=payload.created_by or str(current_user.id),
            status="draft",
            version=1,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)

        # Create version history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "name": asset.name,
                "description": asset.description,
                "tool_type": asset.tool_type,
                "tool_config": asset.tool_config,
                "tool_input_schema": asset.tool_input_schema,
                "tool_output_schema": asset.tool_output_schema,
            },
        )
        session.add(history)
        session.commit()

        return ResponseEnvelope.success(data={"asset": _serialize_tool_asset(asset)})


@router.get("/{asset_id}", response_model=ResponseEnvelope)
def get_tool(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Get a tool asset by ID or name."""
    with get_session_context() as session:
        asset = None

        # Try UUID first
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
            if asset and asset.asset_type != "tool":
                asset = None
        except ValueError:
            pass

        # Try by name
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_id)
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Tool asset not found")

        return ResponseEnvelope.success(data={"asset": _serialize_tool_asset(asset)})


@router.put("/{asset_id}", response_model=ResponseEnvelope)
def update_tool(
    asset_id: str,
    payload: ToolAssetUpdate,
    current_user: TbUser = Depends(get_current_user),
):
    """Update a tool asset."""
    with get_session_context() as session:
        asset = None

        # Try UUID first
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
            if asset and asset.asset_type != "tool":
                asset = None
        except ValueError:
            pass

        # Try by name
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_id)
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Tool asset not found")

        if asset.status != "draft":
            raise HTTPException(
                status_code=400, detail="Only draft tools can be updated"
            )

        # Update fields
        if payload.name is not None:
            asset.name = payload.name
        if payload.description is not None:
            asset.description = payload.description
        if payload.tool_type is not None:
            asset.tool_type = payload.tool_type
        if payload.tool_config is not None:
            asset.tool_config = payload.tool_config
        if payload.tool_input_schema is not None:
            asset.tool_input_schema = payload.tool_input_schema
        if payload.tool_output_schema is not None:
            asset.tool_output_schema = payload.tool_output_schema
        if payload.tags is not None:
            asset.tags = payload.tags

        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()
        session.refresh(asset)

        return ResponseEnvelope.success(data={"asset": _serialize_tool_asset(asset)})


@router.delete("/{asset_id}")
def delete_tool(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Delete a tool asset."""
    with get_session_context() as session:
        asset = None

        # Try UUID first
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
            if asset and asset.asset_type != "tool":
                asset = None
        except ValueError:
            pass

        # Try by name
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_id)
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Tool asset not found")

        if asset.status != "draft":
            raise HTTPException(
                status_code=400, detail="Only draft tools can be deleted"
            )

        session.delete(asset)
        session.commit()

        return ResponseEnvelope.success(message="Tool asset deleted")


@router.post("/{asset_id}/publish", response_model=ResponseEnvelope)
def publish_tool(
    asset_id: str,
    body: dict[str, Any] = Body(default={}),
    current_user: TbUser = Depends(get_current_user),
):
    """Publish a tool asset."""
    published_by = body.get("published_by") or str(current_user.id)

    with get_session_context() as session:
        asset = None

        # Try UUID first
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
            if asset and asset.asset_type != "tool":
                asset = None
        except ValueError:
            pass

        # Try by name
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_id)
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Tool asset not found")

        # Increment version and publish
        asset.version = (asset.version or 0) + 1
        asset.status = "published"
        asset.published_by = published_by
        asset.published_at = datetime.now()
        asset.updated_at = datetime.now()

        session.add(asset)

        # Create version history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "name": asset.name,
                "description": asset.description,
                "tool_type": asset.tool_type,
                "tool_config": asset.tool_config,
                "tool_input_schema": asset.tool_input_schema,
                "tool_output_schema": asset.tool_output_schema,
            },
            published_by=published_by,
            published_at=asset.published_at,
        )
        session.add(history)
        session.commit()
        session.refresh(asset)

        return ResponseEnvelope.success(data={"asset": _serialize_tool_asset(asset)})


@router.post("/{asset_id}/test", response_model=ResponseEnvelope)
async def test_tool(
    asset_id: str,
    test_input: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    """Test a tool asset with given input."""
    with get_session_context() as session:
        asset = None

        # Try UUID first
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
            if asset and asset.asset_type != "tool":
                asset = None
        except ValueError:
            pass

        # Try by name
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_id)
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Tool asset not found")

        # Create test context
        from app.modules.ops.services.ci.tools.base import ToolContext

        context = ToolContext(
            tenant_id="test",
            user_id=str(current_user.id),
            request_id="test_request",
        )

        # Execute tool
        try:
            from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool
            from app.modules.asset_registry.schemas import ToolAssetRead

            # Create DynamicTool instance
            tool_asset_read = ToolAssetRead(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description or "",
                version=asset.version,
                status=asset.status,
                tool_type=asset.tool_type or "",
                tool_config=asset.tool_config or {},
                tool_input_schema=asset.tool_input_schema or {},
                tool_output_schema=asset.tool_output_schema,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )

            tool = DynamicTool(
                asset_id=str(asset.asset_id),
                asset_data=tool_asset_read,
            )

            result = await tool.execute(context, test_input)

            return ResponseEnvelope.success(
                data={
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                    "error_details": result.error_details,
                }
            )

        except Exception as e:
            return ResponseEnvelope.success(
                data={
                    "success": False,
                    "data": None,
                    "error": str(e),
                    "error_details": {"exception_type": type(e).__name__},
                }
            )


@router.post("/reload", response_model=ResponseEnvelope)
def reload_tools(
    current_user: TbUser = Depends(get_current_user),
):
    """Reload all published tools into the tool registry."""
    try:
        from app.modules.ops.services.ci.tools.base import get_tool_registry

        registry = get_tool_registry()

        # Load published tools from DB
        with get_session_context() as session:
            assets = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.status == "published")
            ).all()

            loaded_count = 0
            for asset in assets:
                try:
                    from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool
                    from app.modules.asset_registry.schemas import ToolAssetRead

                    tool_asset_read = ToolAssetRead(
                        asset_id=str(asset.asset_id),
                        asset_type=asset.asset_type,
                        name=asset.name,
                        description=asset.description or "",
                        version=asset.version,
                        status=asset.status,
                        tool_type=asset.tool_type or "",
                        tool_config=asset.tool_config or {},
                        tool_input_schema=asset.tool_input_schema or {},
                        tool_output_schema=asset.tool_output_schema,
                        tags=asset.tags,
                        created_by=asset.created_by,
                        published_by=asset.published_by,
                        published_at=asset.published_at,
                        created_at=asset.created_at,
                        updated_at=asset.updated_at,
                    )

                    tool = DynamicTool(
                        asset_id=str(asset.asset_id),
                        asset_data=tool_asset_read,
                    )

                    # Register with tool name
                    registry._instances[asset.name] = tool
                    loaded_count += 1
                except Exception as e:
                    pass  # Skip failed tools

            return ResponseEnvelope.success(
                data={
                    "loaded_count": loaded_count,
                    "total_tools": len(registry.get_available_tools()),
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload tools: {e}")
