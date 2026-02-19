from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, List

from core.auth import get_current_user
from core.db import get_session, get_session_context
from core.tenant import get_current_tenant
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from schemas.common import ResponseEnvelope
from sqlalchemy.exc import StatementError
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

from app.modules.asset_registry.crud import (
    build_schema_catalog,
    create_resolver_asset,
    create_schema_asset,
    create_source_asset,
    create_tool_asset,
    delete_resolver_asset,
    delete_schema_asset,
    delete_source_asset,
    get_resolver_asset,
    get_schema_asset,
    get_source_asset,
    simulate_resolver_configuration,
    test_source_connection,
    update_resolver_asset,
    update_schema_asset,
    update_source_asset,
)
from app.modules.asset_registry.crud import (
    list_assets as list_registry_assets,
)
from app.modules.asset_registry.crud import (
    unpublish_asset as unpublish_registry_asset,
)
from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.asset_registry.resolver_models import (
    ResolverAssetCreate,
    ResolverAssetResponse,
    ResolverAssetUpdate,
    ResolverConfig,
)
from app.modules.asset_registry.schema_models import (
    CatalogScanRequest,
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
    coerce_source_connection,
    coerce_source_type,
)
from app.modules.auth.models import TbUser
from app.modules.inspector import crud as inspector_crud
from app.modules.inspector.schemas import TraceSummary
from app.modules.permissions.crud import check_permission
from app.modules.permissions.models import ResourcePermission

from .validators import validate_asset

router = APIRouter(prefix="/asset-registry")


from typing import Union


