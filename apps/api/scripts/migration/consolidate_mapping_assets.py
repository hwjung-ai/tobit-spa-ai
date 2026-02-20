#!/usr/bin/env python
"""
Consolidate OPS mapping assets into unified planner mappings.

This migration:
1. Creates/updates published `planner_keywords` mapping asset
2. Creates/updates published `planner_defaults` mapping asset
3. Deletes legacy mapping assets that were merged

Kept mappings after migration:
- planner_keywords
- planner_defaults
- graph_relation
- graph_relation_allowlist
- default_output_format
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context

LEGACY_KEYWORD_MAPPING_NAMES = [
    "metric_aliases",
    "agg_keywords",
    "series_keywords",
    "history_keywords",
    "list_keywords",
    "table_hints",
    "cep_keywords",
    "graph_scope_keywords",
    "auto_keywords",
    "filterable_fields",
    "graph_view_keywords",
    "auto_view_preferences",
]

LEGACY_DEFAULT_MAPPING_NAMES = [
    "output_type_priorities",
]

KEEP_MAPPING_NAMES = {
    "planner_keywords",
    "planner_defaults",
    "graph_relation",
    "graph_relation_allowlist",
    "default_output_format",
}

KEYWORD_DEFAULTS: dict[str, dict[str, Any]] = {
    "metric_aliases": {
        "aliases": {
            "cpu": "cpu_usage",
            "memory": "memory_usage",
            "disk": "disk_usage",
            "latency": "latency",
            "error": "error_rate",
        },
        "keywords": ["cpu", "memory", "disk", "latency", "error"],
    },
    "agg_keywords": {
        "mappings": {
            "avg": "avg",
            "average": "avg",
            "mean": "avg",
            "sum": "sum",
            "total": "sum",
            "max": "max",
            "min": "min",
            "count": "count",
        }
    },
    "series_keywords": {"keywords": ["trend", "timeseries", "series", "over time"]},
    "history_keywords": {
        "keywords": ["history", "event", "log", "recent"],
        "time_map": {
            "today": "last_24h",
            "last day": "last_24h",
            "last week": "last_7d",
            "last month": "last_30d",
            "all time": "all_time",
        },
    },
    "list_keywords": {"keywords": ["list", "show", "top", "all"]},
    "table_hints": {"keywords": ["table", "rows", "columns"]},
    "cep_keywords": {"keywords": ["cep", "pattern", "rule"]},
    "graph_scope_keywords": {
        "scope_keywords": ["dependency", "impact", "neighbors", "path"],
        "metric_keywords": ["metric", "latency", "error", "cpu", "memory"],
    },
    "auto_keywords": {"keywords": ["auto", "automatically"]},
    "filterable_fields": {
        "tag_filter_keys": ["env", "service", "team", "region", "tier"],
        "attr_filter_keys": ["ci_type", "status", "severity", "source", "category"],
    },
    "graph_view_keywords": {
        "view_keyword_map": {
            "dependency": "DEPENDENCY",
            "impact": "IMPACT",
            "neighbors": "NEIGHBORS",
            "path": "PATH",
            "composition": "COMPOSITION",
            "summary": "SUMMARY",
        },
        "default_depths": {
            "DEPENDENCY": 2,
            "IMPACT": 2,
            "NEIGHBORS": 1,
            "PATH": 2,
            "COMPOSITION": 2,
            "SUMMARY": 1,
        },
        "force_keywords": ["dependency map", "impact map", "path between"],
    },
    "auto_view_preferences": {
        "preferences": [
            {"keywords": ["dependency", "depends on"], "views": ["DEPENDENCY"]},
            {"keywords": ["impact", "affected"], "views": ["IMPACT"]},
            {"keywords": ["path", "route"], "views": ["PATH"]},
            {"keywords": ["neighbors", "around"], "views": ["NEIGHBORS"]},
        ]
    },
}

DEFAULT_DEFAULTS: dict[str, dict[str, Any]] = {
    "output_type_priorities": {"global_priorities": ["text", "table", "chart", "network", "number"]}
}


def _latest_published_mapping(session, name: str) -> TbAssetRegistry | None:
    return session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "mapping")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
        .order_by(TbAssetRegistry.updated_at.desc())
    ).first()


def _load_content_or_default(session, name: str, default: dict[str, Any]) -> dict[str, Any]:
    asset = _latest_published_mapping(session, name)
    if asset and isinstance(asset.content, dict):
        return dict(asset.content)
    return default


def _build_planner_keywords_payload(session) -> dict[str, Any]:
    existing = _load_content_or_default(session, "planner_keywords", {})
    payload: dict[str, Any] = {}

    for mapping_name in LEGACY_KEYWORD_MAPPING_NAMES:
        legacy = _latest_published_mapping(session, mapping_name)
        if legacy and isinstance(legacy.content, dict):
            payload[mapping_name] = dict(legacy.content)
            continue

        existing_value = existing.get(mapping_name)
        if isinstance(existing_value, dict):
            payload[mapping_name] = dict(existing_value)
            continue

        payload[mapping_name] = dict(KEYWORD_DEFAULTS[mapping_name])
    return payload


def _build_planner_defaults_payload(session) -> dict[str, Any]:
    existing = _load_content_or_default(session, "planner_defaults", {})
    payload: dict[str, Any] = {}

    for mapping_name in LEGACY_DEFAULT_MAPPING_NAMES:
        legacy = _latest_published_mapping(session, mapping_name)
        if legacy and isinstance(legacy.content, dict):
            payload[mapping_name] = dict(legacy.content)
            continue

        existing_value = existing.get(mapping_name)
        if isinstance(existing_value, dict):
            payload[mapping_name] = dict(existing_value)
            continue

        payload[mapping_name] = dict(DEFAULT_DEFAULTS[mapping_name])
    return payload


def _upsert_published_mapping(
    session,
    *,
    name: str,
    scope: str,
    content: dict[str, Any],
    description: str,
    actor: str,
    tenant_id: str,
) -> TbAssetRegistry:
    now = datetime.now()
    existing = _latest_published_mapping(session, name)
    if existing:
        existing.content = content
        existing.description = description
        existing.scope = scope
        existing.mapping_type = name
        existing.updated_at = now
        existing.published_by = actor
        existing.published_at = now
        existing.status = "published"
        existing.tenant_id = tenant_id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        print(f"  ✓ Updated published mapping: {name} (id={existing.asset_id})")
        return existing

    created = TbAssetRegistry(
        asset_type="mapping",
        name=name,
        description=description,
        version=1,
        status="published",
        scope=scope,
        mapping_type=name,
        content=content,
        is_system=True,
        created_by=actor,
        published_by=actor,
        published_at=now,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    session.add(created)
    session.commit()
    session.refresh(created)
    print(f"  ✓ Created published mapping: {name} (id={created.asset_id})")
    return created


def consolidate_mappings(actor: str = "mapping_consolidation_script") -> None:
    tenant_id = "default"
    with get_session_context() as session:
        print("\n1) Building unified planner mapping payloads...")
        planner_keywords = _build_planner_keywords_payload(session)
        planner_defaults = _build_planner_defaults_payload(session)
        print("  ✓ Payloads prepared")

        print("\n2) Upserting unified published mapping assets...")
        _upsert_published_mapping(
            session,
            name="planner_keywords",
            scope="ops",
            content=planner_keywords,
            description="Unified planner keyword mapping for OPS orchestration",
            actor=actor,
            tenant_id=tenant_id,
        )
        _upsert_published_mapping(
            session,
            name="planner_defaults",
            scope="ops",
            content=planner_defaults,
            description="Unified planner defaults mapping for OPS orchestration",
            actor=actor,
            tenant_id=tenant_id,
        )

        print("\n3) Deleting legacy mapping assets...")
        delete_targets = set(LEGACY_KEYWORD_MAPPING_NAMES + LEGACY_DEFAULT_MAPPING_NAMES) - KEEP_MAPPING_NAMES
        legacy_rows = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.name.in_(delete_targets))
        ).all()
        for row in legacy_rows:
            session.delete(row)
        session.commit()
        print(f"  ✓ Deleted {len(legacy_rows)} legacy mapping assets")

        print("\n4) Final mapping inventory:")
        final_rows = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .order_by(TbAssetRegistry.name, TbAssetRegistry.version.desc())
        ).all()
        for row in final_rows:
            marker = "KEEP" if row.name in KEEP_MAPPING_NAMES else "OTHER"
            print(f"  - [{marker}] {row.name} v{row.version} ({row.status}) scope={row.scope}")

    print("\n✅ Mapping consolidation completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidate OPS mapping assets")
    parser.add_argument("--actor", default="mapping_consolidation_script")
    args = parser.parse_args()
    consolidate_mappings(actor=args.actor)
