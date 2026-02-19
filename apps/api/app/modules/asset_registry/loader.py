from __future__ import annotations

import logging
from typing import Any

from core.config import get_settings
from core.db import get_session_context
from sqlmodel import select

from app.modules.inspector.asset_context import (
    track_catalog_asset,
    track_mapping_asset,
    track_policy_asset,
    track_prompt_asset,
    track_query_asset,
    track_resolver_asset,
    track_schema_asset,
    track_source_asset,
    track_tool_asset,
)
from app.shared import config_loader

from .models import TbAssetRegistry
from .source_models import coerce_source_connection, coerce_source_type

logger = logging.getLogger(__name__)

def _is_real_mode() -> bool:
    """Check if running in real mode (no fallback allowed)."""
    settings = get_settings()
    return settings.ops_mode == "real"


def _extract_catalog_source_ref(content: dict[str, Any]) -> str | None:
    """Extract source_ref from catalog payload with backward compatibility."""
    catalog_data = content.get("catalog", {}) if isinstance(content, dict) else {}
    if isinstance(catalog_data, dict):
        nested_source_ref = catalog_data.get("source_ref")
        if nested_source_ref:
            return str(nested_source_ref)
    top_level_source_ref = content.get("source_ref") if isinstance(content, dict) else None
    return str(top_level_source_ref) if top_level_source_ref else None


def load_prompt_asset(
    scope: str, engine: str, name: str, version: int | None = None
) -> dict[str, Any] | None:
    """
    Load prompt asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. File from resources/prompts/

    Args:
        scope: Prompt scope (e.g., "ci")
        engine: LLM engine (e.g., "openai")
        name: Asset name
        version: Specific version to load (None for published)
    """
    with get_session_context() as session:
        # Try DB first
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == scope)
            .where(TbAssetRegistry.engine == engine)
            .where(TbAssetRegistry.name == name)
        )

        if version is not None:
            # Load specific version
            query = query.where(TbAssetRegistry.version == version)
        else:
            # Load published version
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(f"Loaded prompt from asset registry: {name} (v{asset.version})")
            templates = {"system": asset.template} if asset.template else {}
            params = list((asset.input_schema or {}).get("properties", {}).keys())
            if asset.output_contract:
                templates = asset.output_contract.get("templates") or templates
                params = asset.output_contract.get("params") or params
            payload = {
                "asset_id": str(asset.asset_id),
                "version": asset.version,
                "name": asset.name,
                "templates": templates,
                "params": params,
                "source": "asset_registry",
            }
            track_prompt_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "scope": scope,
                    "engine": engine,
                }
            )
            return payload

    # Fallback to file (only in test/dev mode)
    if _is_real_mode():
        raise ValueError(
            f"[REAL MODE] Prompt asset not found in Asset Registry: {name} "
            f"(scope={scope}, engine={engine}). "
            f"Asset must be published to Asset Registry (DB) in real mode. "
            f"Please create and publish the asset in Admin → Assets."
        )

    file_path = f"prompts/{scope}/{engine}.yaml"
    prompt_data = config_loader.load_yaml(file_path)

    if prompt_data:
        logger.warning(
            f"Using fallback file for prompt '{name}': resources/{file_path}"
        )
        fallback_payload = dict(prompt_data)
        fallback_payload["source"] = "file_fallback"
        fallback_payload["asset_id"] = None
        fallback_payload["version"] = None
        fallback_payload["name"] = name
        track_prompt_asset(
            {
                "asset_id": None,
                "name": name,
                "version": None,
                "source": "file_fallback",
                "scope": scope,
                "engine": engine,
            }
        )
        return fallback_payload

    logger.warning(f"Prompt asset not found: {name} (scope={scope}, engine={engine})")
    return None