@router.post("/assets", response_model=ResponseEnvelope)
def create_asset(
    payload: Union[PromptAssetCreate, ScreenAssetCreate, QueryAssetCreate],
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    if isinstance(payload, ScreenAssetCreate):
        return create_screen_asset_impl(payload, session, current_user, tenant_id)
    elif isinstance(payload, PromptAssetCreate):
        return create_prompt_asset_impl(payload, session, current_user, tenant_id)
    elif isinstance(payload, QueryAssetCreate):
        return create_query_asset_impl(payload, session, current_user, tenant_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid asset type")


def create_screen_asset_impl(
    payload: ScreenAssetCreate, session: Session, current_user: TbUser, tenant_id: str
):
    if payload.asset_type != "screen":
        raise HTTPException(status_code=400, detail="asset_type must be 'screen'")

    # Check permission
    try:
        permission_result = check_permission(
            session=session,
            user_id=current_user.id,
            role=current_user.role,
            permission=ResourcePermission.SCREEN_CREATE,
            resource_type="screen",
            resource_id=None,
        )
        if not permission_result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_result.reason}",
            )
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        from app.modules.auth.models import UserRole
        if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER, UserRole.DEVELOPER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: insufficient role",
            )

    try:
        asset = TbAssetRegistry(
            asset_type="screen",
            screen_id=payload.screen_id,
            name=payload.name,
            description=payload.description,
            schema_json=payload.screen_schema,
            tags=payload.tags,
            created_by=payload.created_by,
            tenant_id=tenant_id,
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
                "schema_json": asset.schema_json,
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
                    screen_schema=asset.schema_json,
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
    payload: PromptAssetCreate, session: Session, current_user: TbUser, tenant_id: str
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
            tenant_id=tenant_id,
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
    payload: QueryAssetCreate, session: Session, current_user: TbUser, tenant_id: str
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
            tenant_id=tenant_id,
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
def list_assets(
    asset_type: str | None = None,
    status: str | None = None,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    with get_session_context() as session:
        q = select(TbAssetRegistry)
        # Tenant isolation - filter by tenant_id OR global/system assets
        if tenant_id:
            q = q.where(
                (TbAssetRegistry.tenant_id == tenant_id)
                | (TbAssetRegistry.tenant_id == "")
                | (TbAssetRegistry.tenant_id == "system")
                | (TbAssetRegistry.tenant_id == "default")
                | (TbAssetRegistry.tenant_id.is_(None))
            )
        if asset_type:
            q = q.where(TbAssetRegistry.asset_type == asset_type)
        if status:
            q = q.where(TbAssetRegistry.status == status)
        assets = session.exec(q).all()
        return ResponseEnvelope.success(
            data={
                "assets": [_serialize_asset(a) for a in assets],
                "total": len(assets),
            }
        )


def _serialize_asset(asset: TbAssetRegistry) -> dict[str, Any]:
    content = asset.content or {}
    result = {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "is_system": bool(asset.is_system),
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
        "schema_json": asset.schema_json,
        "tags": asset.tags,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }

    # Add type-specific fields for Source, Catalog, Resolver assets
    if asset.asset_type == "source":
        result["source_type"] = content.get("source_type")
        result["connection"] = content.get("connection", {})
    elif asset.asset_type == "catalog":
        result["catalog"] = content.get("catalog", {})
    elif asset.asset_type == "resolver":
        # Build config with properly parsed rules
        from .resolver_models import (
            AliasMapping,
            PatternRule,
            TransformationRule,
        )

        rules_data = content.get("rules", [])
        rules = []
        for rule_data in rules_data:
            rule_type = rule_data.get("rule_type", "alias_mapping")
            # Extract the actual rule-specific data (nested in "rule_data" key)
            inner_rule_data = rule_data.get("rule_data", rule_data)

            if rule_type == "alias_mapping":
                rule_data_obj = AliasMapping(**inner_rule_data).model_dump()
            elif rule_type == "pattern_rule":
                rule_data_obj = PatternRule(**inner_rule_data).model_dump()
            elif rule_type == "transformation":
                rule_data_obj = TransformationRule(**inner_rule_data).model_dump()
            else:
                rule_data_obj = rule_data

            rules.append({
                "rule_type": rule_type,
                "name": rule_data.get("name", ""),
                "description": rule_data.get("description"),
                "is_active": rule_data.get("is_active", True),
                "priority": rule_data.get("priority", 0),
                "extra_metadata": rule_data.get("extra_metadata", {}),
                "rule_data": rule_data_obj,
            })

        result["config"] = {
            "name": asset.name,
            "description": asset.description,
            "rules": rules,
            "default_namespace": content.get("default_namespace"),
            "tags": asset.tags,
            "version": asset.version,
        }

    return result


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
        "schema_json": schema or asset.schema_json,
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
            logger.debug("Invalid UUID format for asset_id, falling back to name/ID lookup")
            asset = None

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

        # Permission check for screen assets
        if asset.asset_type == "screen":
            try:
                permission_result = check_permission(
                    session=session,
                    user_id=current_user.id,
                    role=current_user.role,
                    permission=ResourcePermission.SCREEN_EDIT,
                    resource_type="screen",
                    resource_id=str(asset.asset_id),
                )
                if not permission_result.granted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission_result.reason}",
                    )
            except HTTPException:
                raise
            except Exception:
                session.rollback()
                from app.modules.auth.models import UserRole
                if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Permission check unavailable; admin role required",
                    )
                asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
                if not asset:
                    raise HTTPException(status_code=404, detail="asset not found")

        if asset.status != "draft":
            raise HTTPException(
                status_code=400, detail="only draft assets can be updated"
            )

        if not payload.force and payload.expected_updated_at is not None:
            expected = payload.expected_updated_at
            current = asset.updated_at
            # optimistic concurrency guard for collaborative editing
            if current and expected != current:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "asset has been modified by another session",
                        "expected_updated_at": expected.isoformat(),
                        "current_updated_at": current.isoformat(),
                        "asset_id": str(asset.asset_id),
                    },
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
                # Basic schema validation
                schema = payload.screen_schema
                if not isinstance(schema, dict):
                    raise HTTPException(status_code=400, detail="screen_schema must be a dict")
                if "screen_id" not in schema:
                    raise HTTPException(status_code=400, detail="screen_schema.screen_id is required")
                if "components" not in schema:
                    raise HTTPException(status_code=400, detail="screen_schema.components is required")
                if not isinstance(schema.get("components"), list):
                    raise HTTPException(status_code=400, detail="screen_schema.components must be an array")
                asset.schema_json = payload.screen_schema

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
            "screen_schema": asset.schema_json,
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
            logger.debug("Invalid UUID format for asset_id, falling back to name/ID lookup")
            asset = None

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

        # Permission check for screen publish
        if asset.asset_type == "screen":
            try:
                permission_result = check_permission(
                    session=session,
                    user_id=current_user.id,
                    role=current_user.role,
                    permission=ResourcePermission.SCREEN_PUBLISH,
                    resource_type="screen",
                    resource_id=str(asset.asset_id),
                )
                if not permission_result.granted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission_result.reason}",
                    )
            except HTTPException:
                raise
            except Exception:
                session.rollback()
                from app.modules.auth.models import UserRole
                if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Permission denied: insufficient role",
                    )
                # Re-fetch asset after rollback
                asset = session.get(TbAssetRegistry, uuid.UUID(asset_id)) if asset_id else None
                if not asset:
                    raise HTTPException(status_code=404, detail="asset not found")

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
                "schema_json": asset.schema_json,
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
            logger.debug("Invalid UUID format for asset_id, falling back to name/ID lookup")
            asset = None

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

        # Permission check for screen rollback
        if asset.asset_type == "screen":
            permission_result = check_permission(
                session=session,
                user_id=current_user.id,
                role=current_user.role,
                permission=ResourcePermission.SCREEN_ROLLBACK,
                resource_type="screen",
                resource_id=str(asset.asset_id),
            )
            if not permission_result.granted:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission_result.reason}",
                )

        hist = session.exec(
            select(TbAssetVersionHistory)
            .where(TbAssetVersionHistory.asset_id == asset.asset_id)
            .where(TbAssetVersionHistory.version == target_version)
        ).first()
        if not hist:
            raise HTTPException(status_code=404, detail="target version not found")
        # create new published version by copying snapshot
        asset.version = (asset.version or 0) + 1
        asset.schema_json = hist.snapshot.get("schema_json")
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


