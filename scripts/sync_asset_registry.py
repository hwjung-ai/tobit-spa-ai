#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlmodel import select

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
sys.path.append(str(API_ROOT))

from app.modules.asset_registry.crud import (  # noqa: E402
    create_resolver_asset,
    create_schema_asset,
    create_source_asset,
    get_asset,
    list_assets,
    publish_asset,
)
from app.modules.asset_registry.models import TbAssetRegistry  # noqa: E402
from app.modules.asset_registry.resolver_models import ResolverAssetCreate, ResolverConfig  # noqa: E402
from app.modules.asset_registry.schema_models import SchemaAssetCreate, SchemaCatalog  # noqa: E402
from app.modules.asset_registry.source_models import SourceAssetCreate, SourceConnection, SourceType  # noqa: E402
from core.config import get_settings  # noqa: E402
from core.db import get_session_context  # noqa: E402

RESOURCES = API_ROOT / "resources"


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _published_exists(session, asset_type: str, **filters: Any) -> bool:
    statement = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == asset_type)
    for key, value in filters.items():
        column = getattr(TbAssetRegistry, key)
        statement = statement.where(column == value)
    statement = statement.where(TbAssetRegistry.status == "published")
    return session.exec(statement).first() is not None


def _create_or_skip(session, asset: TbAssetRegistry) -> None:
    session.add(asset)
    session.commit()


def import_prompts(session, actor: str) -> None:
    prompt_root = RESOURCES / "prompts"
    if not prompt_root.exists():
        return

    for scope_dir in prompt_root.iterdir():
        if not scope_dir.is_dir():
            continue
        scope = scope_dir.name
        for prompt_file in scope_dir.glob("*.yaml"):
            data = _load_yaml(prompt_file)
            name = data.get("name") or f"{scope}_{prompt_file.stem}"
            engine = prompt_file.stem
            templates = data.get("templates") or {}
            system_template = templates.get("system") or next(iter(templates.values()), None)
            params = data.get("params") or []
            if not system_template:
                continue
            if _published_exists(session, "prompt", name=name, scope=scope, engine=engine):
                continue
            input_schema = {
                "type": "object",
                "properties": {param: {"type": "string"} for param in params},
                "required": list(params),
            }
            output_contract = {
                "templates": templates,
                "params": params,
                "metadata": {
                    "source_file": str(prompt_file.relative_to(RESOURCES)),
                    "seeded_at": datetime.utcnow().isoformat(),
                },
            }
            asset = TbAssetRegistry(
                asset_type="prompt",
                name=name,
                description=data.get("description"),
                scope=scope,
                engine=engine,
                template=system_template,
                input_schema=input_schema,
                output_contract=output_contract,
                status="published",
                created_by=actor,
                published_by=actor,
                published_at=datetime.utcnow(),
            )
            _create_or_skip(session, asset)


def import_mappings(session, actor: str) -> None:
    mapping_root = RESOURCES / "mappings"
    if not mapping_root.exists():
        return
    for mapping_file in mapping_root.glob("*.yaml"):
        data = _load_yaml(mapping_file)
        name = data.get("name") or mapping_file.stem
        mapping_type = data.get("mapping_type") or name
        if _published_exists(session, "mapping", mapping_type=mapping_type):
            continue
        asset = TbAssetRegistry(
            asset_type="mapping",
            name=name,
            description=data.get("description"),
            mapping_type=mapping_type,
            content=data.get("content") or {},
            status="published",
            created_by=actor,
            published_by=actor,
            published_at=datetime.utcnow(),
        )
        _create_or_skip(session, asset)


def import_policies(session, actor: str) -> None:
    policy_root = RESOURCES / "policies"
    if not policy_root.exists():
        return
    for policy_file in policy_root.glob("*.yaml"):
        data = _load_yaml(policy_file)
        name = data.get("name") or policy_file.stem
        policy_type = data.get("policy_type") or name
        if _published_exists(session, "policy", policy_type=policy_type):
            continue
        asset = TbAssetRegistry(
            asset_type="policy",
            name=name,
            description=data.get("description"),
            policy_type=policy_type,
            limits=data.get("limits") or {},
            status="published",
            created_by=actor,
            published_by=actor,
            published_at=datetime.utcnow(),
        )
        _create_or_skip(session, asset)


