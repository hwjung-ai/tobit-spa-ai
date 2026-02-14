from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

from core.logging import get_request_context
from sqlmodel import Session, select

from app.modules.audit_log.crud import create_audit_log

from .models import TbAssetRegistry, TbAssetVersionHistory
from .resolver_models import (
    ResolverAsset,
    ResolverAssetCreate,
    ResolverAssetUpdate,
    ResolverConfig,
    ResolverType,
)
from .schema_models import (
    ScanResult,
    SchemaAsset,
    SchemaAssetCreate,
    SchemaAssetUpdate,
    SchemaCatalog,
)
from .source_models import (
    ConnectionTestResult,
    SourceAsset,
    SourceAssetCreate,
    SourceAssetUpdate,
    SourceType,
)
from .validators import validate_asset


def list_assets(
    session: Session,
    asset_type: str | None = None,
    status: str | None = None,
    tenant_id: str | None = None,
) -> list[TbAssetRegistry]:
    """List assets with optional filters"""
    statement = select(TbAssetRegistry)

    if asset_type:
        statement = statement.where(TbAssetRegistry.asset_type == asset_type)

    if status:
        statement = statement.where(TbAssetRegistry.status == status)

    if tenant_id:
        statement = statement.where(TbAssetRegistry.tenant_id == tenant_id)

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
    tool_type: str | None = None,
    tool_config: dict[str, Any] | None = None,
    tool_input_schema: dict[str, Any] | None = None,
    tool_output_schema: dict[str, Any] | None = None,
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
        schema_json=screen_schema,
        # Tool fields
        tool_type=tool_type,
        tool_config=tool_config,
        tool_input_schema=tool_input_schema,
        tool_output_schema=tool_output_schema,
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
        new_values={
            "status": "published",
            "published_by": published_by,
            "published_at": asset.published_at.isoformat(),
        },
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