@router.post("/assets/{asset_id}/unpublish")
def unpublish_asset(
    asset_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    current_user: TbUser = Depends(get_current_user),
):
    executed_by = body.get("published_by") or body.get("executed_by") or current_user.id
    with get_session_context() as session:
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            pass

        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "screen")
                .where(TbAssetRegistry.screen_id == asset_id)
                .where(TbAssetRegistry.status == "published")
            ).first()

        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        try:
            asset = unpublish_registry_asset(
                session=session,
                asset=asset,
                executed_by=str(executed_by),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return ResponseEnvelope.success(
            data={
                "asset": {
                    "asset_id": str(asset.asset_id),
                    "asset_type": asset.asset_type,
                    "name": asset.name,
                    "description": asset.description,
                    "version": asset.version,
                    "status": asset.status,
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
            logger.debug("Invalid UUID format for asset_id, falling back to name/ID lookup")
            asset = None

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

        # Permission check for screen delete
        if asset.asset_type == "screen":
            try:
                permission_result = check_permission(
                    session=session,
                    user_id=current_user.id,
                    role=current_user.role,
                    permission=ResourcePermission.SCREEN_DELETE,
                    resource_type="screen",
                    resource_id=str(asset.asset_id),
                )
                if not permission_result.granted:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission_result.reason}",
                    )
            except HTTPException:
                raise
            except Exception:
                # Permission table may not exist yet; rollback and fall back to role check
                session.rollback()
                from app.modules.auth.models import UserRole
                if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Permission denied: insufficient role",
                    )
                # Re-fetch the asset after rollback
                asset = session.get(TbAssetRegistry, uuid.UUID(asset_id)) if asset_id else None
                if not asset:
                    raise HTTPException(status_code=404, detail="asset not found")

        if asset.status != "draft":
            raise HTTPException(
                status_code=400, detail="only draft assets can be deleted"
            )

        try:
            # Delete version history first
            histories = session.exec(
                select(TbAssetVersionHistory).where(TbAssetVersionHistory.asset_id == asset.asset_id)
            ).all()
            for history in histories:
                session.delete(history)

            # Delete the asset
            session.delete(asset)
            session.commit()
            return ResponseEnvelope.success(data={"ok": True})
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete asset: {str(e)}"
            )


