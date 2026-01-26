from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List

from core.auth import get_current_user

# Permission checks disabled due to missing tb_resource_permission table
# from app.modules.permissions.models import ResourcePermission
# from app.modules.permissions.crud import check_permission
from core.db import get_session, get_session_context
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from schemas.common import ResponseEnvelope
from sqlmodel import Session, select

from app.modules.asset_registry.crud import (
    create_resolver_asset,
    create_schema_asset,
    create_source_asset,
    build_schema_catalog,
    delete_resolver_asset,
    delete_schema_asset,
    delete_source_asset,
    get_resolver_asset,
    get_schema_asset,
    get_source_asset,
    list_assets as list_registry_assets,
    scan_schema,
    simulate_resolver_configuration,
    test_source_connection,
    update_resolver_asset,
    update_schema_asset,
    update_source_asset,
)
from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.asset_registry.resolver_models import (
    ResolverAssetCreate,
    ResolverAssetResponse,
    ResolverAssetUpdate,
    ResolverConfig,
)
from app.modules.asset_registry.schema_models import (
    ScanRequest,
    SchemaAssetCreate,
    SchemaAssetResponse,
    SchemaAssetUpdate,
    SchemaListResponse,
)
from app.modules.asset_registry.schemas import (
    MappingAssetUpdate,
    PolicyAssetUpdate,
    PromptAssetCreate,
    PromptAssetRead,
    PromptAssetUpdate,
    QueryAssetCreate,
    QueryAssetUpdate,
    ScreenAssetCreate,
    ScreenAssetRead,
    ScreenAssetUpdate,
)
from app.modules.asset_registry.source_models import (
    SourceAssetCreate,
    SourceAssetResponse,
    SourceAssetUpdate,
    SourceListResponse,
    SourceType,
)
from app.modules.auth.models import TbUser
from app.modules.inspector import crud as inspector_crud
from app.modules.inspector.schemas import TraceSummary

from .validators import validate_asset

router = APIRouter(prefix="/asset-registry")


from typing import Union