def load_mapping_asset(
    mapping_type: str, version: int | None = None, scope: str | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Load mapping asset from Asset Registry (DB only).

    Args:
        mapping_type: Mapping type identifier (required)
        version: Specific version to load (None for published)
        scope: Scope to filter by (e.g., "ops", "ci"). If None, searches all scopes.

    Returns:
        Tuple of (content_dict, metadata_str) or (None, None) if not found
    """
    with get_session_context() as session:
        # Query by name instead of mapping_type since mapping_type may be NULL
        # Assets are created with name = mapping_type identifier
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.name == mapping_type)
        )

        # Add scope filter if provided
        if scope:
            query = query.where(TbAssetRegistry.scope == scope)

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(
                f"Loaded mapping from asset registry: {asset.name} (v{asset.version})"
            )
            metadata_str = f"asset_registry:{asset.name}:v{asset.version}"
            track_mapping_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "mapping_type": mapping_type,
                }
            )
            # Return tuple: (content_dict, metadata_str)
            return (dict(asset.content or {}), metadata_str)

    # Asset not found
    logger.warning(f"Mapping asset not found: {mapping_type} (scope={scope})")
    return (None, None)


def load_policy_asset(
    policy_type: str, version: int | None = None, scope: str | None = None
) -> dict[str, Any] | None:
    """
    Load policy asset from Asset Registry (DB only).

    Args:
        policy_type: Policy type identifier (required)
        version: Specific version to load (None for published)
        scope: Scope to filter by (e.g., "ops", "ci"). If None, searches all scopes.
    """
    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "policy")
            .where(TbAssetRegistry.policy_type == policy_type)
        )

        # Add scope filter if provided
        if scope:
            query = query.where(TbAssetRegistry.scope == scope)

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        # Order by created_at DESC to get the most recent asset first
        query = query.order_by(TbAssetRegistry.created_at.desc())

        results = session.exec(query).all()

        # Warn if multiple assets found
        if len(results) > 1:
            logger.warning(
                f"Found {len(results)} policy assets with policy_type='{policy_type}'. "
                f"Using the most recent one (created_at={results[0].created_at}). "
                f"Consider removing duplicate assets."
            )

        asset = results[0] if results else None

        if asset:
            logger.info(
                f"Loaded policy from asset registry: {asset.name} (v{asset.version}), policy_type={policy_type}"
            )
            # Use content field for policy data (not limits field which is for budget policies)
            payload = {
                "content": asset.content or {},
                "_asset_meta": {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "policy_type": policy_type,
                }
            }
            track_policy_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "policy_type": policy_type,
                }
            )
            return payload

    # Asset not found
    logger.warning(f"Policy asset not found: {policy_type} (scope={scope})")
    return None


def load_query_asset(
    scope: str, name: str, version: int | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Load query asset from Asset Registry (DB):
    1. Specific version from DB (if version specified), or
    2. Published asset from DB

    Args:
        scope: Query scope (e.g., "ops")
        name: Asset name
        version: Specific version to load (None for published)

    Returns:
        Query asset content dict, or None if not found
    """
    with get_session_context() as session:
        # Try DB first
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "query")
            .where(TbAssetRegistry.scope == scope)
            .where(TbAssetRegistry.name == name)
        )

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(f"Loaded query from asset registry: {name} (v{asset.version})")
            asset_identifier = f"{str(asset.asset_id)}:v{asset.version}"
            track_query_asset(
                {
                    "asset_id": asset_identifier,
                    "name": name,
                    "scope": scope,
                    "source": "asset_registry",
                    "version": asset.version,
                }
            )
            return (
                {
                    "sql": asset.query_sql,
                    "cypher": asset.query_cypher,
                    "http": asset.query_http,
                    "params": asset.query_params or {},
                    "metadata": asset.query_metadata or {},
                    "source": "asset_registry",
                    "asset_id": asset_identifier,
                },
                asset_identifier,
            )

    if _is_real_mode():
        raise ValueError(
            f"[REAL MODE] Query asset not found in Asset Registry: {name} (scope={scope}). "
            f"Asset must be published to Asset Registry (DB) in real mode. "
            f"Please create and publish the asset in Admin → Assets."
        )

    logger.warning(
        "Query asset not found in Asset Registry (dev mode): %s (scope=%s)",
        name,
        scope,
    )
    return None, None