def import_queries(session, actor: str) -> None:
    query_root = RESOURCES / "queries"
    if not query_root.exists():
        return
    for scope_dir in query_root.iterdir():
        if not scope_dir.is_dir():
            continue
        scope = scope_dir.name
        for sql_file in scope_dir.rglob("*.sql"):
            name = sql_file.stem
            yaml_file = sql_file.with_suffix(".yaml")
            metadata = _load_yaml(yaml_file) if yaml_file.exists() else {}
            if _published_exists(session, "query", scope=scope, name=name):
                continue
            asset = TbAssetRegistry(
                asset_type="query",
                name=name,
                description=metadata.get("description"),
                scope=scope,
                query_sql=_load_text(sql_file),
                query_params={"parameters": metadata.get("parameters") or []},
                query_metadata={
                    "metadata": metadata,
                    "source_file": str(sql_file.relative_to(RESOURCES)),
                },
                status="published",
                created_by=actor,
                published_by=actor,
                published_at=datetime.utcnow(),
            )
            _create_or_skip(session, asset)


def import_source_schema_resolver(session, actor: str) -> None:
    settings = get_settings()
    source_name = settings.ops_default_source_asset or "primary_postgres"
    schema_name = settings.ops_default_schema_asset or "primary_postgres_schema"
    resolver_name = settings.ops_default_resolver_asset or "default_resolver"

    if not _published_exists(session, "source", name=source_name):
        source_payload = SourceAssetCreate(
            name=source_name,
            description="Primary PostgreSQL source",
            source_type=SourceType.POSTGRESQL,
            connection=SourceConnection(
                host=settings.pg_host or "localhost",
                port=settings.pg_port,
                username=settings.pg_user or "postgres",
                database=settings.pg_db or "postgres",
                secret_key_ref="env:PG_PASSWORD",
                timeout=30,
                ssl_mode="verify-full",
                connection_params={},
            ),
            scope="default",
            tags={"seeded": True},
        )
        source = create_source_asset(session, source_payload, created_by=actor)
        registry = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "source")
            .where(TbAssetRegistry.name == source.name)
            .order_by(TbAssetRegistry.created_at.desc())
        ).first()
        if registry:
            publish_asset(session, registry, published_by=actor)

    source_registry = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "source")
        .where(TbAssetRegistry.name == source_name)
        .where(TbAssetRegistry.status == "published")
    ).first()

    if source_registry and not _published_exists(session, "schema", name=schema_name):
        schema_payload = SchemaAssetCreate(
            name=schema_name,
            description="Schema catalog for primary source",
            source_ref=str(source_registry.asset_id),
            scope="default",
            tags={"seeded": True},
        )
        schema = create_schema_asset(session, schema_payload, created_by=actor)
        registry = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "schema")
            .where(TbAssetRegistry.name == schema.name)
            .order_by(TbAssetRegistry.created_at.desc())
        ).first()
        if registry:
            publish_asset(session, registry, published_by=actor)

    if not _published_exists(session, "resolver", name=resolver_name):
        resolver_payload = ResolverAssetCreate(
            name=resolver_name,
            description="Default resolver with no rules",
            config=ResolverConfig(name=resolver_name, rules=[], default_namespace="default"),
            scope="default",
            tags={"seeded": True},
        )
        resolver = create_resolver_asset(session, resolver_payload, created_by=actor)
        registry = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "resolver")
            .where(TbAssetRegistry.name == resolver.name)
            .order_by(TbAssetRegistry.created_at.desc())
        ).first()
        if registry:
            publish_asset(session, registry, published_by=actor)


def main() -> None:
    actor = "system"
    with get_session_context() as session:
        import_prompts(session, actor)
        import_mappings(session, actor)
        import_policies(session, actor)
        import_queries(session, actor)
        import_source_schema_resolver(session, actor)


if __name__ == "__main__":
    main()
