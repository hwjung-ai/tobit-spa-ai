from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from .models import TbAssetRegistry, TbAssetVersionHistory
from .validators import validate_asset


def list_assets(
    session: Session,
    asset_type: str | None = None,
    status: str | None = None,
) -> list[TbAssetRegistry]:
    """List assets with optional filters"""
    statement = select(TbAssetRegistry)

    if asset_type:
        statement = statement.where(TbAssetRegistry.asset_type == asset_type)

    if status:
        statement = statement.where(TbAssetRegistry.status == status)

    statement = statement.order_by(TbAssetRegistry.updated_at.desc())
    return session.exec(statement).all()


def get_asset(session: Session, asset_id: str) -> TbAssetRegistry | None:
    """Get asset by ID"""
    try:
        return session.get(TbAssetRegistry, uuid.UUID(asset_id))
    except (ValueError, TypeError):
        return None


def create_asset(
    session: Session,
    name: str,
    asset_type: str,
    description: str | None = None,
    scope: str | None = None,
    engine: str | None = None,
    template: str | None = None,
    input_schema: dict[str, Any] | None = None,
    output_contract: dict[str, Any] | None = None,
    mapping_type: str | None = None,
    content: dict[str, Any] | None = None,
    policy_type: str | None = None,
    limits: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> TbAssetRegistry:
    """Create new asset in draft status"""
    asset = TbAssetRegistry(
        asset_type=asset_type,
        name=name,
        description=description,
        status="draft",
        version=1,
        # Prompt fields
        scope=scope,
        engine=engine,
        template=template,
        input_schema=input_schema,
        output_contract=output_contract,
        # Mapping fields
        mapping_type=mapping_type,
        content=content,
        # Policy fields
        policy_type=policy_type,
        limits=limits,
        # Metadata
        created_by=created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def update_asset(
    session: Session,
    asset: TbAssetRegistry,
    updates: dict[str, Any],
) -> TbAssetRegistry:
    """Update draft asset"""
    if asset.status == "published":
        raise ValueError("Cannot update published asset")

    if not updates:
        return asset

    for key, value in updates.items():
        if key not in ["asset_id", "created_at", "created_by", "status", "version"]:
            setattr(asset, key, value)

    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def publish_asset(
    session: Session,
    asset: TbAssetRegistry,
    published_by: str,
) -> TbAssetRegistry:
    """Publish draft asset"""
    if asset.status == "published":
        raise ValueError("Asset is already published")

    # Validate before publish
    validate_asset(asset)

    # Find existing published asset with same name
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.name == asset.name)
        .where(TbAssetRegistry.asset_type == asset.asset_type)
        .where(TbAssetRegistry.status == "published")
        .where(TbAssetRegistry.asset_id != asset.asset_id)
    ).first()

    if existing:
        # Archive old published version
        existing.status = "draft"
        existing.updated_at = datetime.utcnow()
        session.add(existing)

    # Publish current asset
    asset.status = "published"
    asset.published_by = published_by
    asset.published_at = datetime.utcnow()
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)

    # Save to version history
    history = TbAssetVersionHistory(
        asset_id=asset.asset_id,
        version=asset.version,
        snapshot=asset.model_dump(mode="json"),
        published_by=published_by,
        published_at=datetime.utcnow(),
    )
    session.add(history)
    session.commit()

    return asset


def rollback_asset(
    session: Session,
    asset_id: str,
    to_version: int,
    executed_by: str,
) -> TbAssetRegistry:
    """Rollback published asset to previous version"""
    try:
        asset_uuid = uuid.UUID(asset_id)
    except (ValueError, TypeError):
        raise ValueError("Invalid asset_id format")

    current = session.get(TbAssetRegistry, asset_uuid)
    if not current:
        raise ValueError("Asset not found")

    if current.status != "published":
        raise ValueError("Can only rollback published assets")

    # Find target version from history
    history = session.exec(
        select(TbAssetVersionHistory)
        .where(TbAssetVersionHistory.asset_id == asset_uuid)
        .where(TbAssetVersionHistory.version == to_version)
    ).first()

    if not history:
        raise ValueError(f"Version {to_version} not found in history")

    # Restore snapshot (excluding immutable fields)
    snapshot = history.snapshot
    immutable_fields = {"asset_id", "created_at", "created_by"}

    for key, value in snapshot.items():
        if key not in immutable_fields:
            setattr(current, key, value)

    # Increment version for rollback
    current.version += 1
    current.published_by = executed_by
    current.published_at = datetime.utcnow()
    current.updated_at = datetime.utcnow()

    session.add(current)
    session.commit()
    session.refresh(current)

    # Record rollback in history
    rollback_history = TbAssetVersionHistory(
        asset_id=current.asset_id,
        version=current.version,
        snapshot=current.model_dump(mode="json"),
        published_by=executed_by,
        published_at=datetime.utcnow(),
        rollback_from_version=to_version,
    )
    session.add(rollback_history)
    session.commit()

    return current