# Source Asset Endpoints
@router.get("/sources", response_model=ResponseEnvelope)
def list_sources(
    asset_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """List source assets"""
    with get_session_context() as session:
        if asset_type and asset_type != "source":
            raise HTTPException(status_code=400, detail="asset_type must be 'source'")

        assets = list_registry_assets(session, asset_type="source", status=status, tenant_id=tenant_id)

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
                    source_type=coerce_source_type(content.get("source_type", "postgresql")),
                    connection=coerce_source_connection(content.get("connection", {})),
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
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new source asset"""
    with get_session_context() as session:
        asset = create_source_asset(
            session, payload, tenant_id=tenant_id, created_by=current_user.id
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
        try:
            asset = update_source_asset(
                session, asset_id, payload, updated_by=current_user.id
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
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


# Catalog Asset Endpoints
@router.get("/catalogs", response_model=ResponseEnvelope)
def list_catalogs(
    asset_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """List catalog assets (database schema catalogs)"""
    with get_session_context() as session:
        if asset_type and asset_type != "catalog":
            raise HTTPException(status_code=400, detail="asset_type must be 'catalog'")

        assets = list_registry_assets(session, asset_type="catalog", status=status, tenant_id=tenant_id)

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


@router.post("/catalogs", response_model=ResponseEnvelope)
def create_catalog(
    payload: SchemaAssetCreate,
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new catalog asset (database schema catalog)"""
    with get_session_context() as session:
        asset = create_schema_asset(
            session, payload, tenant_id=tenant_id, created_by=current_user.id
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


@router.get("/catalogs/{asset_id}", response_model=ResponseEnvelope)
def get_catalog(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Get a catalog asset by ID"""
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


@router.put("/catalogs/{asset_id}", response_model=ResponseEnvelope)
def update_catalog(
    asset_id: str,
    payload: SchemaAssetUpdate,
    current_user: TbUser = Depends(get_current_user),
):
    """Update a catalog asset"""
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


@router.delete("/catalogs/{asset_id}")
def delete_catalog(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Delete a catalog asset"""
    with get_session_context() as session:
        delete_schema_asset(session, asset_id)
        return ResponseEnvelope.success(message="Schema asset deleted")


@router.post("/catalogs/{asset_id}/scan", response_model=ResponseEnvelope)
async def scan_catalog_endpoint(
    asset_id: str,
    payload: CatalogScanRequest = Body(default_factory=CatalogScanRequest),
    current_user: TbUser = Depends(get_current_user),
):
    """
    Scan database schema and populate catalog asset metadata.

    Args:
        asset_id: Catalog asset ID
        payload: Scan options for schema discovery
    """
    import logging

    from app.modules.asset_registry.crud import scan_schema_asset

    logger = logging.getLogger(__name__)

    with get_session_context() as session:
        try:
            asset = session.get(TbAssetRegistry, asset_id)
        except (ValueError, TypeError, StatementError):
            raise HTTPException(status_code=400, detail="Invalid catalog asset_id format")

        if not asset:
            raise HTTPException(status_code=404, detail="Catalog asset not found")

        if asset.asset_type != "catalog":
            raise HTTPException(status_code=400, detail="Asset is not a catalog asset")

        try:
            updated_asset = await scan_schema_asset(
                session,
                asset,
                schema_names=payload.schema_names or None,
                include_row_counts=payload.include_row_counts,
            )

            # Return updated asset
            return ResponseEnvelope.success(
                data={
                    "asset_id": str(updated_asset.asset_id),
                    "name": updated_asset.name,
                    "status": updated_asset.status,
                    "content": updated_asset.content,
                    "message": "Schema scan completed successfully",
                }
            )
        except Exception as e:
            logger.error(f"Schema scan failed for {asset_id}: {e}")
            return ResponseEnvelope.error(
                message=f"Schema scan failed: {str(e)}",
                data=None,
            )


@router.post("/catalogs/{asset_id}/tables/{table_name}/toggle", response_model=ResponseEnvelope)
def toggle_table_enabled(
    asset_id: str,
    table_name: str,
    enabled: bool,
    current_user: TbUser = Depends(get_current_user),
):
    """Toggle whether a table is enabled for Tool usage"""
    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, asset_id)

        if not asset or asset.asset_type != "catalog":
            raise HTTPException(status_code=404, detail="Schema asset not found")

        content = asset.content or {}
        catalog = content.get("catalog", {})
        tables = catalog.get("tables", [])

        # Find and update table
        found = False
        for table in tables:
            if table.get("name") == table_name:
                table["enabled"] = enabled
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Save changes
        catalog["tables"] = tables
        content["catalog"] = catalog
        asset.content = content
        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()

        return ResponseEnvelope.success(
            data={
                "table_name": table_name,
                "enabled": enabled,
                "message": f"Table '{table_name}' {'enabled' if enabled else 'disabled'}",
            }
        )


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

            # Build rules from content
            rules_data = content.get("rules", [])
            rules = []
            for rule_data in rules_data:
                from .resolver_models import (
                    AliasMapping,
                    PatternRule,
                    ResolverRule,
                    ResolverType,
                    TransformationRule,
                )

                rule_type = rule_data.get("rule_type", "alias_mapping")

                # Extract the rule-specific nested payload only.
                inner_rule_data = rule_data.get("rule_data")
                if not isinstance(inner_rule_data, dict):
                    inner_rule_data = {}

                if rule_type == "alias_mapping":
                    rule_data_obj = AliasMapping(**inner_rule_data)
                elif rule_type == "pattern_rule":
                    rule_data_obj = PatternRule(**inner_rule_data)
                elif rule_type == "transformation":
                    rule_data_obj = TransformationRule(**inner_rule_data)
                else:
                    rule_data_obj = rule_data

                rule = ResolverRule(
                    rule_type=ResolverType(rule_type),
                    name=rule_data.get("name", ""),
                    description=rule_data.get("description"),
                    is_active=rule_data.get("is_active", True),
                    priority=rule_data.get("priority", 0),
                    extra_metadata=rule_data.get("extra_metadata", {}),
                    rule_data=rule_data_obj,
                )
                rules.append(rule)

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
                        rules=rules,
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
    tenant_id: str = Depends(get_current_tenant),
):
    """Create a new resolver asset"""
    with get_session_context() as session:
        asset = create_resolver_asset(
            session, payload, tenant_id=tenant_id, created_by=current_user.id
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


# ============= Tools Endpoints =============

@router.get("/tools", response_model=ResponseEnvelope)
def list_tools(
    status: str | None = Query(None),
    tool_type: str | None = Query(None),
    current_user: TbUser = Depends(get_current_user),
):
    """List tools with optional filtering by status or tool type"""
    # BLOCKER-1: Tool 접근 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 목록 조회 권한이 없습니다 (Admin/Manager만 가능)",
        )

    with get_session_context() as session:
        query = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")

        if status:
            query = query.where(TbAssetRegistry.status == status)
        if tool_type:
            query = query.where(TbAssetRegistry.tool_type == tool_type)

        tools = session.exec(query).all()
        return ResponseEnvelope.success(
            data={
                "assets": [_to_tool_dict(t) for t in tools],
                "total": len(tools),
                "page": 1,
                "page_size": len(tools),
            }
        )


@router.post("/tools", response_model=ResponseEnvelope)
def create_tool(
    payload: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create new tool asset"""
    # BLOCKER-1: Tool 생성 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 생성 권한이 없습니다 (Admin/Manager만 가능)",
        )

    # BLOCKER-2: Credential validation - prevent plaintext storage
    from app.modules.asset_registry.credential_manager import (
        validate_tool_config_credentials,
    )
    tool_config = payload.get("tool_config", {})
    credential_errors = validate_tool_config_credentials(tool_config)
    if credential_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool configuration contains plaintext credentials: {'; '.join(credential_errors)}",
        )

    with get_session_context() as session:
        asset = create_tool_asset(
            session,
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            tool_type=payload.get("tool_type", "database_query"),
            tool_config=tool_config,
            tool_input_schema=payload.get("tool_input_schema", {}),
            tool_output_schema=payload.get("tool_output_schema"),
            tool_catalog_ref=payload.get("tool_catalog_ref"),
            tags=payload.get("tags"),
            tenant_id=tenant_id,
            created_by=current_user.id if current_user else "admin",
        )

        # BLOCKER-3: Tool Asset validation
        from app.modules.asset_registry.tool_validator import validate_tool_asset
        validation_errors = validate_tool_asset(asset)
        if validation_errors:
            # Delete the asset since it failed validation
            session.delete(asset)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool validation failed: {'; '.join(validation_errors)}",
            )

        session.refresh(asset)
        return ResponseEnvelope.success(
            data={"asset": _to_tool_dict(asset)},
            message="Tool asset created successfully",
        )


@router.get("/tools/{asset_id}", response_model=ResponseEnvelope)
def get_tool(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Get tool asset by ID"""
    # BLOCKER-1: Tool 조회 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 조회 권한이 없습니다 (Admin/Manager만 가능)",
        )

    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
        if not asset or asset.asset_type != "tool":
            raise HTTPException(status_code=404, detail="Tool not found")

        return ResponseEnvelope.success(data=_to_tool_dict(asset))


@router.put("/tools/{asset_id}", response_model=ResponseEnvelope)
def update_tool(
    asset_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    """Update tool asset"""
    # BLOCKER-1: Tool 수정 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 수정 권한이 없습니다 (Admin/Manager만 가능)",
        )

    # BLOCKER-2: Credential validation - prevent plaintext storage
    from app.modules.asset_registry.credential_manager import (
        validate_tool_config_credentials,
    )
    if "tool_config" in payload:
        credential_errors = validate_tool_config_credentials(payload.get("tool_config"))
        if credential_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool configuration contains plaintext credentials: {'; '.join(credential_errors)}",
            )

    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
        if not asset or asset.asset_type != "tool":
            raise HTTPException(status_code=404, detail="Tool not found")

        # Only allow updates if in draft status
        if asset.status != "draft":
            raise HTTPException(status_code=400, detail="Can only update draft tools")

        if "name" in payload:
            asset.name = payload["name"]
        if "description" in payload:
            asset.description = payload["description"]
        if "tool_type" in payload:
            asset.tool_type = payload["tool_type"]
        if "tool_catalog_ref" in payload:
            asset.tool_catalog_ref = payload["tool_catalog_ref"]
        if "tool_config" in payload:
            asset.tool_config = payload["tool_config"]
        if "tool_input_schema" in payload:
            asset.tool_input_schema = payload["tool_input_schema"]
        if "tool_output_schema" in payload:
            asset.tool_output_schema = payload["tool_output_schema"]
        if "tags" in payload:
            asset.tags = payload["tags"]

        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()
        session.refresh(asset)

        return ResponseEnvelope.success(
            data=_to_tool_dict(asset),
            message="Tool asset updated successfully",
        )