def load_source_asset(name: str, version: int | None = None) -> dict[str, Any] | None:
    """
    Load source asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. Config file from config/sources/

    Args:
        name: Name of source asset
        version: Specific version to load (None for published)

    Returns:
        Dictionary containing source connection details
    """
    with get_session_context() as session:
        # Try DB first
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "source")
            .where(TbAssetRegistry.name == name)
        )

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(f"Loaded source from asset registry: {name} (v{asset.version})")
            content = asset.content or {}
            normalized_connection = coerce_source_connection(content.get("connection", {})).model_dump()
            normalized_source_type = coerce_source_type(content.get("source_type")).value

            payload = {
                "source_type": normalized_source_type,
                "connection": normalized_connection,
                "spec": content.get("spec"),
                "source": "asset_registry",
                "asset_id": str(asset.asset_id),
                "version": asset.version,
                "name": asset.name,
                "scope": asset.scope,
                "tags": asset.tags,
            }
            track_source_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "scope": asset.scope,
                }
            )

            return payload

    # Fallback to config file
    config_file = f"sources/{name}.yaml"
    source_config = config_loader.load_yaml(config_file)

    if source_config:
        # Fallback to file (only in test/dev mode)
        if _is_real_mode():
            raise ValueError(
                f"[REAL MODE] Source asset not found in Asset Registry: {name}. "
                f"Asset must be published to Asset Registry (DB) in real mode. "
                f"Please create and publish the asset in Admin → Assets."
            )

        logger.warning(f"Using config file for source '{name}': {config_file}")
        source_data = dict(source_config)
        source_data["source"] = "file_fallback"
        source_data["asset_id"] = None
        source_data["version"] = None
        track_source_asset(
            {
                "asset_id": None,
                "name": name,
                "version": None,
                "source": "file_fallback",
            }
        )
        return source_data

    logger.warning(f"Source asset not found: {name}")
    return None


def load_catalog_asset(name: str, version: int | None = None) -> dict[str, Any] | None:
    """
    Load catalog asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. Config file from config/catalogs/

    Args:
        name: Name of catalog asset
        version: Specific version to load (None for published)

    Returns:
        Dictionary containing database catalog information
    """
    with get_session_context() as session:
        # Try DB first
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "catalog")
            .where(TbAssetRegistry.name == name)
        )

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(f"Loaded catalog from asset registry: {name} (v{asset.version})")
            content = asset.content or {}
            schema_json = asset.schema_json or {}

            # Use schema_json for catalog if available, otherwise use content
            catalog = schema_json if schema_json else content.get("catalog", {})

            payload = {
                "name": asset.name,
                "source_ref": _extract_catalog_source_ref(content),
                "catalog": catalog,
                "spec": content.get("spec"),
                "source": "asset_registry",
                "asset_id": str(asset.asset_id),
                "version": asset.version,
                "scope": asset.scope,
                "tags": asset.tags,
            }
            # Track catalog asset for inspector
            track_catalog_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "scope": asset.scope,
                }
            )

            return payload

    # Fallback to config file
    config_file = f"catalogs/{name}.yaml"
    catalog_config = config_loader.load_yaml(config_file)

    if catalog_config:
        # Fallback to file (only in test/dev mode)
        if _is_real_mode():
            raise ValueError(
                f"[REAL MODE] Catalog asset not found in Asset Registry: {name}. "
                f"Asset must be published to Asset Registry (DB) in real mode. "
                f"Please create and publish the asset in Admin → Assets."
            )

        logger.warning(f"Using config file for catalog '{name}': {config_file}")
        catalog_data = dict(catalog_config)
        catalog_data["source"] = "file_fallback"
        catalog_data["asset_id"] = None
        catalog_data["version"] = None
        # Track catalog asset for inspector (fallback)
        track_catalog_asset(
            {
                "asset_id": None,
                "name": name,
                "version": None,
                "source": "file_fallback",
            }
        )
        return catalog_data

    logger.warning(f"Catalog asset not found: {name}")
    return None


