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

from app.core.db import get_session_context
from app.modules.asset_registry.crud import (
    create_resolver_asset,
    create_schema_asset,
    create_source_asset,
    publish_asset,
)
from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.asset_registry.resolver_models import (
    AliasMapping,
    PatternRule,
    ResolverAssetCreate,
    ResolverConfig,
    ResolverRule,
    ResolverType,
    TransformationRule,
)
from app.modules.asset_registry.schema_models import SchemaAssetCreate, SchemaCatalog
from app.modules.asset_registry.source_models import (
    SourceAssetCreate,
    SourceConnection,
    SourceType,
)
from app.shared.config_loader import load_yaml

RESOURCES_DIR = ROOT / "resources"
SOURCE_DIR = "sources"
SCHEMA_DIR = "schemas"
RESOLVER_DIR = "resolvers"


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
        .where(TbAssetRegistry.asset_type == "schema")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
    ).first()
    if existing and not force:
        return False

    catalog_payload = payload.get("catalog") or {}
    catalog = SchemaCatalog(**catalog_payload) if catalog_payload else None
    schema_data = SchemaAssetCreate(
        name=payload.get("name", name),
        description=payload.get("description"),
        source_ref=payload.get("source_ref", ""),
        scope=payload.get("scope"),
        tags=payload.get("tags") or {},
    )
    if catalog is not None:
        setattr(schema_data, "catalog", catalog)
    created = create_schema_asset(session, schema_data, created_by="seed")
    publish_asset(session, created, published_by="seed")
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
    resolver_data = ResolverAssetCreate(
        name=payload.get("name", name),
        description=payload.get("description"),
        config=config,
        scope=payload.get("scope"),
        tags=payload.get("tags") or {},
    )
    created = create_resolver_asset(session, resolver_data, created_by="seed")
    publish_asset(session, created, published_by="seed")
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
        .where(TbAssetRegistry.asset_type == "schema")
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
        default="source,schema,resolver",
        help="Comma-separated asset types to process (source,schema,resolver).",
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

        if args.export_resources:
            if "source" in selected_types:
                _export_sources(session)
            if "schema" in selected_types:
                _export_schemas(session)
            if "resolver" in selected_types:
                _export_resolvers(session)


if __name__ == "__main__":
    main()