@router.delete("/tools/{asset_id}")
def delete_tool(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Delete tool asset"""
    # BLOCKER-1: Tool 삭제 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 삭제 권한이 없습니다 (Admin/Manager만 가능)",
        )

    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
        if not asset or asset.asset_type != "tool":
            raise HTTPException(status_code=404, detail="Tool not found")

        session.delete(asset)
        session.commit()

        return ResponseEnvelope.success(message="Tool asset deleted successfully")


@router.post("/tools/{asset_id}/publish", response_model=ResponseEnvelope)
def publish_tool(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Publish tool asset"""
    # BLOCKER-1: Tool 발행 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 발행 권한이 없습니다 (Admin/Manager만 가능)",
        )

    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
        if not asset or asset.asset_type != "tool":
            raise HTTPException(status_code=404, detail="Tool not found")

        # BLOCKER-3: Enhanced validation for publication
        from app.modules.asset_registry.tool_validator import (
            validate_tool_for_publication,
        )
        publication_errors = validate_tool_for_publication(asset)
        if publication_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool publication validation failed: {'; '.join(publication_errors)}",
            )

        asset.status = "published"
        asset.published_by = current_user.id if current_user else "admin"
        asset.published_at = datetime.now()
        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()
        session.refresh(asset)

        return ResponseEnvelope.success(
            data=_to_tool_dict(asset),
            message="Tool asset published successfully",
        )


