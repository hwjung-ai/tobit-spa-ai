from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.modules.audit_log.crud import create_audit_log
from core.logging import get_request_context
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
    query_sql: str | None = None,
    query_params: dict[str, Any] | None = None,
    query_metadata: dict[str, Any] | None = None,
    screen_id: str | None = None,
    screen_schema: dict[str, Any] | None = None,
    tags: dict[str, Any] | None = None,
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
        # Query fields
        query_sql=query_sql,
        query_params=query_params,
        query_metadata=query_metadata,
        # Screen fields
        screen_id=screen_id,
        screen_schema=screen_schema,
        # Common fields
        tags=tags,
        # Metadata
        created_by=created_by,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def update_asset(
    session: Session,
    asset: TbAssetRegistry,
    updates: dict[str, Any],
    updated_by: str | None = None,
) -> TbAssetRegistry:
    """Update draft asset"""
    if asset.status == "published":
        raise ValueError("Cannot update published asset")

    if not updates:
        return asset

    # Get trace info from context
    context = get_request_context()
    trace_id = context.get("trace_id") or str(uuid.uuid4())
    parent_trace_id = context.get("parent_trace_id") or None

    # Store old values for audit
    old_values = {}
    changes = {}
    for key in updates:
        if key not in ["asset_id", "created_at", "created_by", "status", "version"]:
            old_value = getattr(asset, key, None)
            new_value = updates[key]
            old_values[key] = old_value
            changes[key] = f"{old_value} -> {new_value}"

    for key, value in updates.items():
        if key not in ["asset_id", "created_at", "created_by", "status", "version"]:
            setattr(asset, key, value)

    asset.updated_at = datetime.now()

    session.add(asset)
    session.commit()
    session.refresh(asset)

    # Record audit log if there were changes
    if changes and updated_by:
        create_audit_log(
            session=session,
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            resource_type="asset",
            resource_id=str(asset.asset_id),
            action="update",
            actor=updated_by,
            changes=changes,
            old_values=old_values,
            new_values=updates,
            metadata={"asset_type": asset.asset_type, "asset_name": asset.name},
        )

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

    # Get trace info from context
    context = get_request_context()
    trace_id = context.get("trace_id") or str(uuid.uuid4())
    parent_trace_id = context.get("parent_trace_id") or None

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
        existing.updated_at = datetime.now()
        session.add(existing)

    # Publish current asset
    old_status = asset.status
    asset.status = "published"
    asset.published_by = published_by
    asset.published_at = datetime.now()
    asset.updated_at = datetime.now()

    session.add(asset)
    session.commit()
    session.refresh(asset)

    # Record audit log
    create_audit_log(
        session=session,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        resource_type="asset",
        resource_id=str(asset.asset_id),
        action="publish",
        actor=published_by,
        changes={"status": old_status + " -> published", "version": asset.version},
        old_values={"status": old_status},
        new_values={"status": "published", "published_by": published_by, "published_at": asset.published_at.isoformat()},
        metadata={"asset_type": asset.asset_type, "asset_name": asset.name},
    )

    # Save to version history
    history = TbAssetVersionHistory(
        asset_id=asset.asset_id,
        version=asset.version,
        snapshot=asset.model_dump(mode="json"),
        published_by=published_by,
        published_at=datetime.now(),
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

    # Get trace info from context
    context = get_request_context()
    trace_id = context.get("trace_id") or str(uuid.uuid4())
    parent_trace_id = context.get("parent_trace_id") or None

    # Find target version from history
    history = session.exec(
        select(TbAssetVersionHistory)
        .where(TbAssetVersionHistory.asset_id == asset_uuid)
        .where(TbAssetVersionHistory.version == to_version)
    ).first()

    if not history:
        raise ValueError(f"Version {to_version} not found in history")

    # Store old version for audit
    old_version = current.version

    # Restore snapshot (excluding immutable fields)
    snapshot = history.snapshot
    immutable_fields = {"asset_id", "created_at", "created_by"}

    for key, value in snapshot.items():
        if key not in immutable_fields:
            setattr(current, key, value)

    # Increment version for rollback
    current.version += 1
    current.published_by = executed_by
    current.published_at = datetime.now()
    current.updated_at = datetime.now()

    session.add(current)
    session.commit()
    session.refresh(current)

    # Record audit log for rollback
    create_audit_log(
        session=session,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        resource_type="asset",
        resource_id=str(current.asset_id),
        action="rollback",
        actor=executed_by,
        changes={"version": old_version + " -> " + str(current.version), "from_version": to_version},
        old_values={"version": old_version},
        new_values={"version": current.version, "published_by": executed_by, "published_at": current.published_at.isoformat()},
        metadata={"asset_type": current.asset_type, "asset_name": current.name, "from_version": to_version},
    )

    # Record rollback in history
    rollback_history = TbAssetVersionHistory(
        asset_id=current.asset_id,
        version=current.version,
        snapshot=current.model_dump(mode="json"),
        published_by=executed_by,
        published_at=datetime.now(),
        rollback_from_version=to_version,
    )
    session.add(rollback_history)
    session.commit()

    return current


def delete_asset(
    session: Session,
    asset_id: str,
) -> TbAssetRegistry:
    """Delete a draft asset."""
    asset = session.get(TbAssetRegistry, uuid.UUID(asset_id))
    if not asset:
        raise ValueError("Asset not found")
    if asset.status != "draft":
        raise ValueError("Only draft assets can be deleted")

    session.delete(asset)
    session.commit()
    return asset
def unpublish_asset(
    session: Session,
    asset: TbAssetRegistry,
    executed_by: str = "system",
) -> TbAssetRegistry:
    """Unpublish asset (change status to draft)"""
    if asset.status != "published":
        raise ValueError("Only published assets can be unpublished")

    # Get trace info from context
    context = get_request_context()
    trace_id = context.get("trace_id") or str(uuid.uuid4())
    parent_trace_id = context.get("parent_trace_id") or None

    old_status = asset.status
    asset.status = "draft"
    asset.updated_at = datetime.now()

    session.add(asset)
    session.commit()
    session.refresh(asset)

    # Record audit log
    create_audit_log(
        session=session,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        resource_type="asset",
        resource_id=str(asset.asset_id),
        action="unpublish",
        actor=executed_by,
        changes={"status": old_status + " -> draft"},
        old_values={"status": old_status},
        new_values={"status": "draft"},
        metadata={"asset_type": asset.asset_type, "asset_name": asset.name},
    )

    return asset
