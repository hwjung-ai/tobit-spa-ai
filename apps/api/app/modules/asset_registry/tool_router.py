"""
Tool Asset API Router.

Provides CRUD endpoints for Tool Assets and tool testing functionality.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from core.auth import get_current_user
from core.db import get_session, get_session_context
from core.tenant import get_current_tenant
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from schemas.common import ResponseEnvelope
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

from models.api_definition import ApiDefinition, ApiMode

from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.asset_registry.schemas import (
    ToolAssetCreate,
    ToolAssetUpdate,
)
from app.modules.asset_registry.tool_validator import validate_tool_for_publication
from app.modules.audit_log.crud import create_audit_log
from app.modules.auth.models import TbUser

router = APIRouter(prefix="/asset-registry/tools", tags=["tool-assets"])


def _extract_catalog_source_ref_from_asset(asset: TbAssetRegistry | None) -> str | None:
    if not asset:
        return None
    content = asset.content or {}
    nested_catalog = content.get("catalog")
    if isinstance(nested_catalog, dict):
        nested_source_ref = nested_catalog.get("source_ref")
        if nested_source_ref:
            return str(nested_source_ref)
    top_source_ref = content.get("source_ref")
    return str(top_source_ref) if top_source_ref else None


def _resolve_published_asset_by_ref(
    session: Session,
    *,
    asset_type: str,
    ref: str,
    tenant_id: str,
) -> TbAssetRegistry | None:
    if not ref:
        return None

    query = (
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == asset_type)
        .where(TbAssetRegistry.status == "published")
        .where(
            (TbAssetRegistry.tenant_id == tenant_id)
            | (TbAssetRegistry.tenant_id.is_(None))
        )
    )

    try:
        ref_uuid = uuid.UUID(ref)
    except ValueError:
        ref_uuid = None

    if ref_uuid:
        asset = session.exec(query.where(TbAssetRegistry.asset_id == ref_uuid)).first()
        if asset:
            return asset

    return session.exec(query.where(TbAssetRegistry.name == ref)).first()


def _validate_tool_references(
    session: Session,
    *,
    tool_type: str | None,
    tool_config: dict[str, Any] | None,
    tool_catalog_ref: str | None,
    tenant_id: str,
) -> list[str]:
    errors: list[str] = []
    normalized_type = (tool_type or "").strip().lower()
    config = tool_config or {}
    source_ref_value = config.get("source_ref")
    source_ref = str(source_ref_value).strip() if source_ref_value else ""

    if normalized_type in {"database_query", "graph_query"}:
        if not source_ref:
            errors.append(f"{normalized_type}: source_ref is required in tool_config")
        else:
            source_asset = _resolve_published_asset_by_ref(
                session,
                asset_type="source",
                ref=source_ref,
                tenant_id=tenant_id,
            )
            if not source_asset:
                errors.append(
                    f"{normalized_type}: source_ref '{source_ref}' not found in published source assets"
                )

    if tool_catalog_ref:
        catalog_asset = _resolve_published_asset_by_ref(
            session,
            asset_type="catalog",
            ref=tool_catalog_ref,
            tenant_id=tenant_id,
        )
        if not catalog_asset:
            errors.append(
                f"tool_catalog_ref '{tool_catalog_ref}' not found in published catalog assets"
            )
            return errors

        catalog_source_ref = _extract_catalog_source_ref_from_asset(catalog_asset)
        if source_ref and catalog_source_ref and source_ref != catalog_source_ref:
            errors.append(
                "tool_catalog_ref source mismatch: "
                f"tool_config.source_ref='{source_ref}' "
                f"!= catalog.source_ref='{catalog_source_ref}'"
            )

    return errors


def _serialize_tool_asset(asset: TbAssetRegistry) -> dict[str, Any]:
    """Serialize tool asset to dict."""
    data = {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "tool_type": asset.tool_type,
        "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
        "tool_config": asset.tool_config,
        "tool_input_schema": asset.tool_input_schema,
        "tool_output_schema": asset.tool_output_schema,
        "tags": asset.tags,
        "tenant_id": asset.tenant_id,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }

    # API Manager linkage info
    if asset.linked_from_api_id:
        data["linked_from_api"] = {
            "api_id": str(asset.linked_from_api_id),
            "api_name": asset.linked_from_api_name,
            "linked_at": asset.linked_from_api_at.isoformat()
            if asset.linked_from_api_at
            else None,
            "import_mode": asset.import_mode,
            "last_synced_at": asset.last_synced_at.isoformat()
            if asset.last_synced_at
            else None,
            "is_internal_api": True,  # Flag to indicate this is imported from internal API
        }

    return data


@router.get("", response_model=ResponseEnvelope)
def list_tools(
    status: str | None = Query(None, description="Filter by status (draft/published)"),
    tool_type: str | None = Query(None, description="Filter by tool_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_builtin: bool = Query(
        True, description="Include built-in tools (CI, Graph, Metric, etc)"
    ),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """List all tool assets (both database and built-in tools)."""
    with get_session_context() as session:
        # Get tools from database (tenant-scoped)
        query = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")
        query = query.where(
            (TbAssetRegistry.tenant_id == tenant_id)
            | (TbAssetRegistry.tenant_id.is_(None))
        )

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
            from app.modules.ops.services.orchestration.tools.base import (
                get_tool_registry,
            )

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
                    "description": getattr(
                        tool_instance, "description", f"{tool_name.capitalize()} Tool"
                    ),
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
    tenant_id: str = Depends(get_current_tenant),
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

        ref_errors = _validate_tool_references(
            session,
            tool_type=payload.tool_type,
            tool_config=payload.tool_config,
            tool_catalog_ref=payload.tool_catalog_ref,
            tenant_id=tenant_id,
        )
        if ref_errors:
            raise HTTPException(status_code=400, detail="; ".join(ref_errors))

        # Create tool asset
        asset = TbAssetRegistry(
            asset_type="tool",
            name=payload.name,
            description=payload.description,
            tool_type=payload.tool_type,
            tool_catalog_ref=payload.tool_catalog_ref,
            tool_config=payload.tool_config,
            tool_input_schema=payload.tool_input_schema,
            tool_output_schema=payload.tool_output_schema,
            tags=payload.tags,
            created_by=payload.created_by or str(current_user.id),
            tenant_id=tenant_id,
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
                "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
                "tool_config": asset.tool_config,
                "tool_input_schema": asset.tool_input_schema,
                "tool_output_schema": asset.tool_output_schema,
            },
        )
        session.add(history)
        session.commit()

        create_audit_log(
            session=session,
            trace_id=str(uuid.uuid4()),
            resource_type="tool_asset",
            resource_id=str(asset.asset_id),
            action="create",
            actor=str(current_user.id),
            changes={"name": asset.name, "tool_type": asset.tool_type},
        )

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
            logger.debug(
                "Invalid UUID format for asset_id, falling back to name lookup"
            )
            asset = None

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
            logger.debug(
                "Invalid UUID format for asset_id, falling back to name lookup"
            )
            asset = None

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

        effective_tool_type = payload.tool_type if payload.tool_type is not None else asset.tool_type
        effective_tool_config = (
            payload.tool_config if payload.tool_config is not None else asset.tool_config
        )
        effective_tool_catalog_ref = (
            payload.tool_catalog_ref
            if payload.tool_catalog_ref is not None
            else asset.tool_catalog_ref
        )
        ref_errors = _validate_tool_references(
            session,
            tool_type=effective_tool_type,
            tool_config=effective_tool_config,
            tool_catalog_ref=effective_tool_catalog_ref,
            tenant_id=asset.tenant_id or "",
        )
        if ref_errors:
            raise HTTPException(status_code=400, detail="; ".join(ref_errors))

        # Update fields
        if payload.name is not None:
            asset.name = payload.name
        if payload.description is not None:
            asset.description = payload.description
        if payload.tool_type is not None:
            asset.tool_type = payload.tool_type
        if payload.tool_catalog_ref is not None:
            asset.tool_catalog_ref = payload.tool_catalog_ref
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
            logger.debug(
                "Invalid UUID format for asset_id, falling back to name lookup"
            )
            asset = None

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

        try:
            # Delete version history first
            histories = session.exec(
                select(TbAssetVersionHistory).where(
                    TbAssetVersionHistory.asset_id == asset.asset_id
                )
            ).all()
            for history in histories:
                session.delete(history)

            deleted_name = asset.name
            deleted_id = str(asset.asset_id)
            session.delete(asset)
            session.commit()

            create_audit_log(
                session=session,
                trace_id=str(uuid.uuid4()),
                resource_type="tool_asset",
                resource_id=deleted_id,
                action="delete",
                actor=str(current_user.id),
                changes={"name": deleted_name},
            )

            return ResponseEnvelope.success(message="Tool asset deleted")
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to delete tool asset: {str(e)}"
            )


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
            logger.debug(
                "Invalid UUID format for asset_id, falling back to name lookup"
            )
            asset = None

        # Try by name
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_id)
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="Tool asset not found")

        ref_errors = _validate_tool_references(
            session,
            tool_type=asset.tool_type,
            tool_config=asset.tool_config,
            tool_catalog_ref=asset.tool_catalog_ref,
            tenant_id=asset.tenant_id or "",
        )
        publication_errors = validate_tool_for_publication(asset)
        all_errors = [*ref_errors, *publication_errors]
        if all_errors:
            raise HTTPException(
                status_code=400,
                detail=f"Tool publication validation failed: {'; '.join(all_errors)}",
            )

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
                "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
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

        create_audit_log(
            session=session,
            trace_id=str(uuid.uuid4()),
            resource_type="tool_asset",
            resource_id=str(asset.asset_id),
            action="publish",
            actor=str(current_user.id),
            changes={"name": asset.name, "version": asset.version},
        )

        return ResponseEnvelope.success(data={"asset": _serialize_tool_asset(asset)})


@router.post("/{asset_id}/test", response_model=ResponseEnvelope)
async def test_tool(
    asset_id: str,
    test_input: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
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
            logger.debug(
                "Invalid UUID format for asset_id, falling back to name lookup"
            )
            asset = None

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
        from app.modules.ops.services.orchestration.tools.base import ToolContext

        context = ToolContext(
            tenant_id=tenant_id,
            user_id=str(current_user.id),
            request_id=f"test_{uuid.uuid4().hex[:8]}",
        )

        # Execute tool
        try:
            from app.modules.ops.services.orchestration.tools.dynamic_tool import (
                DynamicTool,
            )

            # Create DynamicTool instance from plain dict payload.
            tool_asset_payload = {
                "asset_id": str(asset.asset_id),
                "name": asset.name,
                "description": asset.description or "",
                "tool_type": asset.tool_type or "",
                "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
                "tool_config": asset.tool_config or {},
                "tool_input_schema": asset.tool_input_schema or {},
                "tool_output_schema": asset.tool_output_schema,
                "tags": asset.tags,
            }

            tool = DynamicTool(tool_asset_payload)

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
        from app.modules.ops.services.orchestration.tools.base import get_tool_registry

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
                    from app.modules.asset_registry.schemas import ToolAssetRead
                    from app.modules.ops.services.orchestration.tools.dynamic_tool import (
                        DynamicTool,
                    )

                    tool_asset_read = ToolAssetRead(
                        asset_id=str(asset.asset_id),
                        asset_type=asset.asset_type,
                        name=asset.name,
                        description=asset.description or "",
                        version=asset.version,
                        status=asset.status,
                        tool_type=asset.tool_type or "",
                        tool_catalog_ref=getattr(asset, "tool_catalog_ref", None),
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

                    # Register instance with registry
                    registry.register_dynamic(tool)
                    loaded_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to load tool asset '{asset.name}' (ID: {asset.asset_id}) - "
                        f"{type(e).__name__}: {str(e)}",
                        exc_info=True,
                    )
                    # Continue loading remaining tools

            return ResponseEnvelope.success(
                data={
                    "loaded_count": loaded_count,
                    "total_tools": len(registry.get_available_tools()),
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload tools: {e}")


# ============================================================================
# API Manager Integration Endpoints
# ============================================================================


@router.get("/available-api-exports", response_model=ResponseEnvelope)
def get_available_api_exports(
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Get list of APIs marked for export from API Manager.

    Returns APIs that are ready for import as Tools.
    Only includes APIs with linked_to_tool_name set but linked_to_tool_id is NULL.
    """
    from models.api_definition import ApiDefinition

    with get_session_context() as db_session:
        # Query APIs marked for export (ready for import)
        apis = db_session.exec(
            select(ApiDefinition)
            .where(ApiDefinition.linked_to_tool_name.is_not(None))
            .where(ApiDefinition.linked_to_tool_id.is_(None))  # Not yet imported
            .where(ApiDefinition.deleted_at.is_(None))
            .order_by(ApiDefinition.linked_at.desc())
        ).all()

        export_list = []
        for api in apis:
            export_list.append(
                {
                    "api_id": str(api.id),
                    "api_name": api.name,
                    "api_description": api.description,
                    "api_mode": api.mode.value if api.mode else None,
                    "api_method": api.method,
                    "api_path": api.path,
                    "linked_at": api.linked_at.isoformat() if api.linked_at else None,
                    "is_imported": bool(api.linked_to_tool_id),
                }
            )

        return ResponseEnvelope.success(
            data={"exports": export_list, "total": len(export_list)}
        )


