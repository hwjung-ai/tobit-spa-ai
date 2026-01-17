from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Body
from sqlmodel import Session, select

from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from app.modules.asset_registry.schemas import (
    ScreenAssetCreate,
    ScreenAssetRead,
    ScreenAssetUpdate,
)
from core.db import get_session_context
from schemas.common import ResponseEnvelope

router = APIRouter(prefix="/asset-registry")


@router.post("/assets", response_model=ScreenAssetRead)
def create_screen_asset(payload: ScreenAssetCreate):
    if payload.asset_type != "screen":
        raise HTTPException(status_code=400, detail="asset_type must be 'screen'")

    with get_session_context() as session:
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


@router.get("/assets", response_model=ResponseEnvelope)
def list_assets(asset_type: str | None = None):
    with get_session_context() as session:
        q = select(TbAssetRegistry)
        if asset_type:
            q = q.where(TbAssetRegistry.asset_type == asset_type)
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


@router.get("/assets/{asset_id}", response_model=ScreenAssetRead)
def get_asset(asset_id: str, version: int | None = None):
    with get_session_context() as session:
        asset = None
        try:
            asset_uuid = uuid.UUID(asset_id)
            asset = session.get(TbAssetRegistry, asset_uuid)
        except ValueError:
            asset = None
        if not asset:
            asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "screen")
                .where(TbAssetRegistry.screen_id == asset_id)
                .where(TbAssetRegistry.status == "published")
            ).first()
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")

        if version and version != asset.version:
            # fetch from history
            hist = session.exec(
                select(TbAssetVersionHistory).where(
                    TbAssetVersionHistory.asset_id == asset.asset_id
                ).where(TbAssetVersionHistory.version == version)
            ).first()
            if not hist:
                raise HTTPException(status_code=404, detail="version not found")
            snapshot = hist.snapshot
            return ScreenAssetRead(
                asset_id=str(asset.asset_id),
                asset_type=asset.asset_type,
                screen_id=asset.screen_id,
                name=snapshot.get("name"),
                description=snapshot.get("description"),
                version=hist.version,
                status=asset.status,
                screen_schema=snapshot.get("schema_json"),
                tags=asset.tags,
                created_by=asset.created_by,
                published_by=asset.published_by,
                published_at=asset.published_at,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )

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


@router.put("/assets/{asset_id}", response_model=ScreenAssetRead)
def update_asset(asset_id: str, payload: ScreenAssetUpdate):
    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
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
def publish_asset(asset_id: str, body: dict[str, Any] = Body(...)):
    published_by = body.get("published_by")
    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
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
def rollback_asset(asset_id: str, body: dict[str, Any] = Body(...)):
    target_version = body.get("target_version")
    published_by = body.get("published_by")
    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
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
def delete_asset(asset_id: str):
    with get_session_context() as session:
        asset = session.get(TbAssetRegistry, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
        if asset.status != "draft":
            raise HTTPException(status_code=400, detail="only draft assets can be deleted")
        session.delete(asset)
        session.commit()
        return {"ok": True}
