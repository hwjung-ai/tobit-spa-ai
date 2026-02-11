from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml
from sqlmodel import select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.crud import (
    create_asset,
    create_source_asset,
    publish_asset,
)
from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.asset_registry.resolver_models import (
    AliasMapping,
    PatternRule,
    ResolverConfig,
    ResolverRule,
    ResolverType,
    TransformationRule,
)
from app.modules.asset_registry.schema_models import SchemaAssetCreate
from app.modules.asset_registry.source_models import (
    SourceAssetCreate,
    SourceConnection,
    SourceType,
)
from app.shared.config_loader import load_yaml
from core.db import get_session_context

RESOURCES_DIR = ROOT / "resources"
SOURCE_DIR = "sources"
SCHEMA_DIR = "schemas"
RESOLVER_DIR = "resolvers"
QUERY_DIR = "queries"
POLICY_DIR = "policies"
PROMPT_DIR = "prompts"
MAPPING_DIR = "mappings"


def _load_resource_names(folder: str) -> list[str]:
    base = RESOURCES_DIR / folder
    if not base.exists():
        return []
    return sorted([path.stem for path in base.glob("*.yaml") if path.is_file()])


def _safe_dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


def _strip_secret_fields(connection: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(connection)
    if "password_encrypted" in sanitized:
        sanitized["password_encrypted"] = None
    return sanitized


def _seed_source(session, name: str, force: bool) -> bool:
    payload = load_yaml(f"{SOURCE_DIR}/{name}.yaml")
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "source")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    connection = payload.get("connection") or {}
    source_data = SourceAssetCreate(
        name=payload.get("name", name),
        description=payload.get("description"),
        source_type=SourceType(payload.get("source_type", "postgresql")),
        connection=SourceConnection(**connection),
        scope=payload.get("scope"),
        tags=payload.get("tags") or {},
    )
    created = create_source_asset(session, source_data, created_by="seed")
    publish_asset(session, created, published_by="seed")
    return True


def _seed_schema(session, name: str, force: bool) -> bool:
    payload = load_yaml(f"{SCHEMA_DIR}/{name}.yaml")
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "catalog")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    catalog_payload = payload.get("catalog") or {}
    schema_data = SchemaAssetCreate(
        name=payload.get("name", name),
        description=payload.get("description"),
        source_ref=payload.get("source_ref", ""),
        scope=payload.get("scope"),
        tags=payload.get("tags") or {},
    )
    # Create TbAssetRegistry record directly
    from app.modules.asset_registry.crud import update_asset

    asset = create_asset(
        session=session,
        name=schema_data.name,
        asset_type="catalog",
        description=schema_data.description,
        scope=schema_data.scope,
        tags=schema_data.tags,
        created_by="seed",
    )

    # Store schema data in content field
    content = {
        "source_ref": schema_data.source_ref,
        "catalog": catalog_payload,
        "spec": None,
    }

    update_asset(
        session=session,
        asset=asset,
        updates={"content": content},
        updated_by="seed",
    )

    publish_asset(session, asset, published_by="seed")
    return True


def _parse_resolver_rules(raw_rules: Iterable[dict[str, Any]]) -> list[ResolverRule]:
    parsed: list[ResolverRule] = []
    for rule in raw_rules:
        rule_type = ResolverType(rule.get("rule_type"))
        rule_data = rule.get("rule_data") or {}
        if rule_type == ResolverType.ALIAS_MAPPING:
            resolved_rule_data = AliasMapping(**rule_data)
        elif rule_type == ResolverType.PATTERN_RULE:
            resolved_rule_data = PatternRule(**rule_data)
        else:
            resolved_rule_data = TransformationRule(**rule_data)
        parsed.append(
            ResolverRule(
                rule_type=rule_type,
                name=rule.get("name", resolved_rule_data.name),
                description=rule.get("description"),
                is_active=rule.get("is_active", True),
                priority=rule.get("priority", 0),
                extra_metadata=rule.get("extra_metadata") or {},
                rule_data=resolved_rule_data,
            )
        )
    return parsed


def _seed_resolver(session, name: str, force: bool) -> bool:
    payload = load_yaml(f"{RESOLVER_DIR}/{name}.yaml")
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "resolver")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    rules = _parse_resolver_rules(payload.get("rules") or [])
    config = ResolverConfig(
        name=payload.get("name", name),
        description=payload.get("description"),
        rules=rules,
        default_namespace=payload.get("default_namespace"),
        tags=payload.get("tags") or {},
    )
    # Create TbAssetRegistry record directly
    asset = create_asset(
        session=session,
        name=payload.get("name", name),
        asset_type="resolver",
        description=payload.get("description"),
        scope=payload.get("scope"),
        tags=payload.get("tags") or {},
        created_by="seed",
    )

    # Store resolver data in content field
    content = {
        "rules": [rule.model_dump() for rule in rules],
        "default_namespace": payload.get("default_namespace"),
        "spec": None,
    }

    from app.modules.asset_registry.crud import update_asset
    update_asset(
        session=session,
        asset=asset,
        updates={"content": content},
        updated_by="seed",
    )

    publish_asset(session, asset, published_by="seed")
    return True


