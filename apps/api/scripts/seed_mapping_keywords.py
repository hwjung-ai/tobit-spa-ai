#!/usr/bin/env python3
"""Seed unified OPS planner mapping assets directly into DB."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context

PLANNER_KEYWORDS_TEMPLATE: dict[str, Any] = {
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

PLANNER_DEFAULTS_TEMPLATE: dict[str, Any] = {
    "output_type_priorities": {
        "global_priorities": ["text", "table", "chart", "network", "number"],
    }
}


def _upsert_published_mapping(
    session,
    *,
    name: str,
    scope: str,
    content: dict[str, Any],
    description: str,
    actor: str,
    tenant_id: str,
) -> None:
    now = datetime.now()
    current = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "mapping")
        .where(TbAssetRegistry.name == name)
        .where(TbAssetRegistry.status == "published")
        .order_by(TbAssetRegistry.updated_at.desc())
    ).first()

    if current:
        current.content = content
        current.description = description
        current.scope = scope
        current.mapping_type = name
        current.updated_at = now
        current.published_by = actor
        current.published_at = now
        current.tenant_id = tenant_id
        session.add(current)
        session.commit()
        print(f"Updated: {name} ({current.asset_id})")
        return

    row = TbAssetRegistry(
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
    session.add(row)
    session.commit()
    print(f"Created: {name} ({row.asset_id})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed unified OPS planner mappings")
    parser.add_argument("--actor", default="seed_mapping_keywords_script")
    parser.add_argument("--scope", default="ops")
    parser.add_argument("--tenant-id", default="default")
    args = parser.parse_args()

    planner_keywords = dict(PLANNER_KEYWORDS_TEMPLATE)
    planner_defaults = dict(PLANNER_DEFAULTS_TEMPLATE)

    with get_session_context() as session:
        _upsert_published_mapping(
            session,
            name="planner_keywords",
            scope=args.scope,
            content=planner_keywords,
            description="Unified planner keyword mapping for OPS orchestration",
            actor=args.actor,
            tenant_id=args.tenant_id,
        )
        _upsert_published_mapping(
            session,
            name="planner_defaults",
            scope=args.scope,
            content=planner_defaults,
            description="Unified planner defaults mapping for OPS orchestration",
            actor=args.actor,
            tenant_id=args.tenant_id,
        )

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
