from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from core.db import get_session
from schemas.common import ResponseEnvelope
from .crud import (
    list_assets,
    get_asset,
    create_asset,
    update_asset,
    publish_asset,
    rollback_asset,
)
from .schemas import (
    AssetCreate,
    AssetRead,
    AssetUpdate,
    AssetPublishRequest,
    AssetType,
)

router = APIRouter(prefix="/asset-registry", tags=["asset-registry"])


@router.get("/assets")
def list_assets_endpoint(
    asset_type: AssetType | None = Query(None),
    status: str | None = Query(None),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """List assets with optional filters"""
    items = list_assets(session, asset_type=asset_type, status=status)
    payload = [AssetRead.model_validate(item).model_dump() for item in items]
    return ResponseEnvelope.success(data={"assets": payload})


@router.get("/assets/{asset_id}")
def get_asset_endpoint(
    asset_id: str, session: Session = Depends(get_session)
) -> ResponseEnvelope:
    """Get single asset by ID"""
    asset = get_asset(session, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return ResponseEnvelope.success(data={"asset": AssetRead.model_validate(asset).model_dump()})


@router.post("/assets")
def create_asset_endpoint(
    payload: AssetCreate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Create new asset in draft status"""
    try:
        created = create_asset(
            session,
            name=payload.name,
            asset_type=payload.asset_type,
            description=payload.description,
            scope=payload.scope,
            engine=payload.engine,
            template=payload.template,
            input_schema=payload.input_schema,
            output_contract=payload.output_contract,
            mapping_type=payload.mapping_type,
            content=payload.content,
            policy_type=payload.policy_type,
            limits=payload.limits,
            created_by=payload.created_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseEnvelope.success(data={"asset": AssetRead.model_validate(created).model_dump()})


@router.put("/assets/{asset_id}")
def update_asset_endpoint(
    asset_id: str,
    payload: AssetUpdate,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Update draft asset"""
    asset = get_asset(session, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.status == "published":
        raise HTTPException(
            status_code=400,
            detail="Cannot update published asset. Create new draft first.",
        )

    try:
        updates = payload.model_dump(exclude_none=True)
        updated = update_asset(session, asset, updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseEnvelope.success(data={"asset": AssetRead.model_validate(updated).model_dump()})


@router.post("/assets/{asset_id}/publish")
def publish_asset_endpoint(
    asset_id: str,
    payload: AssetPublishRequest,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Publish draft asset"""
    asset = get_asset(session, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        published = publish_asset(session, asset, published_by=payload.published_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseEnvelope.success(data={"asset": AssetRead.model_validate(published).model_dump()})


@router.post("/assets/{asset_id}/rollback")
def rollback_asset_endpoint(
    asset_id: str,
    to_version: int = Query(..., ge=1),
    executed_by: str = Query("system"),
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """Rollback published asset to previous version"""
    try:
        rolled_back = rollback_asset(session, asset_id, to_version, executed_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ResponseEnvelope.success(data={"asset": AssetRead.model_validate(rolled_back).model_dump()})
