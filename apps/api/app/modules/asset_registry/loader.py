from __future__ import annotations

import logging
from typing import Any

from sqlmodel import Session, select

from app.shared import config_loader
from core.db import get_session_context
from .models import TbAssetRegistry

logger = logging.getLogger(__name__)


def load_prompt_asset(scope: str, engine: str, name: str) -> dict[str, Any] | None:
    """
    Load prompt asset with fallback priority:
    1. Published asset from DB
    2. File from resources/prompts/
    """
    with get_session_context() as session:
        # Try DB first
        asset = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == scope)
            .where(TbAssetRegistry.engine == engine)
            .where(TbAssetRegistry.name == name)
            .where(TbAssetRegistry.status == "published")
        ).first()

        if asset:
            logger.info(f"Loaded prompt from asset registry: {name} (v{asset.version})")
            return {
                "version": asset.version,
                "name": asset.name,
                "templates": {"system": asset.template},
                "params": list(asset.input_schema.get("properties", {}).keys()),
                "source": "asset_registry",
            }

    # Fallback to file
    file_path = f"prompts/{scope}/{engine}.yaml"
    prompt_data = config_loader.load_yaml(file_path)

    if prompt_data:
        logger.warning(f"Using fallback file for prompt '{name}': resources/{file_path}")
        prompt_data["source"] = "file_fallback"
        return prompt_data

    logger.warning(f"Prompt asset not found: {name} (scope={scope}, engine={engine})")
    return None


def load_mapping_asset(mapping_type: str = "graph_relation") -> dict[str, Any] | None:
    """
    Load mapping asset with fallback priority:
    1. Published asset from DB
    2. File from resources/
    """
    with get_session_context() as session:
        asset = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.mapping_type == mapping_type)
            .where(TbAssetRegistry.status == "published")
        ).first()

        if asset:
            logger.info(f"Loaded mapping from asset registry: {asset.name} (v{asset.version})")
            return asset.content

    # Fallback to file
    file_path = "app/modules/ops/services/ci/relation_mapping.yaml"
    mapping_data = config_loader.load_yaml(file_path)

    if mapping_data:
        logger.warning(f"Using fallback file for mapping: {file_path}")
        return mapping_data

    logger.warning(f"Mapping asset not found: {mapping_type}")
    return None


def load_policy_asset(policy_type: str = "plan_budget") -> dict[str, Any] | None:
    """
    Load policy asset with fallback priority:
    1. Published asset from DB
    2. Hardcoded defaults
    """
    with get_session_context() as session:
        asset = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "policy")
            .where(TbAssetRegistry.policy_type == policy_type)
            .where(TbAssetRegistry.status == "published")
        ).first()

        if asset:
            logger.info(f"Loaded policy from asset registry: {asset.name} (v{asset.version})")
            return asset.limits

    # Fallback to defaults
    logger.info(f"Using default policy for {policy_type}")
    return {
        "max_steps": 10,
        "timeout_ms": 120000,  # 2 minutes
        "max_depth": 5,
    }


def load_query_asset(scope: str, name: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Load query asset with fallback priority:
    1. Published asset from DB
    2. File from resources/queries/

    Returns:
        Tuple of (asset_data, asset_id_version_str)
        asset_id_version_str format: "{asset_id}:v{version}" for tracking
    """
    with get_session_context() as session:
        # Try DB first
        asset = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "query")
            .where(TbAssetRegistry.scope == scope)
            .where(TbAssetRegistry.name == name)
            .where(TbAssetRegistry.status == "published")
        ).first()

        if asset:
            logger.info(f"Loaded query from asset registry: {name} (v{asset.version})")
            asset_identifier = f"{str(asset.asset_id)}:v{asset.version}"
            return {
                "sql": asset.query_sql,
                "params": asset.query_params or {},
                "metadata": asset.query_metadata or {},
                "source": "asset_registry",
            }, asset_identifier

    # Fallback to file
    file_path = f"queries/{scope}/{name}.sql"
    query_text = config_loader.load_text(file_path)

    if query_text:
        logger.warning(f"Using fallback file for query '{name}': resources/{file_path}")
        return {
            "sql": query_text,
            "params": {},
            "metadata": {"seed_file": file_path},
            "source": "file_fallback",
        }, None

    logger.warning(f"Query asset not found: {name} (scope={scope})")
    return None, None