@router.post("/assets", response_model=ResponseEnvelope)
def create_asset(
    payload: Union[PromptAssetCreate, ScreenAssetCreate, QueryAssetCreate],
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if isinstance(payload, ScreenAssetCreate):
        return create_screen_asset_impl(payload, session, current_user)
    elif isinstance(payload, PromptAssetCreate):
        return create_prompt_asset_impl(payload, session, current_user)
    elif isinstance(payload, QueryAssetCreate):
        return create_query_asset_impl(payload, session, current_user)
    else:
        raise HTTPException(status_code=400, detail="Invalid asset type")


def create_screen_asset_impl(
    payload: ScreenAssetCreate, session: Session, current_user: TbUser
):
    if payload.asset_type != "screen":
        raise HTTPException(status_code=400, detail="asset_type must be 'screen'")

    # Check permission
    # permission_result = check_permission(
    #     session=session,
    #     user_id=current_user.id,
    #     role=current_user.role,
    #     permission=ResourcePermission.ASSET_CREATE,
    #     resource_type="asset",
    #     resource_id=None,
    # )

    # if not permission_result.granted:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Permission denied: {permission_result.reason}",
    #     )

    try:
        asset = TbAssetRegistry(
            asset_type="screen",
            screen_id=payload.screen_id,
            name=payload.name,
            description=payload.description,
            screen_schema=payload.screen_schema,
            tags=payload.tags,
            created_by=payload.created_by,
            status="draft",
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)

        # Create initial version history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "schema_json": asset.screen_schema,
                "name": asset.name,
                "description": asset.description,
            },
        )
        session.add(history)
        session.commit()

        return ResponseEnvelope.success(
            data={
                "asset": ScreenAssetRead(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    screen_id=asset.screen_id,
                    name=asset.name,
                    description=asset.description,
                    version=asset.version,
                    status=asset.status,
                    screen_schema=asset.screen_schema,
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
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {str(e)}")


def create_prompt_asset_impl(
    payload: PromptAssetCreate, session: Session, current_user: TbUser
):
    """Create a prompt asset"""
    if payload.asset_type != "prompt":
        raise HTTPException(status_code=400, detail="asset_type must be 'prompt'")

    # Check for existing published asset with same name, scope, and engine
    existing_published = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "prompt")
        .where(TbAssetRegistry.name == payload.name)
        .where(TbAssetRegistry.scope == payload.scope)
        .where(TbAssetRegistry.engine == payload.engine)
        .where(TbAssetRegistry.status == "published")
    ).first()

    if existing_published:
        raise HTTPException(
            status_code=409,
            detail=f"Published prompt asset with name '{payload.name}' (scope='{payload.scope}', engine='{payload.engine}') already exists. "
                   f"Please publish this draft to replace it, or delete the existing published version first."
        )

    try:
        asset = TbAssetRegistry(
            asset_type="prompt",
            name=payload.name,
            scope=payload.scope,
            engine=payload.engine,
            template=payload.template,
            input_schema=payload.input_schema,
            output_contract=payload.output_contract,
            tags=payload.tags,
            created_by=payload.created_by,
            status="draft",
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)

        # Create initial version history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "input_schema": asset.input_schema,
                "output_contract": asset.output_contract,
                "template": asset.template,
                "name": asset.name,
            },
        )
        session.add(history)
        session.commit()

        return ResponseEnvelope.success(
            data={
                "asset": PromptAssetRead(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    name=asset.name,
                    scope=asset.scope,
                    engine=asset.engine,
                    version=asset.version,
                    status=asset.status,
                    template=asset.template,
                    input_schema=asset.input_schema,
                    output_contract=asset.output_contract,
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
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {str(e)}")


def create_query_asset_impl(
    payload: QueryAssetCreate, session: Session, current_user: TbUser
):
    """Create a query asset"""
    if payload.asset_type != "query":
        raise HTTPException(status_code=400, detail="asset_type must be 'query'")

    try:
        asset = TbAssetRegistry(
            asset_type="query",
            name=payload.name,
            description=payload.description,
            scope=payload.scope,
            query_sql=payload.query_sql,
            query_params=payload.query_params,
            query_metadata=payload.query_metadata,
            tags=payload.tags,
            created_by=payload.created_by,
            status="draft",
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)

        # Create initial version history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "query_sql": asset.query_sql,
                "query_params": asset.query_params,
                "query_metadata": asset.query_metadata,
                "name": asset.name,
                "description": asset.description,
            },
        )
        session.add(history)
        session.commit()

        return ResponseEnvelope.success(
            data={
                "asset": _serialize_asset(asset)
            }
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {str(e)}")


@router.get("/assets", response_model=ResponseEnvelope)
def list_assets(asset_type: str | None = None, status: str | None = None):
    with get_session_context() as session:
        q = select(TbAssetRegistry)
        if asset_type:
            q = q.where(TbAssetRegistry.asset_type == asset_type)
        if status:
            q = q.where(TbAssetRegistry.status == status)
        assets = session.exec(q).all()
        return ResponseEnvelope.success(
            data={
                "assets": [
                    {
                        "asset_id": str(a.asset_id),
                        "screen_id": a.screen_id,
                        "asset_type": a.asset_type,
                        "name": a.name,
                        "description": a.description,
                        "version": a.version,
                        "status": a.status,
                        "published_at": a.published_at,
                        "updated_at": a.updated_at,
                    }
                    for a in assets
                ],
                "total": len(assets),
            }
        )


def _serialize_asset(asset: TbAssetRegistry) -> dict[str, Any]:
    return {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "scope": asset.scope,
        "engine": asset.engine,
        "template": asset.template,
        "input_schema": asset.input_schema,
        "output_contract": asset.output_contract,
        "mapping_type": asset.mapping_type,
        "content": asset.content,
        "policy_type": asset.policy_type,
        "limits": asset.limits,
        "query_sql": asset.query_sql,
        "query_params": asset.query_params,
        "query_metadata": asset.query_metadata,
        "screen_id": asset.screen_id,
        "screen_schema": asset.screen_schema,
        "tags": asset.tags,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


def _truncate_question(question: str | None, length: int = 120) -> str:
    if not question:
        return ""
    return question[:length] + "…" if len(question) > length else question


@router.get("/assets/{asset_id}/traces", response_model=ResponseEnvelope)
def list_asset_traces(
    asset_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc

    asset = session.get(TbAssetRegistry, asset_uuid)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")

    traces, total = inspector_crud.list_execution_traces(
        session=session,
        asset_id=str(asset.asset_id),
        limit=limit,
        offset=offset,
    )
    summaries: list[TraceSummary] = []
    for trace in traces:
        summaries.append(
            TraceSummary(
                trace_id=trace.trace_id,
                created_at=trace.created_at,
                feature=trace.feature,
                status=trace.status,
                duration_ms=trace.duration_ms,
                question_snippet=_truncate_question(trace.question),
                applied_asset_versions=trace.asset_versions or [],
            )
        )
    return ResponseEnvelope.success(
        data={
            "traces": [summary.model_dump() for summary in summaries],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


def _to_screen_asset(
    asset: TbAssetRegistry, schema: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "screen_id": asset.screen_id,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "schema_json": schema or asset.screen_schema,
        "tags": asset.tags,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, stage: str | None = None, version: int | None = None):
    with get_session_context() as session:
        if stage:
            stage = stage.lower()
            if stage not in {"draft", "published"}:
                raise HTTPException(
                    status_code=400, detail="stage must be 'draft' or 'published'"
                )
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            asset = None
        if asset and stage and asset.status != stage:
            asset = None

        # If not found by UUID, try to find by screen_id (draft or published)
        if not asset:
            # For screens, optionally restrict to a stage
            def _find_by_stage(stage_status: str) -> TbAssetRegistry | None:
                return session.exec(
                    select(TbAssetRegistry)
                    .where(TbAssetRegistry.asset_type == "screen")
                    .where(TbAssetRegistry.screen_id == asset_id)
                    .where(TbAssetRegistry.status == stage_status)
                ).first()

            if stage == "published":
                asset = _find_by_stage("published")
            elif stage == "draft":
                asset = _find_by_stage("draft")
            else:
                asset = _find_by_stage("draft")
                if not asset:
                    asset = _find_by_stage("published")

        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        if asset.asset_type != "screen":
            return ResponseEnvelope.success(data={"asset": _serialize_asset(asset)})

        if version and version != asset.version:
            hist = session.exec(
                select(TbAssetVersionHistory)
                .where(TbAssetVersionHistory.asset_id == asset.asset_id)
                .where(TbAssetVersionHistory.version == version)
            ).first()
            if not hist:
                raise HTTPException(status_code=404, detail="version not found")
            snapshot = hist.snapshot
            return ResponseEnvelope.success(
                data={"asset": _to_screen_asset(asset, snapshot.get("schema_json"))}
            )

        return ResponseEnvelope.success(data={"asset": _to_screen_asset(asset)})


@router.put("/assets/{asset_id}")
def update_asset(
    asset_id: str,
    payload: Union[
        PromptAssetUpdate,
        ScreenAssetUpdate,
        MappingAssetUpdate,
        PolicyAssetUpdate,
        QueryAssetUpdate,
    ] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    with get_session_context() as session:
        # Try to find by UUID first
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            pass

        # If not found by UUID, try to find by asset_id or screen_id (draft first, then published)
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_id == asset_id)
                .where(TbAssetRegistry.status == "draft")
            ).first()

            if not asset:
                asset = session.exec(
                    select(TbAssetRegistry)
                    .where(TbAssetRegistry.asset_id == asset_id)
                    .where(TbAssetRegistry.status == "published")
                ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        # TODO: Permission check disabled due to missing tb_resource_permission table
        # Will be re-enabled once database migrations are complete

        if asset.status != "draft":
            raise HTTPException(
                status_code=400, detail="only draft assets can be updated"
            )

        if payload.name is not None:
            asset.name = payload.name
        if payload.description is not None:
            asset.description = payload.description
        if payload.tags is not None:
            asset.tags = payload.tags

        # Handle type-specific fields
        if isinstance(payload, PromptAssetUpdate):
            if payload.template is not None:
                asset.template = payload.template
            if payload.input_schema is not None:
                asset.input_schema = payload.input_schema
            if payload.output_contract is not None:
                asset.output_contract = payload.output_contract
        elif isinstance(payload, MappingAssetUpdate):
            if payload.content is not None:
                asset.content = payload.content
        elif isinstance(payload, PolicyAssetUpdate):
            if payload.limits is not None:
                asset.limits = payload.limits
        elif isinstance(payload, QueryAssetUpdate):
            if payload.query_sql is not None:
                asset.query_sql = payload.query_sql
            if payload.query_params is not None:
                asset.query_params = payload.query_params
            if payload.query_metadata is not None:
                asset.query_metadata = payload.query_metadata
        elif isinstance(payload, ScreenAssetUpdate):
            if payload.screen_schema is not None:
                asset.screen_schema = payload.screen_schema

        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()
        session.refresh(asset)

        # Return asset as dict to avoid response validation issues
        asset_dict = {
            "asset_id": str(asset.asset_id),
            "asset_type": asset.asset_type,
            "name": asset.name,
            "description": asset.description,
            "version": asset.version,
            "status": asset.status,
            "template": asset.template,
            "input_schema": asset.input_schema,
            "output_contract": asset.output_contract,
            "content": asset.content,
            "limits": asset.limits,
            "query_sql": asset.query_sql,
            "query_params": asset.query_params,
            "query_metadata": asset.query_metadata,
            "screen_id": asset.screen_id,
            "screen_schema": asset.screen_schema,
            "tags": asset.tags,
            "created_by": asset.created_by,
            "published_by": asset.published_by,
            "published_at": asset.published_at,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
        }

        return ResponseEnvelope.success(data={"asset": asset_dict})


@router.post("/assets/{asset_id}/publish")
def publish_asset(
    asset_id: str,
    body: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    published_by = body.get("published_by") or current_user.id
    with get_session_context() as session:
        # Try to find by UUID first
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            pass

        # If not found by UUID, try to find by screen_id (draft first, then published)
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "screen")
                .where(TbAssetRegistry.screen_id == asset_id)
                .where(TbAssetRegistry.status == "draft")
            ).first()

            if not asset:
                asset = session.exec(
                    select(TbAssetRegistry)
                    .where(TbAssetRegistry.asset_type == "screen")
                    .where(TbAssetRegistry.screen_id == asset_id)
                    .where(TbAssetRegistry.status == "published")
                ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        # TODO: Permission check disabled due to missing tb_resource_permission table
        # Will be re-enabled once database migrations are complete
        # Run validation before publish
        try:
            validate_asset(asset)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(err),
            )
        # increment version and set status
        asset.version = (asset.version or 0) + 1
        asset.status = "published"
        asset.published_by = published_by
        asset.published_at = datetime.now()
        asset.updated_at = datetime.now()
        session.add(asset)
        # snapshot history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "schema_json": asset.screen_schema,
                "name": asset.name,
                "description": asset.description,
            },
            published_by=published_by,
            published_at=asset.published_at,
        )
        session.add(history)
        session.commit()
        session.refresh(asset)
        return ResponseEnvelope.success(
            data={
                "asset": {
                    "asset_id": str(asset.asset_id),
                    "asset_type": asset.asset_type,
                    "name": asset.name,
                    "description": asset.description,
                    "version": asset.version,
                    "status": asset.status,
                    "published_at": asset.published_at,
                    "published_by": asset.published_by,
                    "created_at": asset.created_at,
                    "updated_at": asset.updated_at,
                }
            }
        )


@router.post("/assets/{asset_id}/rollback")
def rollback_asset(
    asset_id: str,
    body: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    target_version = body.get("target_version")
    published_by = body.get("published_by") or current_user.id
    with get_session_context() as session:
        # Try to find by UUID first
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            pass

        # If not found by UUID, try to find by screen_id (draft first, then published)
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "screen")
                .where(TbAssetRegistry.screen_id == asset_id)
                .where(TbAssetRegistry.status == "draft")
            ).first()

            if not asset:
                asset = session.exec(
                    select(TbAssetRegistry)
                    .where(TbAssetRegistry.asset_type == "screen")
                    .where(TbAssetRegistry.screen_id == asset_id)
                    .where(TbAssetRegistry.status == "published")
                ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        # TODO: Permission check disabled due to missing tb_resource_permission table
        # Will be re-enabled once database migrations are complete
        hist = session.exec(
            select(TbAssetVersionHistory)
            .where(TbAssetVersionHistory.asset_id == asset.asset_id)
            .where(TbAssetVersionHistory.version == target_version)
        ).first()
        if not hist:
            raise HTTPException(status_code=404, detail="target version not found")
        # create new published version by copying snapshot
        asset.version = (asset.version or 0) + 1
        asset.screen_schema = hist.snapshot.get("schema_json")
        asset.status = "published"
        asset.published_by = published_by
        asset.published_at = datetime.now()
        session.add(asset)
        # record history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot=hist.snapshot,
            published_by=published_by,
            published_at=asset.published_at,
            rollback_from_version=hist.version,
        )
        session.add(history)
        session.commit()
        session.refresh(asset)
        return ResponseEnvelope.success(
            data={
                "asset": {
                    "asset_id": str(asset.asset_id),
                    "asset_type": asset.asset_type,
                    "name": asset.name,
                    "description": asset.description,
                    "version": asset.version,
                    "status": asset.status,
                    "published_at": asset.published_at,
                    "rollback_from_version": hist.version,
                    "created_at": asset.created_at,
                    "updated_at": asset.updated_at,
                }
            }
        )


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    with get_session_context() as session:
        # Try to find by UUID first
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            pass

        # If not found by UUID, try to find by screen_id (draft first, then published)
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "screen")
                .where(TbAssetRegistry.screen_id == asset_id)
                .where(TbAssetRegistry.status == "draft")
            ).first()

            if not asset:
                asset = session.exec(
                    select(TbAssetRegistry)
                    .where(TbAssetRegistry.asset_type == "screen")
                    .where(TbAssetRegistry.screen_id == asset_id)
                    .where(TbAssetRegistry.status == "published")
                ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        # Permission checks disabled due to missing tb_resource_permission table
        # permission_result = check_permission(
        #     session=session,
        #     user_id=current_user.id,
        #     role=current_user.role,
        #     permission=ResourcePermission.ASSET_DELETE,
        #     resource_type="asset",
        #     resource_id=asset_id,
        # )

        # if not permission_result.granted:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail=f"Permission denied: {permission_result.reason}",
        #     )

        if asset.status != "draft":
            raise HTTPException(
                status_code=400, detail="only draft assets can be deleted"
            )
        session.delete(asset)
        session.commit()
        return {"ok": True}


# Source Asset Endpoints
@router.get("/sources", response_model=ResponseEnvelope)
def list_sources(
    asset_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: TbUser = Depends(get_current_user),
):
    """List source assets"""
    with get_session_context() as session:
        if asset_type and asset_type != "source":
            raise HTTPException(status_code=400, detail="asset_type must be 'source'")

        assets = list_registry_assets(session, asset_type="source", status=status)

        # Convert to response format
        source_assets = []
        for asset in assets:
            content = asset.content or {}
            source_assets.append(
                SourceAssetResponse(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    name=asset.name,
                    description=asset.description,
                    version=asset.version,
                    status=asset.status,
                    source_type=SourceType(content.get("source_type", "postgresql")),
                    connection=content.get("connection", {}),
                    scope=asset.scope,
                    tags=asset.tags,
                    created_by=asset.created_by,
                    published_by=asset.published_by,
                    published_at=asset.published_at,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                )
            )

        return ResponseEnvelope.success(
            data=SourceListResponse(
                assets=source_assets,
                total=len(source_assets),
                page=page,
                page_size=page_size,
            ).model_dump()
        )


@router.post("/sources", response_model=ResponseEnvelope)
def create_source(
    payload: SourceAssetCreate,
    current_user: TbUser = Depends(get_current_user),
):
    """Create a new source asset"""
    with get_session_context() as session:
        asset = create_source_asset(session, payload, created_by=current_user.id)
        return ResponseEnvelope.success(
            data=SourceAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                source_type=asset.source_type,
                connection=asset.connection,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.get("/sources/{asset_id}", response_model=ResponseEnvelope)
def get_source(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Get a source asset by ID"""
    with get_session_context() as session:
        asset = get_source_asset(session, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Source asset not found")

        return ResponseEnvelope.success(
            data=SourceAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                source_type=asset.source_type,
                connection=asset.connection,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.put("/sources/{asset_id}", response_model=ResponseEnvelope)
def update_source(
    asset_id: str,
    payload: SourceAssetUpdate,
    current_user: TbUser = Depends(get_current_user),
):
    """Update a source asset"""
    with get_session_context() as session:
        asset = update_source_asset(
            session, asset_id, payload, updated_by=current_user.id
        )
        return ResponseEnvelope.success(
            data=SourceAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                source_type=asset.source_type,
                connection=asset.connection,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.delete("/sources/{asset_id}")
def delete_source(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Delete a source asset"""
    with get_session_context() as session:
        delete_source_asset(session, asset_id)
        return ResponseEnvelope.success(message="Source asset deleted")


@router.post("/sources/{asset_id}/test", response_model=ResponseEnvelope)
def test_source(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Test source connection"""
    with get_session_context() as session:
        result = test_source_connection(session, asset_id)
        return ResponseEnvelope.success(data=result.model_dump())


# Schema Asset Endpoints
@router.get("/schemas", response_model=ResponseEnvelope)
def list_schemas(
    asset_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: TbUser = Depends(get_current_user),
):
    """List schema assets"""
    with get_session_context() as session:
        if asset_type and asset_type != "schema":
            raise HTTPException(status_code=400, detail="asset_type must be 'schema'")

        assets = list_registry_assets(session, asset_type="schema", status=status)

        # Convert to response format
        schema_assets = []
        for asset in assets:
            schema_assets.append(
                SchemaAssetResponse(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    name=asset.name,
                    description=asset.description,
                    version=asset.version,
                    status=asset.status,
                    catalog=build_schema_catalog(asset),
                    scope=asset.scope,
                    tags=asset.tags,
                    created_by=asset.created_by,
                    published_by=asset.published_by,
                    published_at=asset.published_at,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                )
            )

        return ResponseEnvelope.success(
            data=SchemaListResponse(
                assets=schema_assets,
                total=len(schema_assets),
                page=page,
                page_size=page_size,
            ).model_dump()
        )


@router.post("/schemas", response_model=ResponseEnvelope)
def create_schema(
    payload: SchemaAssetCreate,
    current_user: TbUser = Depends(get_current_user),
):
    """Create a new schema asset"""
    with get_session_context() as session:
        asset = create_schema_asset(session, payload, created_by=current_user.id)
        return ResponseEnvelope.success(
            data=SchemaAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                catalog=asset.catalog,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.get("/schemas/{asset_id}", response_model=ResponseEnvelope)
def get_schema(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Get a schema asset by ID"""
    with get_session_context() as session:
        asset = get_schema_asset(session, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Schema asset not found")

        return ResponseEnvelope.success(
            data=SchemaAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                catalog=asset.catalog,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.put("/schemas/{asset_id}", response_model=ResponseEnvelope)
def update_schema(
    asset_id: str,
    payload: SchemaAssetUpdate,
    current_user: TbUser = Depends(get_current_user),
):
    """Update a schema asset"""
    with get_session_context() as session:
        asset = update_schema_asset(
            session, asset_id, payload, updated_by=current_user.id
        )
        return ResponseEnvelope.success(
            data=SchemaAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                catalog=asset.catalog,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.delete("/schemas/{asset_id}")
def delete_schema(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Delete a schema asset"""
    with get_session_context() as session:
        delete_schema_asset(session, asset_id)
        return ResponseEnvelope.success(message="Schema asset deleted")


@router.post("/schemas/{asset_id}/scan", response_model=ResponseEnvelope)
def scan_schema_endpoint(
    asset_id: str,
    scan_request: ScanRequest,
    current_user: TbUser = Depends(get_current_user),
):
    """Scan schema from source"""
    with get_session_context() as session:
        # Update the scan request with the asset_id
        scan_request.source_ref = asset_id

        result = scan_schema(session, asset_id)
        return ResponseEnvelope.success(data=result.model_dump())


# Resolver Asset Endpoints
@router.get("/resolvers", response_model=ResponseEnvelope)
def list_resolvers(
    asset_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: TbUser = Depends(get_current_user),
):
    """List resolver assets"""
    with get_session_context() as session:
        if asset_type and asset_type != "resolver":
            raise HTTPException(status_code=400, detail="asset_type must be resolver")

        assets = list_registry_assets(session, asset_type="resolver", status=status)

        # Convert to response format
        resolver_assets = []
        for asset in assets:
            content = asset.content or {}
            resolver_assets.append(
                ResolverAssetResponse(
                    asset_id=str(asset.asset_id),
                    asset_type=asset.asset_type,
                    name=asset.name,
                    description=asset.description,
                    version=asset.version,
                    status=asset.status,
                    config=ResolverConfig(
                        name=asset.name,
                        description=asset.description,
                        rules=[],  # Simplified for now
                        default_namespace=content.get("default_namespace"),
                        tags=asset.tags,
                        version=asset.version,
                    ),
                    scope=asset.scope,
                    tags=asset.tags,
                    created_by=asset.created_by,
                    published_by=asset.published_by,
                    published_at=asset.published_at,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                )
            )

        return ResponseEnvelope.success(
            data={
                "assets": resolver_assets,
                "total": len(resolver_assets),
                "page": page,
                "page_size": page_size,
            }
        )


@router.post("/resolvers", response_model=ResponseEnvelope)
def create_resolver(
    payload: ResolverAssetCreate,
    current_user: TbUser = Depends(get_current_user),
):
    """Create a new resolver asset"""
    with get_session_context() as session:
        asset = create_resolver_asset(session, payload, created_by=current_user.id)
        return ResponseEnvelope.success(
            data=ResolverAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                config=asset.config,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.get("/resolvers/{asset_id}", response_model=ResponseEnvelope)
def get_resolver(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Get a resolver asset by ID"""
    with get_session_context() as session:
        asset = get_resolver_asset(session, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Resolver asset not found")

        return ResponseEnvelope.success(
            data=ResolverAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                config=asset.config,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.put("/resolvers/{asset_id}", response_model=ResponseEnvelope)
def update_resolver(
    asset_id: str,
    payload: ResolverAssetUpdate,
    current_user: TbUser = Depends(get_current_user),
):
    """Update a resolver asset"""
    with get_session_context() as session:
        asset = update_resolver_asset(
            session, asset_id, payload, updated_by=current_user.id
        )
        return ResponseEnvelope.success(
            data=ResolverAssetResponse(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                name=asset.name,
                description=asset.description,
                version=asset.version,
                status=asset.status,
                config=asset.config,
                scope=asset.scope,
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
        )


@router.delete("/resolvers/{asset_id}")
def delete_resolver(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Delete a resolver asset"""
    with get_session_context() as session:
        delete_resolver_asset(session, asset_id)
        return ResponseEnvelope.success(message="Resolver asset deleted")


@router.post("/resolvers/{asset_id}/simulate", response_model=ResponseEnvelope)
def simulate_resolver(
    asset_id: str,
    test_entities: List[str] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    """Simulate resolver configuration"""
    with get_session_context() as session:
        result = simulate_resolver_configuration(session, asset_id, test_entities)
        return ResponseEnvelope.success(data=result)