def create_tool_asset(
    session: Session,
    name: str,
    description: str,
    tool_type: str,
    tool_config: dict[str, Any],
    tool_input_schema: dict[str, Any],
    tool_output_schema: dict[str, Any] | None = None,
    tool_catalog_ref: str | None = None,
    tags: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> TbAssetRegistry:
    """Create new tool asset in draft status"""
    asset = TbAssetRegistry(
        asset_type="tool",
        name=name,
        description=description,
        status="draft",
        version=1,
        tool_type=tool_type,
        tool_catalog_ref=tool_catalog_ref,
        tool_config=tool_config,
        tool_input_schema=tool_input_schema,
        tool_output_schema=tool_output_schema,
        tags=tags,
        created_by=created_by,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def get_tool_asset(
    session: Session,
    asset_id: str,
) -> TbAssetRegistry | None:
    """Get tool asset by ID"""
    try:
        return session.get(TbAssetRegistry, uuid.UUID(asset_id))
    except (ValueError, TypeError):
        return None


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
        changes={
            "version": old_version + " -> " + str(current.version),
            "from_version": to_version,
        },
        old_values={"version": old_version},
        new_values={
            "version": current.version,
            "published_by": executed_by,
            "published_at": current.published_at.isoformat(),
        },
        metadata={
            "asset_type": current.asset_type,
            "asset_name": current.name,
            "from_version": to_version,
        },
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

    # Delete version history first
    histories = session.exec(
        select(TbAssetVersionHistory).where(TbAssetVersionHistory.asset_id == asset.asset_id)
    ).all()
    for history in histories:
        session.delete(history)

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


# Source Asset CRUD operations
def create_source_asset(
    session: Session,
    source_data: SourceAssetCreate,
    created_by: str | None = None,
) -> SourceAsset:
    """Create a new source asset"""
    # Create TbAssetRegistry record
    asset = create_asset(
        session=session,
        name=source_data.name,
        asset_type="source",
        description=source_data.description,
        scope=source_data.scope,
        tags=source_data.tags,
        created_by=created_by,
    )

    # Store source-specific data in content field
    content = {
        "source_type": source_data.source_type.value,
        "connection": source_data.connection.model_dump(),
        "spec": source_data.connection.spec
        if hasattr(source_data.connection, "spec")
        else None,
    }

    update_asset(
        session=session,
        asset=asset,
        updates={"content": content},
        updated_by=created_by,
    )

    return SourceAsset(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        name=asset.name,
        description=asset.description,
        version=asset.version,
        status=asset.status,
        source_type=source_data.source_type,
        connection=source_data.connection,
        scope=asset.scope,
        tags=asset.tags,
        created_by=asset.created_by,
        published_by=asset.published_by,
        published_at=asset.published_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        spec_json=asset.content.get("spec"),
    )


def get_source_asset(session: Session, asset_id: str) -> SourceAsset | None:
    """Get source asset by ID"""
    asset = get_asset(session, asset_id)
    if not asset or asset.asset_type != "source":
        return None

    # Extract source data from content
    content = asset.content or {}
    return SourceAsset(
        asset_id=asset.asset_id,
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
        spec_json=content.get("spec"),
    )


def update_source_asset(
    session: Session,
    asset_id: str,
    updates: SourceAssetUpdate,
    updated_by: str | None = None,
) -> SourceAsset:
    """Update a source asset"""
    asset = get_source_asset(session, asset_id)
    if not asset:
        raise ValueError("Source asset not found")

    # Convert to dict for updates
    content = asset.content or {}

    # Update connection if provided
    if updates.connection:
        content["connection"] = updates.connection.model_dump()
        content["spec"] = (
            updates.connection.spec if hasattr(updates.connection, "spec") else None
        )

    # Build update dictionary
    update_dict = {}
    if updates.name is not None:
        update_dict["name"] = updates.name
    if updates.description is not None:
        update_dict["description"] = updates.description
    if updates.source_type is not None:
        update_dict["source_type"] = updates.source_type.value
        update_dict["content"] = content
    if updates.connection is not None:
        update_dict["content"] = content
    if updates.scope is not None:
        update_dict["scope"] = updates.scope
    if updates.tags is not None:
        update_dict["tags"] = updates.tags

    # Update the asset
    update_asset(
        session=session,
        asset=asset,
        updates=update_dict,
        updated_by=updated_by,
    )

    return get_source_asset(session, asset_id)


def delete_source_asset(session: Session, asset_id: str) -> SourceAsset:
    """Delete a source asset"""
    asset = get_source_asset(session, asset_id)
    if not asset:
        raise ValueError("Source asset not found")

    return delete_asset(session, asset_id)


def test_source_connection(session: Session, asset_id: str) -> ConnectionTestResult:
    """Test source connection"""
    asset = get_source_asset(session, asset_id)
    if not asset:
        raise ValueError("Source asset not found")

    import time

    start_time = time.time()

    def resolve_secret(secret_ref: str | None) -> str | None:
        if not secret_ref:
            return None
        if secret_ref.startswith("env:"):
            key = secret_ref.split(":", 1)[1]
            return os.environ.get(key)
        return None

    try:
        # Test connection based on source type
        if asset.source_type == SourceType.POSTGRESQL:
            import psycopg2

            conn = psycopg2.connect(
                host=asset.connection.host,
                port=asset.connection.port,
                user=asset.connection.username,
                password=asset.connection.password
                or asset.connection.password_encrypted
                or resolve_secret(asset.connection.secret_key_ref)
                or "",
                database=asset.connection.database,
                connect_timeout=asset.connection.timeout,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                execution_time_ms=int((time.time() - start_time) * 1000),
                test_result={"rows": 1},
            )

        elif asset.source_type == SourceType.NEO4J:
            from neo4j import GraphDatabase

            # Build URI from host and port
            uri = (
                asset.connection.uri
                or f"bolt://{asset.connection.host}:{asset.connection.port}"
            )

            driver = GraphDatabase.driver(
                uri,
                auth=(
                    asset.connection.username,
                    asset.connection.password
                    or asset.connection.password_encrypted
                    or resolve_secret(asset.connection.secret_key_ref)
                    or "",
                ),
            )
            driver.verify_connectivity()

            # Check if database is accessible
            with driver.session() as session:
                result = session.run("RETURN 1 as num")
                result.single()

            driver.close()

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                execution_time_ms=int((time.time() - start_time) * 1000),
                test_result={"uri": uri},
            )

        elif asset.source_type == SourceType.REDIS:
            import redis

            r = redis.Redis(
                host=asset.connection.host,
                port=asset.connection.port,
                password=asset.connection.password
                or asset.connection.password_encrypted
                or resolve_secret(asset.connection.secret_key_ref),
                decode_responses=True,
            )
            r.ping()

            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                execution_time_ms=int((time.time() - start_time) * 1000),
                test_result={"ping": "pong"},
            )

        else:
            return ConnectionTestResult(
                success=False,
                message="Source type not supported for testing",
                error_details=f"Connection testing not implemented for {asset.source_type}",
            )

    except Exception as e:
        return ConnectionTestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            error_details=str(e),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )


