from __future__ import annotations

import logging
from typing import Any

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

    # Fallback to file
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
    2. Seed file from resources/
    3. Legacy file (current location)

    Args:
        mapping_type: Mapping type identifier
        version: Specific version to load (None for published)
    """
    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.mapping_type == mapping_type)
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
            payload = dict(asset.content or {})
            payload["_asset_meta"] = {
                "asset_id": str(asset.asset_id),
                "name": asset.name,
                "version": asset.version,
                "source": "asset_registry",
                "mapping_type": mapping_type,
            }
            track_mapping_asset(
                {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "version": asset.version,
                    "source": "asset_registry",
                    "mapping_type": mapping_type,
                }
            )
            return payload

    # Fallback to seed file
    seed_path = "mappings/graph_relation_mapping.yaml"
    seed_data = config_loader.load_yaml(seed_path)

    if seed_data and "content" in seed_data:
        logger.warning(f"Using seed file for mapping: resources/{seed_path}")
        payload = dict(seed_data.get("content") or {})
        payload["_asset_meta"] = {
            "asset_id": None,
            "name": mapping_type,
            "version": None,
            "source": "seed_file",
            "mapping_type": mapping_type,
        }
        track_mapping_asset(
            {
                "asset_id": None,
                "name": mapping_type,
                "version": None,
                "source": "seed_file",
                "mapping_type": mapping_type,
            }
        )
        return payload

    # Legacy fallback
    legacy_path = "app/modules/ops/services/ci/relation_mapping.yaml"
    legacy_data = config_loader.load_yaml(legacy_path)

    if legacy_data:
        logger.warning(f"Using legacy file for mapping: {legacy_path}")
        payload = dict(legacy_data)
        payload["_asset_meta"] = {
            "asset_id": None,
            "name": mapping_type,
            "version": None,
            "source": "legacy_file",
            "mapping_type": mapping_type,
        }
        track_mapping_asset(
            {
                "asset_id": None,
                "name": mapping_type,
                "version": None,
                "source": "legacy_file",
                "mapping_type": mapping_type,
            }
        )
        return payload

    logger.warning(f"Mapping asset not found: {mapping_type}")
    return None


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

        asset = session.exec(query).first()

        if asset:
            logger.info(
                f"Loaded policy from asset registry: {asset.name} (v{asset.version})"
            )
            payload = dict(asset.limits or {})
            payload["_asset_meta"] = {
                "asset_id": str(asset.asset_id),
                "name": asset.name,
                "version": asset.version,
                "source": "asset_registry",
                "policy_type": policy_type,
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

    # Fallback to seed file
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

    # Ultimate fallback to hardcoded defaults
    logger.warning(f"Using hardcoded defaults for policy '{policy_type}'")
    if policy_type == "plan_budget":
        return {
            "max_steps": 10,
            "timeout_ms": 120000,  # 2 minutes
            "max_depth": 5,
            "max_branches": 3,
            "max_iterations": 100,
        }
    elif policy_type == "view_depth":
        # Return a minimal view_depth policy (this shouldn't normally be used)
        logger.warning("No view_depth policy found in DB or seed file, returning None")
        payload = {
            "max_steps": 10,
            "timeout_ms": 120000,
            "max_depth": 5,
            "max_branches": 3,
            "max_iterations": 100,
            "_asset_meta": {
                "asset_id": None,
                "name": policy_type,
                "version": None,
                "source": "default",
                "policy_type": policy_type,
            },
        }
        track_policy_asset(
            {
                "asset_id": None,
                "name": policy_type,
                "version": None,
                "source": "default",
                "policy_type": policy_type,
            }
        )
        return payload

    return None


def load_query_asset(
    scope: str, name: str, version: int | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Load query asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. File from resources/queries/

    Args:
        scope: Query scope (e.g., "ops")
        name: Asset name
        version: Specific version to load (None for published)

    Returns:
        Tuple of (asset_data, asset_id_version_str)
        asset_id_version_str format: "{asset_id}:v{version}" for tracking
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
                    "params": asset.query_params or {},
                    "metadata": asset.query_metadata or {},
                    "source": "asset_registry",
                    "asset_id": asset_identifier,
                },
                asset_identifier,
            )

    # Fallback to file
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


def load_schema_asset(name: str, version: int | None = None) -> dict[str, Any] | None:
    """
    Load schema asset with fallback priority:
    1. Specific version from DB (if version specified) or Published asset from DB
    2. Config file from config/schemas/

    Args:
        name: Name of schema asset
        version: Specific version to load (None for published)

    Returns:
        Dictionary containing schema catalog information
    """
    with get_session_context() as session:
        # Try DB first
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "schema")
            .where(TbAssetRegistry.name == name)
        )

        if version is not None:
            query = query.where(TbAssetRegistry.version == version)
        else:
            query = query.where(TbAssetRegistry.status == "published")

        asset = session.exec(query).first()

        if asset:
            logger.info(f"Loaded schema from asset registry: {name} (v{asset.version})")
            content = asset.content or {}

            payload = {
                "name": asset.name,
                "source_ref": content.get("source_ref"),
                "catalog": content.get("catalog", {}),
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
    config_file = f"schemas/{name}.yaml"
    schema_config = config_loader.load_yaml(config_file)

    if schema_config:
        logger.warning(f"Using config file for schema '{name}': {config_file}")
        schema_data = dict(schema_config)
        schema_data["source"] = "file_fallback"
        schema_data["asset_id"] = None
        schema_data["version"] = None
        track_schema_asset(
            {
                "asset_id": None,
                "name": name,
                "version": None,
                "source": "file_fallback",
            }
        )
        return schema_data

    logger.warning(f"Schema asset not found: {name}")
    return None


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


def load_screen_asset(
    name: str, version: int | None = None
) -> dict[str, Any] | None:
    """Load screen asset with fallback priority.

    Priority:
    1. DB (specific version or published screen asset)
    2. File (resources/screens/{name}.json)
    3. None (not found)

    Args:
        name: Asset name
        version: Specific version to load (None for published)
    """
    try:
        from core.db import get_session
        from sqlmodel import select

        from app.modules.asset_registry.models import TbAssetRegistry

        with get_session() as session:
            query = (
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "screen")
                .where(TbAssetRegistry.name == name)
            )

            if version is not None:
                query = query.where(TbAssetRegistry.version == version)
            else:
                query = query.where(TbAssetRegistry.status == "published")

            asset = session.exec(query).first()

            if asset:
                logger.info(f"Screen asset loaded from DB: {name} (v{asset.version})")
                return {
                    "asset_id": str(asset.asset_id),
                    "name": asset.name,
                    "screen_id": asset.screen_id,
                    "description": asset.description,
                    "screen_schema": asset.screen_schema,
                    "tags": asset.tags,
                    "version": asset.version,
                    "source": "db",
                }
    except Exception as e:
        logger.debug(f"Failed to load screen asset from DB: {e}")

    # Fallback to file
    try:
        import json
        from pathlib import Path

        resource_dir = Path(__file__).resolve().parents[2] / "resources" / "screens"
        screen_file = resource_dir / f"{name}.json"

        if screen_file.exists():
            with open(screen_file, "r") as f:
                data = json.load(f)
            logger.info(f"Screen asset loaded from file: {name}")
            return {
                "asset_id": None,
                "name": name,
                "screen_schema": data,
                "version": None,
                "source": "file",
            }
    except Exception as e:
        logger.debug(f"Failed to load screen asset from file: {e}")

    logger.warning(f"Screen asset not found: {name}")
    return None