@router.post("/import-from-api-manager/{api_id}", response_model=ResponseEnvelope)
async def import_from_api_manager(
    api_id: str,
    body: dict[str, Any] = Body(default={}),
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Import an API from API Manager as a Tool.

    Creates a Tool Asset from an API Definition and establishes
    bidirectional linkage between API and Tool.
    """
    from models.api_definition import ApiDefinition

    with get_session_context() as db_session:
        # 1. Fetch the source API
        api = db_session.get(ApiDefinition, api_id)
        if not api or api.deleted_at:
            raise HTTPException(404, "API not found")

        # 2. Check if already imported
        if api.linked_to_tool_id:
            raise HTTPException(
                400, f"API already imported as tool: {api.linked_to_tool_name}"
            )

        # 3. Prepare Tool Asset data
        tool_name = body.get("name") or f"Tool from API: {api.name}"
        tool_description = body.get("description") or (
            f"Tool imported from API Manager API '{api.name}'. "
            f"Mode: {api.mode.value}. "
            f"Use when: {api.description or api.name}"
        )

        # 4. Extract input_schema from API
        input_schema = _extract_input_schema_from_api(api)

        # 5. Infer output_schema if requested
        output_schema = None
        if body.get("infer_output_schema", False):
            output_schema = await _infer_output_schema_from_api(api, db_session)

        # 6. Create tool_config pointing to API endpoint
        tool_config = {
            "url": f"/api-manager/apis/{api.id}/execute",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {token}",
                "X-Tenant-Id": "{tenant_id}",
            },
        }

        # 7. Check for existing tool with same name
        existing = db_session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "tool")
            .where(TbAssetRegistry.name == tool_name)
        ).first()

        if existing:
            raise HTTPException(409, f"Tool with name '{tool_name}' already exists")

        # 8. Create Tool Asset
        tool_asset = TbAssetRegistry(
            asset_type="tool",
            name=tool_name,
            description=tool_description,
            tool_type="http_api",
            tool_config=tool_config,
            tool_input_schema=input_schema,
            tool_output_schema=output_schema,
            tags={
                "source": "api_manager",
                "api_id": str(api.id),
                "api_name": api.name,
                "import_mode": "api_to_tool",
            },
            created_by=str(current_user.id),
            status="draft",
            version=1,
            # API Manager linkage fields
            linked_from_api_id=api.id,
            linked_from_api_name=api.name,
            linked_from_api_at=datetime.now(),
            import_mode="api_to_tool",
            last_synced_at=datetime.now(),
        )

        db_session.add(tool_asset)
        db_session.commit()
        db_session.refresh(tool_asset)

        # 9. Create version history
        history = TbAssetVersionHistory(
            asset_id=tool_asset.asset_id,
            version=1,
            snapshot={
                "name": tool_asset.name,
                "description": tool_asset.description,
                "tool_type": tool_asset.tool_type,
                "tool_config": tool_asset.tool_config,
                "tool_input_schema": tool_asset.tool_input_schema,
                "tool_output_schema": tool_asset.tool_output_schema,
                "linked_from_api_id": str(tool_asset.linked_from_api_id),
                "linked_from_api_name": tool_asset.linked_from_api_name,
            },
        )
        db_session.add(history)
        db_session.commit()

        # 10. Complete bidirectional linkage (update API side)
        api.linked_to_tool_id = tool_asset.asset_id
        api.linked_to_tool_name = tool_asset.name
        db_session.add(api)
        db_session.commit()

        return ResponseEnvelope.success(
            data={
                "tool_id": str(tool_asset.asset_id),
                "tool_name": tool_asset.name,
                "api_id": str(api.id),
                "api_name": api.name,
                "status": "imported",
                "message": "Tool created successfully from API Manager",
                "asset": _serialize_tool_asset(tool_asset),
            }
        )


@router.post("/{tool_id}/sync-from-api", response_model=ResponseEnvelope)
async def sync_tool_from_api(
    tool_id: str,
    session: Session = Depends(get_session),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Sync Tool with latest changes from API Manager.

    Updates Tool's input_schema and description based on source API.
    Only works for Tools imported from API Manager.
    """
    from models.api_definition import ApiDefinition

    with get_session_context() as db_session:
        # 1. Fetch the Tool
        tool_uuid = uuid.UUID(tool_id)
        tool = db_session.get(TbAssetRegistry, tool_uuid)
        if not tool or tool.asset_type != "tool":
            raise HTTPException(404, "Tool not found")

        # 2. Check if this tool was imported from API Manager
        if not tool.linked_from_api_id:
            raise HTTPException(
                400,
                "This tool was not imported from API Manager. "
                "Manual sync not available.",
            )

        # 3. Fetch the source API
        api = db_session.get(ApiDefinition, tool.linked_from_api_id)
        if not api or api.deleted_at:
            raise HTTPException(404, "Linked API not found or deleted")

        # 4. Only draft tools can be synced
        if tool.status != "draft":
            raise HTTPException(
                400,
                "Only draft tools can be synced. "
                "Create a new version or rollback to draft first.",
            )

        # 5. Update Tool fields
        tool.tool_input_schema = _extract_input_schema_from_api(api)
        tool.description = (
            f"Tool imported from API Manager API '{api.name}'. "
            f"Mode: {api.mode.value}. "
            f"Use when: {api.description or api.name}"
        )
        tool.updated_at = datetime.now()
        tool.last_synced_at = datetime.now()

        db_session.add(tool)
        db_session.commit()
        db_session.refresh(tool)

        return ResponseEnvelope.success(
            data={
                "tool_id": str(tool.asset_id),
                "tool_name": tool.name,
                "synced_at": tool.last_synced_at.isoformat(),
                "api_version": api.updated_at.isoformat() if api.updated_at else None,
                "message": "Tool synced successfully from API Manager",
                "asset": _serialize_tool_asset(tool),
            }
        )


# ============================================================================
# MCP Server Integration Endpoints
# ============================================================================


@router.post("/discover-mcp-tools", response_model=ResponseEnvelope)
async def discover_mcp_tools(
    body: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Discover available tools from an MCP server.

    Connects to the MCP server and calls tools/list to retrieve
    the list of tools provided by that server.

    Body:
        server_url: MCP server endpoint (e.g. "http://localhost:3100/sse")
        transport: "sse" (default) or "streamable_http"
        headers: Optional extra HTTP headers
    """
    import httpx

    server_url = body.get("server_url")
    transport = body.get("transport", "sse")
    extra_headers = body.get("headers", {})
    timeout_sec = body.get("timeout_ms", 15000) / 1000

    if not server_url:
        raise HTTPException(400, "server_url is required")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }

    try:
        if transport == "streamable_http":
            # Streamable HTTP: direct POST
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            headers.update(extra_headers)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    server_url, json=payload, headers=headers, timeout=timeout_sec
                )
                response.raise_for_status()
                result = response.json()
        else:
            # SSE: discover message endpoint first, then POST
            headers = {"Content-Type": "application/json"}
            headers.update(extra_headers)

            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                # Step 1: Connect to SSE to get message endpoint
                message_url = None
                async with client.stream(
                    "GET", server_url, headers={"Accept": "text/event-stream"}
                ) as sse_init:
                    async for line in sse_init.aiter_lines():
                        if line.startswith("event: endpoint"):
                            continue
                        if line.startswith("data: "):
                            endpoint_path = line[6:].strip()
                            if endpoint_path.startswith("http"):
                                message_url = endpoint_path
                            else:
                                from urllib.parse import urljoin

                                message_url = urljoin(server_url, endpoint_path)
                            break

                if not message_url:
                    raise HTTPException(
                        502, "Failed to discover MCP message endpoint from SSE"
                    )

                # Step 2: Send tools/list
                response = await client.post(message_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

        # Parse JSON-RPC response
        if "error" in result:
            err = result["error"]
            raise HTTPException(
                502,
                f"MCP server error ({err.get('code', '?')}): {err.get('message', 'Unknown')}",
            )

        mcp_tools = result.get("result", {}).get("tools", [])

        # Normalize tool list
        tools = []
        for t in mcp_tools:
            tools.append(
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "inputSchema": t.get("inputSchema", {}),
                }
            )

        return ResponseEnvelope.success(
            data={
                "tools": tools,
                "total": len(tools),
                "server_url": server_url,
                "transport": transport,
            }
        )

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            502,
            f"MCP server returned HTTP {exc.response.status_code}: {exc.response.text[:500]}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            502,
            f"Failed to connect to MCP server: {str(exc)}",
        )


@router.post("/import-from-mcp", response_model=ResponseEnvelope)
def import_from_mcp(
    body: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Import one or more tools from an MCP server as Tool Assets.

    Body:
        server_url: MCP server endpoint
        transport: "sse" or "streamable_http"
        headers: Optional extra HTTP headers for the MCP server
        tools: List of tools to import, each with:
            - name: Tool name on the MCP server
            - description: Tool description
            - inputSchema: Tool input JSON Schema
            - custom_name: (optional) Override the tool asset name
    """
    server_url = body.get("server_url")
    transport = body.get("transport", "sse")
    extra_headers = body.get("headers", {})
    tools_to_import = body.get("tools", [])

    if not server_url:
        raise HTTPException(400, "server_url is required")
    if not tools_to_import:
        raise HTTPException(400, "tools list is required (at least one tool)")

    imported = []
    errors = []

    with get_session_context() as session:
        for tool_info in tools_to_import:
            mcp_tool_name = tool_info.get("name")
            if not mcp_tool_name:
                errors.append({"name": None, "error": "Tool name is required"})
                continue

            # Use custom name or prefix with mcp_
            asset_name = tool_info.get("custom_name") or f"mcp_{mcp_tool_name}"
            description = tool_info.get("description") or f"MCP tool: {mcp_tool_name}"
            input_schema = tool_info.get(
                "inputSchema",
                {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            )

            # Check for existing tool with same name
            existing = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "tool")
                .where(TbAssetRegistry.name == asset_name)
            ).first()

            if existing:
                errors.append(
                    {
                        "name": asset_name,
                        "mcp_tool": mcp_tool_name,
                        "error": f"Tool '{asset_name}' already exists",
                    }
                )
                continue

            # Create Tool Asset
            tool_config = {
                "server_url": server_url,
                "transport": transport,
                "tool_name": mcp_tool_name,
                "timeout_ms": 30000,
            }
            if extra_headers:
                tool_config["headers"] = extra_headers

            asset = TbAssetRegistry(
                asset_type="tool",
                name=asset_name,
                description=description,
                tool_type="mcp",
                tool_config=tool_config,
                tool_input_schema=input_schema,
                tool_output_schema=None,
                tags={
                    "source": "mcp_import",
                    "mcp_server_url": server_url,
                    "mcp_transport": transport,
                    "mcp_tool_name": mcp_tool_name,
                },
                created_by=str(current_user.id),
                status="draft",
                version=1,
            )

            session.add(asset)
            session.flush()  # Get asset_id

            # Version history
            history = TbAssetVersionHistory(
                asset_id=asset.asset_id,
                version=1,
                snapshot={
                    "name": asset.name,
                    "description": asset.description,
                    "tool_type": "mcp",
                    "tool_config": tool_config,
                    "tool_input_schema": input_schema,
                    "mcp_server_url": server_url,
                    "mcp_tool_name": mcp_tool_name,
                },
            )
            session.add(history)

            imported.append(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "mcp_tool": mcp_tool_name,
                    "status": "draft",
                }
            )

        session.commit()

    return ResponseEnvelope.success(
        data={
            "imported": imported,
            "errors": errors,
            "total_imported": len(imported),
            "total_errors": len(errors),
        }
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _extract_input_schema_from_api(api: ApiDefinition) -> dict:
    """Extract input_schema from API's param_schema."""
    if not api.param_schema:
        return {"type": "object", "properties": {}, "required": []}

    properties = {}
    required = []

    param_schema = api.param_schema if isinstance(api.param_schema, dict) else {}

    for param_name, param_info in (param_schema.get("properties") or {}).items():
        properties[param_name] = {
            "type": param_info.get("type", "string"),
            "description": param_info.get("description", f"Parameter: {param_name}"),
        }
        if param_info.get("required", False):
            required.append(param_name)

    return {"type": "object", "properties": properties, "required": required}


async def _infer_output_schema_from_api(
    api: ApiDefinition, session: Session
) -> dict | None:
    """
    Infer output_schema by executing the API with sample data.

    Returns schema based on actual execution results.
    """
    try:
        if api.mode == ApiMode.sql:
            from app.modules.api_manager.executor import execute_sql_api

            result = execute_sql_api(
                session=session,
                api_id=str(api.id),
                logic_body=api.logic,
                params={},
                limit=1,
                executed_by="schema_inference",
            )

            if result.columns:
                properties = {}
                for col in result.columns:
                    properties[col["name"]] = {
                        "type": _map_column_type(col["type"]),
                        "description": col.get("description", f"Column: {col['name']}"),
                    }

                return {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties.keys()),
                    },
                }
    except Exception as e:
        import logging

        logging.warning(f"Failed to infer output schema: {e}")

    return None


def _map_column_type(db_type: str) -> str:
    """Map database type to JSON Schema type."""
    type_mapping = {
        "integer": "integer",
        "bigint": "integer",
        "smallint": "integer",
        "numeric": "number",
        "decimal": "number",
        "real": "number",
        "float": "number",
        "double precision": "number",
        "text": "string",
        "varchar": "string",
        "char": "string",
        "boolean": "boolean",
        "date": "string",
        "timestamp": "string",
        "timestamptz": "string",
        "json": "object",
        "jsonb": "object",
        "uuid": "string",
    }
    return type_mapping.get(db_type.lower(), "string")