# Backward compatibility alias
def load_resolver_asset(name: str, version: int | None = None) -> dict[str, Any] | None:
    """
    Load resolver asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. Config file from config/resolvers/

    Args:
        name: Name of resolver asset
        version: Specific version to load (None for published)

    Returns:
        Dictionary containing resolver configuration
    """
    with get_session_context() as session:
        # Try DB first
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "resolver")
            .where(TbAssetRegistry.name == name)
        )

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(
                f"Loaded resolver from asset registry: {name} (v{asset.version})"
            )
            content = asset.content or {}

            payload = {
                "name": asset.name,
                "rules": content.get("rules", []),
                "default_namespace": content.get("default_namespace"),
                "spec": content.get("spec"),
                "source": "asset_registry",
                "asset_id": str(asset.asset_id),
                "version": asset.version,
                "scope": asset.scope,
                "tags": asset.tags,
            }
            track_resolver_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "scope": asset.scope,
                }
            )

            return payload

    # Fallback to config file
    config_file = f"resolvers/{name}.yaml"
    resolver_config = config_loader.load_yaml(config_file)

    if resolver_config:
        # Fallback to file (only in test/dev mode)
        if _is_real_mode():
            raise ValueError(
                f"[REAL MODE] Resolver asset not found in Asset Registry: {name}. "
                f"Asset must be published to Asset Registry (DB) in real mode. "
                f"Please create and publish the asset in Admin → Assets."
            )

        logger.warning(f"Using config file for resolver {name}: {config_file}")
        resolver_data = dict(resolver_config)
        resolver_data["source"] = "file_fallback"
        resolver_data["asset_id"] = None
        resolver_data["version"] = None
        track_resolver_asset(
            {
                "asset_id": None,
                "name": name,
                "version": None,
                "source": "file_fallback",
            }
        )
        return resolver_data

    logger.warning(f"Resolver asset not found: {name}")
    return None
def load_tool_asset(
    name_or_id: str,
    version: int | None = None,
    status: str | None = "published",
) -> dict[str, Any] | None:
    """
    Load a tool asset by name (preferred) or UUID.

    Args:
        name_or_id: Tool name or UUID string
        version: Specific version to load (None for latest by status)
        status: Status filter (default: published, None to ignore status)

    Returns:
        Tool asset dict or None if not found
    """
    import uuid

    with get_session_context() as session:
        query = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")
        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        elif status:
            query = query.where(TbAssetRegistry.status == status)

        # Prefer exact name match first
        by_name = session.exec(query.where(TbAssetRegistry.name == name_or_id)).first()
        asset = by_name

        # Fallback to UUID lookup
        if asset is None:
            try:
                asset_uuid = uuid.UUID(name_or_id)
                by_id_query = select(TbAssetRegistry).where(
                    TbAssetRegistry.asset_type == "tool",
                    TbAssetRegistry.asset_id == asset_uuid,
                )
                if version is not None:
                    by_id_query = by_id_query.where(TbAssetRegistry.version == version)
                elif status:
                    by_id_query = by_id_query.where(TbAssetRegistry.status == status)
                asset = session.exec(by_id_query).first()
            except (ValueError, TypeError):
                asset = None

        if asset is None:
            return None

        tool_info = {
            "asset_id": str(asset.asset_id),
            "name": asset.name,
            "description": asset.description,
            "tool_type": asset.tool_type,
            "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
            "tool_config": getattr(asset, "tool_config", None) or {},
            "tool_input_schema": getattr(asset, "tool_input_schema", None) or {},
            "tool_output_schema": getattr(asset, "tool_output_schema", None) or {},
            "version": asset.version,
            "status": asset.status,
            "source": "asset_registry",
        }

        # Track tool asset for inspector
        track_tool_asset({
            "asset_id": str(asset.asset_id),
            "name": asset.name,
            "tool_type": asset.tool_type,
            "version": asset.version,
            "source": "asset_registry",
        })

        return tool_info


