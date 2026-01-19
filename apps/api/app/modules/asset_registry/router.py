from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Body, Depends, status
from sqlmodel import Session, select

from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.asset_registry.schemas import (
    ScreenAssetCreate,
    ScreenAssetRead,
    ScreenAssetUpdate,
)
from app.modules.auth.models import TbUser
# Permission checks disabled due to missing tb_resource_permission table
# from app.modules.permissions.models import ResourcePermission
# from app.modules.permissions.crud import check_permission
from core.db import get_session_context, get_session
from core.auth import get_current_user
from schemas.common import ResponseEnvelope

router = APIRouter(prefix="/asset-registry")


@router.post("/assets", response_model=ScreenAssetRead)
def create_screen_asset(
    payload: ScreenAssetCreate,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
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

        return ScreenAssetRead(
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
                        "version": a.version,
                        "status": a.status,
                        "published_at": a.published_at,
                    } for a in assets
                ],
                "total": len(assets)
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


def _to_screen_asset(asset: TbAssetRegistry, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "asset_id": str(asset.asset_id),
        "asset_type": asset.asset_type,
        "screen_id": asset.screen_id,
        "name": asset.name,
        "description": asset.description,
        "version": asset.version,
        "status": asset.status,
        "screen_schema": schema or asset.screen_schema,
        "tags": asset.tags,
        "created_by": asset.created_by,
        "published_by": asset.published_by,
        "published_at": asset.published_at,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, version: int | None = None):
    with get_session_context() as session:
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            asset = None

        # If not found by UUID, try to find by screen_id (draft or published)
        if not asset:
            # For screens, try to find draft first, then published
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

        if asset.asset_type != "screen":
            return ResponseEnvelope.success(data={"asset": _serialize_asset(asset)})

        if not asset.screen_id or asset.screen_schema is None:
            raise HTTPException(status_code=404, detail="screen asset is not available")

        if version and version != asset.version:
            hist = session.exec(
                select(TbAssetVersionHistory)
                .where(TbAssetVersionHistory.asset_id == asset.asset_id)
                .where(TbAssetVersionHistory.version == version)
            ).first()
            if not hist:
                raise HTTPException(status_code=404, detail="version not found")
            snapshot = hist.snapshot
            return ResponseEnvelope.success(data={"asset": _to_screen_asset(asset, snapshot.get("schema_json"))})

        return ResponseEnvelope.success(data={"asset": _to_screen_asset(asset)})


@router.put("/assets/{asset_id}", response_model=ScreenAssetRead)
def update_asset(
    asset_id: str,
    payload: ScreenAssetUpdate,
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

        # TODO: Permission check disabled due to missing tb_resource_permission table
        # Will be re-enabled once database migrations are complete

        if asset.status != "draft":
            raise HTTPException(status_code=400, detail="only draft assets can be updated")
        if payload.name is not None:
            asset.name = payload.name
        if payload.description is not None:
            asset.description = payload.description
        if payload.screen_schema is not None:
            asset.screen_schema = payload.screen_schema
        if payload.tags is not None:
            asset.tags = payload.tags
        asset.updated_at = datetime.now()
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return ScreenAssetRead(
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
        return {
            "asset_id": str(asset.asset_id),
            "version": asset.version,
            "status": asset.status,
            "published_at": asset.published_at,
            "published_by": asset.published_by,
        }


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
        return {
            "asset_id": str(asset.asset_id),
            "version": asset.version,
            "status": asset.status,
            "published_at": asset.published_at,
            "rollback_from_version": hist.version,
        }


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

        # Check permission
        permission_result = check_permission(
            session=session,
            user_id=current_user.id,
            role=current_user.role,
            permission=ResourcePermission.ASSET_DELETE,
            resource_type="asset",
            resource_id=asset_id,
        )

        if not permission_result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_result.reason}",
            )

        if asset.status != "draft":
            raise HTTPException(status_code=400, detail="only draft assets can be deleted")
        session.delete(asset)
        session.commit()
        return {"ok": True}