def _seed_query(session, scope: str, name: str, force: bool) -> bool:
    """Seed a query asset from YAML and SQL files"""
    # Load YAML metadata
    yaml_path = f"queries/postgres/{scope}/{name}.yaml"
    payload = load_yaml(yaml_path)
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "query")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.scope == scope)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    # Load SQL content
    from app.shared.config_loader import load_text
    sql_path = f"queries/postgres/{scope}/{name}.sql"
    query_sql = load_text(sql_path) or ""

    # Import QueryAssetCreate locally to avoid circular imports
    from app.modules.asset_registry.crud import create_asset

    # Convert tags list to dict if needed
    tags = payload.get("tags", {})
    if isinstance(tags, list):
        tags = {"tags": tags}

    # Create the asset directly using create_asset
    asset = create_asset(
        session=session,
        name=payload.get("name", name),
        asset_type="query",
        description=payload.get("description"),
        scope=payload.get("scope", scope),
        query_sql=query_sql,
        query_params=payload.get("query_params", {}),
        query_metadata=payload.get("query_metadata", {}),
        tags=tags,
        created_by="seed",
    )
    publish_asset(session, asset, published_by="seed")
    return True


def _seed_policy(session, name: str, force: bool) -> bool:
    """Seed a policy asset from YAML file"""
    payload = load_yaml(f"{POLICY_DIR}/{name}.yaml")
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "policy")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    # Create TbAssetRegistry record directly
    asset = create_asset(
        session=session,
        name=payload.get("name", name),
        asset_type="policy",
        description=payload.get("description"),
        scope=payload.get("scope"),
        policy_type=payload.get("policy_type"),
        limits=payload.get("limits"),
        tags=payload.get("tags") or {},
        created_by="seed",
    )

    # Store additional data in content field
    content = {
        "policy_type": payload.get("policy_type"),
        "limits": payload.get("limits"),
        "metadata": payload.get("metadata"),
        "spec": None,
    }

    from app.modules.asset_registry.crud import update_asset
    update_asset(
        session=session,
        asset=asset,
        updates={"content": content},
        updated_by="seed",
    )

    publish_asset(session, asset, published_by="seed")
    return True


def _seed_prompt(session, scope: str, name: str, force: bool) -> bool:
    """Seed a prompt asset from YAML file"""
    # Load YAML metadata
    yaml_path = f"{PROMPT_DIR}/{scope}/{name}.yaml"
    payload = load_yaml(yaml_path)
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "prompt")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.scope == scope)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    # Convert templates to template string format
    templates = payload.get("templates", {})
    template_str = _format_prompt_template(templates)
    params = payload.get("params", [])

    # Derive engine from prompt name
    valid_engines = [
        "planner",
        "compose",
        "langgraph",
        "response_builder",
        "validator",
        "all_router",
        "graph_router",
        "history_router",
        "metric_router",
    ]
    # Try to find matching engine from name or use the prompt name directly
    engine = payload.get("engine")
    if not engine:
        # Check if name matches any valid engine
        if name in valid_engines:
            engine = name
        else:
            # Fallback to using the prompt name as engine
            engine = name

    # Create input_schema with 'question' property for validation
    input_schema = {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"],
    }

    # Create output_contract with 'plan' property for validation
    # Also include templates and params for the loader to use
    output_contract = {
        "type": "object",
        "properties": {
            "plan": {
                "type": "object",
                "properties": {
                    "steps": {"type": "array"},
                    "policy": {"type": "object"},
                },
            }
        },
        "templates": templates,  # For loader: output_contract.get("templates")
        "params": params,         # For loader: output_contract.get("params")
    }

    # Create TbAssetRegistry record directly
    asset = create_asset(
        session=session,
        name=payload.get("name", name),
        asset_type="prompt",
        scope=scope,
        engine=engine,
        template=template_str,
        input_schema=input_schema,
        output_contract=output_contract,
        tags=payload.get("tags") or {},
        created_by="seed",
    )

    publish_asset(session, asset, published_by="seed")
    return True


def _format_prompt_template(templates: dict[str, str]) -> str:
    """Format templates dict into a single template string"""
    parts = []
    for role, template in templates.items():
        parts.append(f"### {role.upper()}\n{template}")
    return "\n\n".join(parts)