def load_all_published_tools() -> list[dict[str, Any]]:
    """
    Load all published Tool Assets from Asset Registry.

    Returns:
        List of tool asset dictionaries
    """
    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "tool")
            .where(TbAssetRegistry.status == "published")
        )
        tools = session.exec(query).all()

        result = []
        for asset in tools:
            tool_asset = {
                "asset_id": str(asset.asset_id),
                "name": asset.name,
                "description": asset.description,
                "tool_type": asset.tool_type,
                "tool_catalog_ref": getattr(asset, "tool_catalog_ref", None),
                "tool_config": getattr(asset, 'tool_config', None) or {},
                "tool_input_schema": getattr(asset, 'tool_input_schema', None) or {},
                "tool_output_schema": getattr(asset, 'tool_output_schema', None) or {},
                "version": asset.version,
                "source": "asset_registry",
            }
            result.append(tool_asset)

        logger.info(f"Loaded {len(result)} tool assets from Asset Registry")
        return result


def load_all_published_mappings() -> dict[str, Any]:
    """
    Load all published Mapping Assets from Asset Registry.

    Returns:
        Dictionary mapping mapping_name -> content_dict
    """
    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.status == "published")
        )
        mappings = session.exec(query).all()

        result = {}
        for asset in mappings:
            mapping_name = asset.name
            content = dict(asset.content or {})
            result[mapping_name] = content
            logger.debug(
                f"Loaded mapping '{mapping_name}' (v{asset.version}) "
                f"from Asset Registry"
            )

        logger.info(
            f"Loaded {len(result)} mapping assets from Asset Registry"
        )
        return result


def resolve_catalog_asset_for_source(source_ref: str) -> dict[str, Any] | None:
    """
    Resolve a published catalog asset payload for a source_ref.

    Returns:
        Catalog asset payload (same shape as load_catalog_asset) or None
    """
    if not source_ref:
        return None

    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "catalog")
            .where(TbAssetRegistry.status == "published")
            .order_by(TbAssetRegistry.updated_at.desc())
        )
        assets = session.exec(query).all()

        for asset in assets:
            content = asset.content or {}
            catalog = asset.schema_json or content.get("catalog", {})
            catalog_source_ref = _extract_catalog_source_ref(content)
            if catalog_source_ref != source_ref:
                continue
            return {
                "name": asset.name,
                "source_ref": catalog_source_ref,
                "catalog": catalog if isinstance(catalog, dict) else {},
                "spec": content.get("spec"),
                "source": "asset_registry",
                "asset_id": str(asset.asset_id),
                "version": asset.version,
                "scope": asset.scope,
                "tags": asset.tags,
            }

    return None


def load_catalog_for_source(source_ref: str) -> dict[str, Any] | None:
    """
    Load catalog information for a specific data source from Asset Registry.

    Args:
        source_ref: Reference to the data source (e.g., 'postgres_prod', 'primary_postgres')

    Returns:
        Full catalog data with tables, columns, and metadata, or None if not found
    """

    asset_payload = resolve_catalog_asset_for_source(source_ref)
    if asset_payload:
        catalog_data = asset_payload.get("catalog", {})
        if isinstance(catalog_data, dict):
            if not catalog_data.get("source_ref"):
                catalog_data = {**catalog_data, "source_ref": source_ref}
            logger.info(f"Loaded catalog for source: {source_ref}")
            return catalog_data

    logger.warning(f"Catalog not found for source: {source_ref}")
    return None