# Schema Asset CRUD operations
def build_schema_catalog(asset: TbAssetRegistry) -> SchemaCatalog:
    content = asset.content or {}
    catalog_data = content.get("catalog") or {}

    if isinstance(catalog_data, SchemaCatalog):
        return catalog_data

    catalog_name = catalog_data.get("name") or asset.name
    source_ref = (
        catalog_data.get("source_ref")
        or content.get("source_ref")
        or str(asset.asset_id)
    )

    return SchemaCatalog(
        name=catalog_name,
        description=catalog_data.get("description"),
        source_ref=source_ref,
        tables=catalog_data.get("tables", []),
        last_scanned_at=catalog_data.get("last_scanned_at"),
        scan_status=catalog_data.get("scan_status", "pending"),
        scan_metadata=catalog_data.get("scan_metadata", {}),
    )


def create_schema_asset(
    session: Session,
    schema_data: SchemaAssetCreate,
    created_by: str | None = None,
) -> SchemaAsset:
    """Create a new schema asset"""
    catalog = getattr(schema_data, "catalog", None)
    if catalog is None:
        catalog = SchemaCatalog(
            name=schema_data.name,
            source_ref=schema_data.source_ref,
            tables=[],
        )

    # Create TbAssetRegistry record
    asset = create_asset(
        session=session,
        name=schema_data.name,
        asset_type="catalog",
        description=schema_data.description,
        scope=schema_data.scope,
        tags=schema_data.tags,
        created_by=created_by,
    )

    # Store schema data in content field
    content = {
        "source_ref": schema_data.source_ref,
        "catalog": catalog.model_dump(),
        "spec": None,
    }

    update_asset(
        session=session,
        asset=asset,
        updates={"content": content},
        updated_by=created_by,
    )

    return SchemaAsset(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        name=asset.name,
        description=asset.description,
        version=asset.version,
        status=asset.status,
        catalog=catalog,
        scope=asset.scope,
        tags=asset.tags,
        created_by=asset.created_by,
        published_by=asset.published_by,
        published_at=asset.published_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        spec_json=content.get("spec"),
    )


def get_schema_asset(session: Session, asset_id: str) -> SchemaAsset | None:
    """Get schema asset by ID"""
    asset = get_asset(session, asset_id)
    if not asset or asset.asset_type != "catalog":
        return None

    # Extract schema data from content
    return SchemaAsset(
        asset_id=asset.asset_id,
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
        spec_json=(asset.content or {}).get("spec"),
    )


def update_schema_asset(
    session: Session,
    asset_id: str,
    updates: SchemaAssetUpdate,
    updated_by: str | None = None,
) -> SchemaAsset:
    """Update a schema asset"""
    asset = get_schema_asset(session, asset_id)
    if not asset:
        raise ValueError("Schema asset not found")

    # Convert to dict for updates
    content = asset.content or {}

    # Update catalog if provided
    if updates.catalog:
        content["catalog"] = updates.catalog.model_dump()
        content["spec"] = updates.catalog.spec

    # Build update dictionary
    update_dict = {}
    if updates.name is not None:
        update_dict["name"] = updates.name
    if updates.description is not None:
        update_dict["description"] = updates.description
    if updates.catalog is not None:
        update_dict["content"] = content
    if updates.scope is not None:
        update_dict["scope"] = updates.scope
    if updates.tags is not None:
        update_dict["tags"] = updates.tags

    # Update the asset
    update_asset(
        session=session,
        asset=asset,
        updates=update_dict,
        updated_by=updated_by,
    )

    return get_schema_asset(session, asset_id)


def delete_schema_asset(session: Session, asset_id: str) -> SchemaAsset:
    """Delete a schema asset"""
    asset = get_schema_asset(session, asset_id)
    if not asset:
        raise ValueError("Schema asset not found")

    return delete_asset(session, asset_id)