def _seed_mapping(session, name: str, force: bool) -> bool:
    """Seed a mapping asset from YAML file"""
    payload = load_yaml(f"{MAPPING_DIR}/{name}.yaml")
    if not payload:
        return False

    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "mapping")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    # Store the content from YAML directly
    mapping_content = payload.get("content") or {}

    # Create TbAssetRegistry record directly
    asset = create_asset(
        session=session,
        name=payload.get("name", name),
        asset_type="mapping",
        description=payload.get("description"),
        scope=payload.get("scope"),
        mapping_type=payload.get("mapping_type"),
        content=mapping_content,
        tags=payload.get("tags") or {},
        created_by="seed",
    )

    publish_asset(session, asset, published_by="seed")
    return True


def _export_sources(session) -> int:
    assets = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "source")
        .where(TbAssetRegistry.status == "published")
    ).all()
    count = 0
    for asset in assets:
        content = asset.content or {}
        connection = _strip_secret_fields(content.get("connection") or {})
        payload = {
            "name": asset.name,
            "description": asset.description,
            "source_type": content.get("source_type"),
            "connection": connection,
            "scope": asset.scope,
            "tags": asset.tags or {},
        }
        path = RESOURCES_DIR / SOURCE_DIR / f"{asset.name}.yaml"
        _safe_dump_yaml(path, payload)
        count += 1
    return count


def _export_schemas(session) -> int:
    assets = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "catalog")
        .where(TbAssetRegistry.status == "published")
    ).all()
    count = 0
    for asset in assets:
        content = asset.content or {}
        payload = {
            "name": asset.name,
            "description": asset.description,
            "source_ref": content.get("source_ref"),
            "catalog": content.get("catalog") or {},
            "scope": asset.scope,
            "tags": asset.tags or {},
        }
        path = RESOURCES_DIR / SCHEMA_DIR / f"{asset.name}.yaml"
        _safe_dump_yaml(path, payload)
        count += 1
    return count


def _export_resolvers(session) -> int:
    assets = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "resolver")
        .where(TbAssetRegistry.status == "published")
    ).all()
    count = 0
    for asset in assets:
        content = asset.content or {}
        payload = {
            "name": asset.name,
            "description": asset.description,
            "default_namespace": content.get("default_namespace"),
            "rules": content.get("rules") or [],
            "scope": asset.scope,
            "tags": asset.tags or {},
        }
        path = RESOURCES_DIR / RESOLVER_DIR / f"{asset.name}.yaml"
        _safe_dump_yaml(path, payload)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed asset registry from resources and/or export fallback YAMLs."
    )
    parser.add_argument(
        "--import-resources",
        action="store_true",
        help="Import resources into DB (published).",
    )
    parser.add_argument(
        "--export-resources",
        action="store_true",
        help="Export published assets to resources YAML.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite published assets by creating a new version.",
    )
    parser.add_argument(
        "--types",
        default="source,schema,resolver,query,policy,prompt,mapping",
        help="Comma-separated asset types to process (source,schema,resolver,query,policy,prompt,mapping).",
    )
    args = parser.parse_args()

    selected_types = {t.strip() for t in args.types.split(",") if t.strip()}
    if not args.import_resources and not args.export_resources:
        args.import_resources = True

    with get_session_context() as session:
        if args.import_resources:
            if "source" in selected_types:
                for name in _load_resource_names(SOURCE_DIR):
                    _seed_source(session, name, args.force)
            if "schema" in selected_types:
                for name in _load_resource_names(SCHEMA_DIR):
                    _seed_schema(session, name, args.force)
            if "resolver" in selected_types:
                for name in _load_resource_names(RESOLVER_DIR):
                    _seed_resolver(session, name, args.force)
            if "query" in selected_types:
                # Seed query assets from queries/postgres/{scope}/*.sql
                query_base = RESOURCES_DIR / "queries" / "postgres"
                if query_base.exists():
                    for scope_dir in query_base.iterdir():
                        if scope_dir.is_dir():
                            scope = scope_dir.name
                            for sql_file in scope_dir.glob("*.sql"):
                                name = sql_file.stem
                                _seed_query(session, scope, name, args.force)
            if "policy" in selected_types:
                for name in _load_resource_names(POLICY_DIR):
                    _seed_policy(session, name, args.force)
            if "prompt" in selected_types:
                # Seed prompt assets from prompts/{scope}/*.yaml
                prompt_base = RESOURCES_DIR / "prompts"
                if prompt_base.exists():
                    for scope_dir in prompt_base.iterdir():
                        if scope_dir.is_dir():
                            scope = scope_dir.name
                            for yaml_file in scope_dir.glob("*.yaml"):
                                name = yaml_file.stem
                                _seed_prompt(session, scope, name, args.force)
            if "mapping" in selected_types:
                for name in _load_resource_names(MAPPING_DIR):
                    _seed_mapping(session, name, args.force)

        if args.export_resources:
            if "source" in selected_types:
                _export_sources(session)
            if "schema" in selected_types:
                _export_schemas(session)
            if "resolver" in selected_types:
                _export_resolvers(session)


if __name__ == "__main__":
    main()
