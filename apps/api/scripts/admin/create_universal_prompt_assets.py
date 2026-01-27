#!/usr/bin/env python
"""Create universal prompt assets for 100 test questions coverage"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
from core.db import get_session_context
from sqlmodel import select
from app.modules.asset_registry.models import TbAssetRegistry
from app.modules.asset_registry.crud import create_asset, publish_asset


UNIVERSAL_PROMPTS = [
    {
        "name": "ci_universal_planner",
        "file": "universal_planner.yaml",
        "engine": "planner",
        "description": "Universal planner for 100 test questions covering CI, Graph, Metric, and History tools",
    },
    {
        "name": "ci_universal_compose",
        "file": "universal_compose.yaml",
        "engine": "compose",
        "description": "Universal compose for multi-tool result composition",
    },
    {
        "name": "ci_universal_present",
        "file": "universal_present.yaml",
        "engine": "present",
        "description": "Universal present for final response formatting",
    },
]


def create_prompt_asset(session, prompt_def: dict) -> TbAssetRegistry:
    """Create a prompt asset from YAML file"""
    prompt_file = ROOT / "resources" / "prompts" / "ci" / prompt_def["file"]

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        yaml_content = yaml.safe_load(f)

    templates = yaml_content.get("templates", {})
    system_template = templates.get("system", "")

    # Input schema
    input_schema = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "User's question"
            }
        },
        "required": ["question"]
    }

    # Output contract varies by engine
    if prompt_def["engine"] == "planner":
        output_contract = {
            "type": "object",
            "properties": {
                "route": {"type": "string"},
                "tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "operation": {"type": "string"},
                            "priority": {"type": "integer"},
                            "params": {"type": "object"}
                        }
                    }
                },
                "output_types": {"type": "array", "items": {"type": "string"}},
                "ambiguity": {"type": "boolean"},
                "confidence": {"type": "number"}
            },
            "required": ["route", "tools"]
        }
    elif prompt_def["engine"] == "compose":
        output_contract = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "sections": {"type": "array"},
                "format": {"type": "string"}
            }
        }
    else:  # present
        output_contract = {
            "type": "object",
            "properties": {
                "output": {"type": "string"},
                "format": {"type": "string"}
            }
        }

    # Check if asset already exists
    existing = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "prompt")
        .where(TbAssetRegistry.scope == "ci")
        .where(TbAssetRegistry.engine == prompt_def["engine"])
        .where(TbAssetRegistry.name == prompt_def["name"])
    ).first()

    if existing:
        print(f"  ⚠ Asset {prompt_def['name']} already exists (v{existing.version})")
        return existing

    # Create new asset
    asset = create_asset(
        session=session,
        name=prompt_def["name"],
        asset_type="prompt",
        description=prompt_def["description"],
        scope="ci",
        engine=prompt_def["engine"],
        template=system_template,
        input_schema=input_schema,
        output_contract=output_contract,
        created_by="admin",
    )

    return asset


def main() -> None:
    """Create all universal prompt assets"""
    print("\n" + "=" * 80)
    print("CREATING UNIVERSAL PROMPT ASSETS")
    print("=" * 80 + "\n")

    with get_session_context() as session:
        created_count = 0
        skipped_count = 0

        for prompt_def in UNIVERSAL_PROMPTS:
            print(f"Processing: {prompt_def['name']}")
            print(f"  File: {prompt_def['file']}")
            print(f"  Engine: {prompt_def['engine']}")

            try:
                asset = create_prompt_asset(session, prompt_def)
                if asset and hasattr(asset, 'version'):
                    print(f"  ✓ Created: v{asset.version} (draft status)")
                    created_count += 1
                else:
                    print(f"  ⊘ Skipped: already exists")
                    skipped_count += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")

            print()

        print("-" * 80)
        print(f"Summary: {created_count} created, {skipped_count} skipped")
        print()

        if created_count > 0:
            print("Assets created in DRAFT status.")
            print("Review and publish when ready:")
            print("  UPDATE: UPDATE tb_asset_registry SET status='published' WHERE name IN (")
            for p in UNIVERSAL_PROMPTS:
                print(f"    '{p['name']}',")
            print("  ) AND status='draft';")
            print()

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