def scan_schema(session: Session, asset_id: str) -> ScanResult:
    """Scan schema from source"""
    # This is a placeholder implementation
    # In a real implementation, this would connect to the source and scan the schema
    import time

    start_time = time.time()

    try:
        # Simulate scanning process
        scan_id = f"scan_{uuid.uuid4().hex[:8]}"

        # Get the source asset
        from .crud import get_source_asset

        source_asset = get_source_asset(session, asset_id)
        if not source_asset:
            raise ValueError("Source asset not found")

        # In a real implementation, this would:
        # 1. Connect to the database using source_asset.connection
        # 2. Query the schema information (information_schema)
        # 3. Build the SchemaCatalog object
        # 4. Update the schema asset

        # For now, return a mock result
        result = ScanResult(
            scan_id=scan_id,
            source_ref=asset_id,
            status="completed",
            tables_scanned=10,
            columns_discovered=50,
            scan_metadata={"source_type": source_asset.source_type.value},
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        return result

    except Exception as e:
        return ScanResult(
            scan_id=f"scan_{uuid.uuid4().hex[:8]}",
            source_ref=asset_id,
            status="failed",
            tables_scanned=0,
            columns_discovered=0,
            error_message=str(e),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )


async def scan_schema_asset(
    session: Session,
    asset: TbAssetRegistry,
    schema_names: list[str] | None = None,
    include_row_counts: bool = False,
) -> TbAssetRegistry:
    """
    Scan source database and populate schema asset with metadata.

    Args:
        session: Database session
        asset: Schema asset to populate
        schema_names: List of schema names to scan (None = default schema)
        include_row_counts: Whether to count rows (can be slow)

    Returns:
        Updated schema asset
    """
    from core.logging import get_logger

    from app.modules.ops.services.orchestration.discovery.catalog_factory import CatalogFactory

    logger = get_logger(__name__)

    # Update status to scanning
    content = asset.content or {}
    source_ref = content.get("source_ref")

    if not source_ref:
        raise ValueError("Schema asset must have source_ref in content")

    # Load source asset
    source_asset = load_source_asset(source_ref)

    # Update scan status
    catalog_data = content.get("catalog", {})
    catalog_data["scan_status"] = "scanning"
    content["catalog"] = catalog_data
    asset.content = content
    session.add(asset)
    session.commit()

    try:
        # Create appropriate catalog
        catalog = CatalogFactory.create(source_asset)

        # Build catalog
        catalog_result = await catalog.build_catalog(schema_names)

        # Update asset with scanned data
        from datetime import datetime

        catalog_data = {
            "name": asset.name,
            "description": asset.description,
            "source_ref": source_ref,
            "tables": catalog_result["tables"],
            "database_type": catalog_result["database_type"],
            "last_scanned_at": datetime.now().isoformat(),
            "scan_status": "completed",
            "scan_metadata": {
                "schema_names": schema_names,
                "include_row_counts": include_row_counts,
                "table_count": len(catalog_result["tables"]),
                "total_columns": sum(len(t.get("columns", [])) for t in catalog_result["tables"]),
            },
        }

        content["catalog"] = catalog_data
        asset.content = content
        session.add(asset)
        session.commit()

        logger.info(f"Schema scan completed: {asset.name} ({len(catalog_result['tables'])} tables)")

        await catalog.close()

        return asset

    except Exception as e:
        logger.error(f"Schema scan failed: {asset.name}: {e}")

        # Update status to failed
        from datetime import datetime

        catalog_data["scan_status"] = "failed"
        catalog_data["scan_error"] = str(e)
        catalog_data["last_scanned_at"] = datetime.now().isoformat()
        content["catalog"] = catalog_data
        asset.content = content
        session.add(asset)
        session.commit()

        raise


# Resolver Asset CRUD operations
def create_resolver_asset(
    session: Session,
    resolver_data: ResolverAssetCreate,
    created_by: str | None = None,
) -> ResolverAsset:
    """Create a new resolver asset"""
    # Create TbAssetRegistry record
    asset = create_asset(
        session=session,
        name=resolver_data.name,
        asset_type="resolver",
        description=resolver_data.description,
        scope=resolver_data.scope,
        tags=resolver_data.tags,
        created_by=created_by,
    )

    # Store resolver data in content field
    content = {
        "rules": [rule.model_dump() for rule in resolver_data.config.rules],
        "default_namespace": resolver_data.config.default_namespace,
        "spec": None,
    }

    update_asset(
        session=session,
        asset=asset,
        updates={"content": content},
        updated_by=created_by,
    )

    return ResolverAsset(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        name=asset.name,
        description=asset.description,
        version=asset.version,
        status=asset.status,
        config=resolver_data.config,
        scope=asset.scope,
        tags=asset.tags,
        created_by=asset.created_by,
        published_by=asset.published_by,
        published_at=asset.published_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        spec_json=content.get("spec"),
    )


def get_resolver_asset(session: Session, asset_id: str) -> ResolverAsset | None:
    """Get resolver asset by ID"""
    asset = get_asset(session, asset_id)
    if not asset or asset.asset_type != "resolver":
        return None

    # Extract resolver data from content
    content = asset.content or {}

    # Rebuild rules from content
    rules_data = content.get("rules", [])
    rules = []
    for rule_data in rules_data:
        # This is a simplified version - in a real implementation, we would need to handle the union type properly
        from .resolver_models import (
            AliasMapping,
            PatternRule,
            ResolverRule,
            ResolverType,
            TransformationRule,
        )

        rule_type = rule_data.get("rule_type", "alias_mapping")

        if rule_type == "alias_mapping":
            rule_data_obj = AliasMapping(**rule_data)
        elif rule_type == "pattern_rule":
            rule_data_obj = PatternRule(**rule_data)
        elif rule_type == "transformation":
            rule_data_obj = TransformationRule(**rule_data)
        else:
            rule_data_obj = rule_data

        rule = ResolverRule(
            rule_type=ResolverType(rule_type),
            name=rule_data.get("name", ""),
            description=rule_data.get("description"),
            is_active=rule_data.get("is_active", True),
            priority=rule_data.get("priority", 0),
            metadata=rule_data.get("metadata", {}),
            rule_data=rule_data_obj,
        )
        rules.append(rule)

    config = ResolverConfig(
        name=asset.name,
        description=asset.description,
        rules=rules,
        default_namespace=content.get("default_namespace"),
        tags=asset.tags,
        version=asset.version,
    )

    return ResolverAsset(
        asset_id=asset.asset_id,
        asset_type=asset.asset_type,
        name=asset.name,
        description=asset.description,
        version=asset.version,
        status=asset.status,
        config=config,
        scope=asset.scope,
        tags=asset.tags,
        created_by=asset.created_by,
        published_by=asset.published_by,
        published_at=asset.published_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        spec_json=content.get("spec"),
    )


def update_resolver_asset(
    session: Session,
    asset_id: str,
    updates: ResolverAssetUpdate,
    updated_by: str | None = None,
) -> ResolverAsset:
    """Update a resolver asset"""
    asset = get_resolver_asset(session, asset_id)
    if not asset:
        raise ValueError("Resolver asset not found")

    # Convert to dict for updates
    content = asset.content or {}

    # Update config if provided
    if updates.config:
        content["rules"] = [rule.model_dump() for rule in updates.config.rules]
        content["default_namespace"] = updates.config.default_namespace
        content["spec"] = updates.config.spec

    # Build update dictionary
    update_dict = {}
    if updates.name is not None:
        update_dict["name"] = updates.name
    if updates.description is not None:
        update_dict["description"] = updates.description
    if updates.config is not None:
        update_dict["content"] = content
    if updates.scope is not None:
        update_dict["scope"] = updates.scope
    if updates.tags is not None:
        update_dict["tags"] = updates.tags

    # Update the asset
    update_asset(
        session=session,
        asset=asset,
        updates=update_dict,
        updated_by=updated_by,
    )

    return get_resolver_asset(session, asset_id)


def delete_resolver_asset(session: Session, asset_id: str) -> ResolverAsset:
    """Delete a resolver asset"""
    asset = get_resolver_asset(session, asset_id)
    if not asset:
        raise ValueError("Resolver asset not found")

    return delete_asset(session, asset_id)


def simulate_resolver_configuration(
    session: Session, asset_id: str, test_entities: List[str]
) -> Dict[str, Any]:
    """Simulate resolver configuration with test entities"""
    asset = get_resolver_asset(session, asset_id)
    if not asset:
        raise ValueError("Resolver asset not found")

    results = []
    for entity in test_entities:
        # This is a simplified simulation
        # In a real implementation, this would apply the actual resolver logic
        result = {
            "original_entity": entity,
            "resolved_entity": entity,  # No transformation by default
            "transformations_applied": [],
            "confidence_score": 0.0,
            "matched_rules": [],
            "metadata": {"simulation": True},
        }

        # Apply alias mappings
        for rule in asset.config.get_rules_by_type(ResolverType.ALIAS_MAPPING):
            if rule.is_active:
                if entity == rule.rule_data.source_entity:
                    result["resolved_entity"] = rule.rule_data.target_entity
                    result["matched_rules"].append(rule.name)
                    result["transformations_applied"].append("alias_mapping")
                    result["confidence_score"] = 1.0

        results.append(result)

    return {
        "asset_id": str(asset.asset_id),
        "test_count": len(test_entities),
        "results": results,
        "metadata": {
            "resolver_version": asset.version,
            "rule_count": len(asset.config.rules),
        },
    }


# Query Asset CRUD operations
def create_query_asset(
    session: Session,
    query_data: Any,  # QueryAssetCreate from query_models
    created_by: str | None = None,
) -> Any:  # QueryAssetResponse
    """Create a new query asset"""
    # Create TbAssetRegistry record
    asset = create_asset(
        session=session,
        name=query_data.name,
        asset_type="query",
        description=query_data.description,
        scope=query_data.scope,
        query_sql=query_data.query_sql,
        query_params=query_data.query_params,
        query_metadata=query_data.query_metadata,
        tags=query_data.tags,
        created_by=created_by,
    )

    # Import QueryAssetResponse locally to avoid circular imports
    from .query_models import QueryAssetResponse

    return QueryAssetResponse(
        asset_id=str(asset.asset_id),
        asset_type=asset.asset_type,
        name=asset.name,
        description=asset.description,
        version=asset.version,
        status=asset.status,
        scope=asset.scope,
        query_sql=asset.query_sql or "",
        query_params=asset.query_params or {},
        query_metadata=asset.query_metadata or {},
        tags=asset.tags,
        created_by=asset.created_by,
        published_by=asset.published_by,
        published_at=asset.published_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def get_query_asset(
    session: Session, asset_id: str
) -> Any | None:  # QueryAssetResponse | None
    """Get query asset by ID"""
    asset = get_asset(session, asset_id)
    if not asset or asset.asset_type != "query":
        return None

    from .query_models import QueryAssetResponse

    return QueryAssetResponse(
        asset_id=str(asset.asset_id),
        asset_type=asset.asset_type,
        name=asset.name,
        description=asset.description,
        version=asset.version,
        status=asset.status,
        scope=asset.scope,
        query_sql=asset.query_sql or "",
        query_params=asset.query_params or {},
        query_metadata=asset.query_metadata or {},
        tags=asset.tags,
        created_by=asset.created_by,
        published_by=asset.published_by,
        published_at=asset.published_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def update_query_asset(
    session: Session,
    asset_id: str,
    updates: Any,  # QueryAssetUpdate from query_models
    updated_by: str | None = None,
) -> Any:  # QueryAssetResponse
    """Update a query asset"""
    asset = get_query_asset(session, asset_id)
    if not asset:
        raise ValueError("Query asset not found")

    # Build update dictionary
    update_dict = {}
    if updates.name is not None:
        update_dict["name"] = updates.name
    if updates.description is not None:
        update_dict["description"] = updates.description
    if updates.query_sql is not None:
        update_dict["query_sql"] = updates.query_sql
    if updates.query_params is not None:
        update_dict["query_params"] = updates.query_params
    if updates.query_metadata is not None:
        update_dict["query_metadata"] = updates.query_metadata
    if updates.tags is not None:
        update_dict["tags"] = updates.tags

    # Update the asset
    # Need to get the actual TbAssetRegistry object
    tb_asset = get_asset(session, asset_id)
    if tb_asset:
        update_asset(
            session=session,
            asset=tb_asset,
            updates=update_dict,
            updated_by=updated_by,
        )

    return get_query_asset(session, asset_id)


def delete_query_asset(session: Session, asset_id: str) -> Any:  # QueryAssetResponse
    """Delete a query asset"""
    asset = get_query_asset(session, asset_id)
    if not asset:
        raise ValueError("Query asset not found")

    return delete_asset(session, asset_id)