def load_catalog_for_llm(
    source_ref: str,
    max_tables: int = 10,
    max_columns_per_table: int = 15,
    max_sample_rows: int = 3
) -> dict[str, Any] | None:
    """
    Load catalog and convert to LLM-friendly format.

    This function loads the full catalog and simplifies it for use in LLM prompts:
    - Includes table names, schemas, descriptions
    - Includes column names, types, sizes, descriptions
    - Includes sample data and statistics
    - Limits output size for token efficiency

    Args:
        source_ref: Reference to the data source
        max_tables: Maximum number of tables to include
        max_columns_per_table: Maximum columns per table
        max_sample_rows: Maximum sample rows per table

    Returns:
        Simplified catalog dictionary suitable for LLM prompts, or None if not found
    """
    from app.modules.asset_registry.schema_models import SchemaCatalog

    catalog_data = load_catalog_for_source(source_ref)
    if not catalog_data:
        return None

    try:
        normalized_tables: list[dict[str, Any]] = []
        for table in (catalog_data.get("tables") or []):
            if not isinstance(table, dict):
                continue
            raw_columns = table.get("columns") or []
            normalized_columns: list[dict[str, Any]] = []
            for col in raw_columns:
                if not isinstance(col, dict):
                    continue
                normalized_columns.append(
                    {
                        "name": col.get("name") or col.get("column_name"),
                        "data_type": col.get("data_type") or col.get("type") or "text",
                        "is_nullable": col.get("is_nullable", True),
                        "is_primary_key": col.get("is_primary_key", False),
                        "is_foreign_key": col.get("is_foreign_key", False),
                        "description": col.get("description") or col.get("comment"),
                        "column_size": col.get("column_size"),
                        "numeric_precision": col.get("numeric_precision"),
                        "numeric_scale": col.get("numeric_scale"),
                        "data_samples": col.get("data_samples") or col.get("samples"),
                        "distinct_count": col.get("distinct_count"),
                        "null_count": col.get("null_count"),
                        "min_value": col.get("min_value"),
                        "max_value": col.get("max_value"),
                        "avg_value": col.get("avg_value"),
                        "is_indexed": col.get("is_indexed", False),
                        "is_unique": col.get("is_unique", False),
                        "character_maximum_length": col.get("character_maximum_length"),
                        "ordinal_position": col.get("ordinal_position"),
                    }
                )

            normalized_table = {
                "name": table.get("name"),
                "schema_name": table.get("schema_name") or table.get("schema") or "public",
                "description": table.get("description"),
                "columns": [
                    c for c in normalized_columns if c.get("name")
                ],
                "row_count": table.get("row_count"),
                "size_bytes": table.get("size_bytes"),
                "sample_rows": table.get("sample_rows"),
            }
            if normalized_table["name"]:
                normalized_tables.append(normalized_table)

        normalized_catalog_data = {
            **catalog_data,
            "source_ref": catalog_data.get("source_ref") or source_ref,
            "tables": normalized_tables,
        }

        # Convert dict to SchemaCatalog object
        catalog = SchemaCatalog(**normalized_catalog_data)

        # Convert to LLM format
        llm_format = catalog.to_llm_format(
            max_tables=max_tables,
            max_columns_per_table=max_columns_per_table,
            max_sample_rows=max_sample_rows
        )

        logger.info(
            f"Converted catalog for source {source_ref} to LLM format "
            f"({len(llm_format['tables'])} tables)"
        )

        return llm_format

    except Exception as e:
        logger.error(f"Failed to convert catalog to LLM format: {e}")
        return None


def get_catalog_summary(source_ref: str) -> dict[str, Any] | None:
    """
    Get a quick summary of catalog structure (table and column counts only).

    Useful for quickly checking if catalog exists without loading full data.

    Args:
        source_ref: Reference to the data source

    Returns:
        Dictionary with name, table_count, column_count, or None if not found
    """
    from app.modules.asset_registry.schema_models import SchemaCatalog

    catalog_data = load_catalog_for_source(source_ref)
    if not catalog_data:
        return None

    try:
        catalog = SchemaCatalog(**catalog_data)
        return {
            "name": catalog.name,
            "source_ref": catalog.source_ref,
            "table_count": catalog.table_count,
            "column_count": catalog.column_count,
            "last_scanned": catalog.last_scanned_at,
            "scan_status": catalog.scan_status,
        }
    except Exception as e:
        logger.error(f"Failed to get catalog summary: {e}")
        return None
