from __future__ import annotations

import logging
from typing import Any

from core.config import get_settings
from core.db import get_session_context
from sqlmodel import select

from app.modules.inspector.asset_context import (
    track_mapping_asset,
    track_policy_asset,
    track_prompt_asset,
    track_query_asset,
    track_resolver_asset,
    track_schema_asset,
    track_source_asset,
)
from app.shared import config_loader

from .models import TbAssetRegistry

logger = logging.getLogger(__name__)

def _is_real_mode() -> bool:
    """Check if running in real mode (no fallback allowed)."""
    settings = get_settings()
    return settings.ops_mode == "real"


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
    mapping_type: str = "graph_relation", version: int | None = None
) -> dict[str, Any] | None:
    """
    Load mapping asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. File from resources/
    3. Legacy file (current location)

    Args:
        mapping_type: Mapping type identifier
        version: Specific version to load (None for published)

    Returns:
        Mapping asset content dict, or None if not found
    """
    with get_session_context() as session:
        # Query by name instead of mapping_type since mapping_type may be NULL
        # Assets are created with name = mapping_type identifier
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.name == mapping_type)
        )

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

    # Fallback to seed file (only in test/dev mode)
    if _is_real_mode():
        raise ValueError(
            f"[REAL MODE] Mapping asset not found in Asset Registry: {mapping_type}. "
            f"Asset must be published to Asset Registry (DB) in real mode. "
            f"Please create and publish the asset in Admin → Assets."
        )

    seed_path = "mappings/graph_relation_mapping.yaml"
    seed_data = config_loader.load_yaml(seed_path)

    if seed_data and "content" in seed_data:
        logger.warning(f"Using seed file for mapping: resources/{seed_path}")
        metadata_str = f"seed_file:{mapping_type}"
        track_mapping_asset(
            {
                "asset_id": None,
                "name": mapping_type,
                "version": None,
                "source": "seed_file",
                "mapping_type": mapping_type,
            }
        )
        # Return tuple: (content_dict, metadata_str)
        return (dict(seed_data.get("content") or {}), metadata_str)

    # Legacy fallback
    legacy_path = "app/modules/ops/services/ci/relation_mapping.yaml"
    legacy_data = config_loader.load_yaml(legacy_path)

    if legacy_data:
        logger.warning(f"Using legacy file for mapping: {legacy_path}")
        metadata_str = f"legacy_file:{mapping_type}"
        track_mapping_asset(
            {
                "asset_id": None,
                "name": mapping_type,
                "version": None,
                "source": "legacy_file",
                "mapping_type": mapping_type,
            }
        )
        # Return tuple: (content_dict, metadata_str)
        return (dict(legacy_data), metadata_str)

    logger.warning(f"Mapping asset not found: {mapping_type}")
    return (None, None)


def load_policy_asset(
    policy_type: str = "plan_budget", version: int | None = None
) -> dict[str, Any] | None:
    """
    Load policy asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. Seed file from resources/
    3. Hardcoded defaults

    Args:
        policy_type: Policy type identifier
        version: Specific version to load (None for published)
    """
    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "policy")
            .where(TbAssetRegistry.policy_type == policy_type)
        )

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

    # Fallback to seed file or hardcoded (only in test/dev mode)
    if _is_real_mode():
        raise ValueError(
            f"[REAL MODE] Policy asset not found in Asset Registry: {policy_type}. "
            f"Asset must be published to Asset Registry (DB) in real mode. "
            f"Please create and publish the asset in Admin → Assets."
        )

    seed_file_map = {
        "plan_budget": "policies/plan_budget.yaml",
        "view_depth": "policies/view_depth_policies.yaml",
    }

    if policy_type in seed_file_map:
        seed_path = seed_file_map[policy_type]
        seed_data = config_loader.load_yaml(seed_path)
        if seed_data and "limits" in seed_data:
            logger.warning(
                f"Using seed file for policy '{policy_type}': resources/{seed_path}"
            )
            payload = dict(seed_data["limits"] or {})
            payload["_asset_meta"] = {
                "asset_id": None,
                "name": policy_type,
                "version": None,
                "source": "seed_file",
                "policy_type": policy_type,
            }
            track_policy_asset(
                {
                    "asset_id": None,
                    "name": policy_type,
                    "version": None,
                    "source": "seed_file",
                    "policy_type": policy_type,
                }
            )
            return payload

    # No fallback - policy asset is required
    logger.error(f"Policy asset '{policy_type}' not found in DB or seed files")
    raise ValueError(
        f"Policy asset '{policy_type}' is required but not found. "
        f"Please create the policy asset in the database or provide a seed file."
    )


def load_query_asset(
    scope: str, name: str, version: int | None = None
) -> dict[str, Any] | None:
    """
    Load query asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. File from resources/queries/

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

    # Fallback to file (only in test/dev mode)
    if _is_real_mode():
        raise ValueError(
            f"[REAL MODE] Query asset not found in Asset Registry: {name} (scope={scope}). "
            f"Asset must be published to Asset Registry (DB) in real mode. "
            f"Please create and publish the asset in Admin → Assets."
        )

    file_path = f"queries/{scope}/{name}.sql"
    query_text = config_loader.load_text(file_path)

    if query_text:
        logger.warning(f"Using fallback file for query '{name}': resources/{file_path}")
        track_query_asset(
            {
                "asset_id": None,
                "name": name,
                "scope": scope,
                "source": "file_fallback",
                "version": None,
            }
        )
        return (
            {
                "sql": query_text,
                "params": {},
                "metadata": {"seed_file": file_path},
                "source": "file_fallback",
            },
            None,
        )

    logger.warning(f"Query asset not found: {name} (scope={scope})")
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

            payload = {
                "source_type": content.get("source_type"),
                "connection": content.get("connection", {}),
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
                "source_ref": content.get("source_ref"),
                "catalog": catalog,
                "spec": content.get("spec"),
                "source": "asset_registry",
                "asset_id": str(asset.asset_id),
                "version": asset.version,
                "scope": asset.scope,
                "tags": asset.tags,
            }
            track_schema_asset(
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
        track_schema_asset(
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
                "tool_config": getattr(asset, 'tool_config', None) or {},
                "tool_input_schema": getattr(asset, 'tool_input_schema', None) or {},
                "tool_output_schema": getattr(asset, 'tool_output_schema', None) or {},
                "version": asset.version,
                "source": "asset_registry",
            }
            result.append(tool_asset)

        logger.info(f"Loaded {len(result)} tool assets from Asset Registry")
        return result
