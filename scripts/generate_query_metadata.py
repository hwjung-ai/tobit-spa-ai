#!/usr/bin/env python3
"""
Generate YAML metadata for SQL query files automatically.

This script creates YAML files for each SQL query with basic metadata
including name, description, scope, and output schema placeholders.

Usage:
  python generate_query_metadata.py
"""

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
QUERIES_ROOT = REPO_ROOT / "apps/api/resources/queries"

# Scope mapping based on directory names
SCOPE_MAP = {
    "ci": "ci",
    "discovery": "ci",
    "metric": "metric",
    "history": "history",
    "graph": "graph",
}

# Category mapping
CATEGORY_MAP = {
    "ci": "ci_management",
    "discovery": "discovery",
    "metric": "metric_tracking",
    "history": "history_tracking",
    "graph": "graph_analysis",
}


def get_scope_and_category(sql_file: Path) -> tuple[str, str]:
    """Determine scope and category from file path."""
    parts = sql_file.parts
    # Find the scope directory (one level up from SQL file)
    scope_dir = parts[-2]
    scope = SCOPE_MAP.get(scope_dir, "general")
    category = CATEGORY_MAP.get(scope_dir, "general")
    return scope, category


def generate_yaml_metadata(sql_file: Path, scope: str, category: str) -> str:
    """Generate YAML metadata content for a SQL file."""
    name = sql_file.stem
    description = f"Query for {scope}: {name.replace('_', ' ')}"

    yaml_content = {
        "name": name,
        "description": description,
        "scope": scope,
        "category": category,
        "tags": [scope, category],
        "parameters": [],
        "output_schema": {
            "type": "object",
            "properties": {},
        },
    }

    return yaml.dump(
        yaml_content,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


def main():
    """Generate YAML metadata files for all SQL queries."""
    if not QUERIES_ROOT.exists():
        print(f"Error: {QUERIES_ROOT} not found")
        return

    sql_files = sorted(QUERIES_ROOT.rglob("*.sql"))

    if not sql_files:
        print("No SQL files found")
        return

    created_count = 0
    skipped_count = 0

    for sql_file in sql_files:
        yaml_file = sql_file.with_suffix(".yaml")

        # Skip if YAML already exists
        if yaml_file.exists():
            print(f"  ⊘ YAML exists: {yaml_file.relative_to(REPO_ROOT)}")
            skipped_count += 1
            continue

        # Generate metadata
        scope, category = get_scope_and_category(sql_file)
        yaml_content = generate_yaml_metadata(sql_file, scope, category)

        # Write YAML file
        yaml_file.write_text(yaml_content, encoding="utf-8")
        print(f"  ✓ Created: {yaml_file.relative_to(REPO_ROOT)}")
        created_count += 1

    print(f"\n--- Metadata generation complete ---")
    print(f"  Created: {created_count} YAML files")
    print(f"  Skipped: {skipped_count} (already exist)")
    print(f"\nNext steps:")
    print(f"  1. Review generated YAML files")
    print(f"  2. Run: python scripts/query_asset_importer.py --scope ci --apply --publish")


if __name__ == "__main__":
    main()