@router.post("/tools/{asset_id}/unpublish", response_model=ResponseEnvelope)
def unpublish_tool(
    asset_id: str,
    current_user: TbUser = Depends(get_current_user),
):
    """Unpublish tool asset (rollback published tool to draft)."""
    from app.modules.auth.models import UserRole

    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 언발행 권한이 없습니다 (Admin/Manager만 가능)",
        )

    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
        if not asset or asset.asset_type != "tool":
            raise HTTPException(status_code=404, detail="Tool not found")

        if asset.status != "published":
            raise HTTPException(
                status_code=400,
                detail="Only published tools can be unpublished",
            )

        asset.status = "draft"
        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()
        session.refresh(asset)

        return ResponseEnvelope.success(
            data=_to_tool_dict(asset),
            message="Tool asset unpublished successfully",
        )


@router.post("/tools/{asset_id}/test", response_model=ResponseEnvelope)
def test_tool(
    asset_id: str,
    payload: dict[str, Any] = Body(...),
    current_user: TbUser = Depends(get_current_user),
):
    """Test tool execution with given input"""
    # BLOCKER-1: Tool 테스트 권한 체크
    from app.modules.auth.models import UserRole
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tool 테스트 권한이 없습니다 (Admin/Manager만 가능)",
        )

    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
        if not asset or asset.asset_type != "tool":
            raise HTTPException(status_code=404, detail="Tool not found")

        # For now, return success with echo of input
        # In production, this would actually execute the tool
        return ResponseEnvelope.success(
            data={
                "success": True,
                "data": payload,
                "error": None,
                "error_details": None,
            }
        )


def _to_tool_dict(asset: TbAssetRegistry) -> dict[str, Any]:
    """Convert tool asset to dict"""
    return {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "tool_type": getattr(asset, "tool_type", None),
        "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
        "tool_config": getattr(asset, "tool_config", None),
        "tool_input_schema": getattr(asset, "tool_input_schema", None),
        "tool_output_schema": getattr(asset, "tool_output_schema", None),
        "tags": asset.tags,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at.isoformat() if asset.published_at else None,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }
