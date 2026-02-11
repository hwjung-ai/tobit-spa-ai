#!/usr/bin/env python
"""Update ci_planner_output_parser asset from planner.yaml file"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
from app.modules.asset_registry.crud import create_asset, publish_asset, update_asset
from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select

PLANNER_FILE = ROOT / "resources" / "prompts" / "ci" / "planner.yaml"


def update_planner_asset() -> None:
    """Update ci_planner_output_parser asset from planner.yaml"""
    if not PLANNER_FILE.exists():
        print(f"\n❌ planner.yaml not found at {PLANNER_FILE}")
        return

    with open(PLANNER_FILE, "r", encoding="utf-8") as f:
        yaml_content = yaml.safe_load(f)

    print("\n" + "=" * 80)
    print("UPDATING ci_planner_output_parser ASSET")
    print("=" * 80 + "\n")

    with get_session_context() as session:
        # Check if asset exists
        existing = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "planner")
            .where(TbAssetRegistry.name == "ci_planner_output_parser")
            .order_by(TbAssetRegistry.version.desc())
        ).first()

        # Get templates from YAML
        templates = yaml_content.get("templates", {})
        system_template = templates.get("system", "")

        # Proper JSON Schema for input_schema (validator requires 'question' property)
        input_schema = {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "User's question to parse"
                }
            },
            "required": ["question"]
        }

        # Proper JSON Schema for output_contract (validator requires 'plan' property)
        output_contract = {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "object",
                    "description": "Parsed plan from LLM",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "description": "Plan steps",
                            "items": {"type": "object"}
                        },
                        "policy": {
                            "type": "object",
                            "description": "Plan policy"
                        }
                    }
                }
            },
            "required": ["plan"]
        }

        if existing:
            print(f"Found existing asset: {existing.asset_id} (v{existing.version})")

            # Check if there's a draft version
            draft_asset = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.name == "ci_planner_output_parser")
                .where(TbAssetRegistry.asset_type == "prompt")
                .where(TbAssetRegistry.status == "draft")
            ).first()

            if draft_asset:
                print("Updating existing draft version...")
                update_asset(
                    session=session,
                    asset=draft_asset,
                    updates={
                        "template": system_template,
                        "input_schema": input_schema,
                        "output_contract": output_contract,
                    },
                    updated_by="admin",
                )
                print(f"✓ Updated draft asset: {draft_asset.asset_id}")
            else:
                # Create new draft version
                print("Creating new draft version...")
                new_asset = create_asset(
                    session=session,
                    name="ci_planner_output_parser",
                    asset_type="prompt",
                    description="CI Planner output parser LLM prompt",
                    scope="ci",
                    engine="planner",
                    template=system_template,
                    input_schema=input_schema,
                    output_contract=output_contract,
                    created_by="admin",
                )
                print(f"✓ Created new draft asset: {new_asset.asset_id} (v{new_asset.version})")

            print("\nRun 'python apps/api/scripts/admin/publish_planner_asset.py' to publish.")
        else:
            print("No existing asset found. Creating new asset...")
            new_asset = create_asset(
                session=session,
                name="ci_planner_output_parser",
                asset_type="prompt",
                description="CI Planner output parser LLM prompt",
                scope="ci",
                engine="planner",
                template=system_template,
                input_schema=input_schema,
                output_contract=output_contract,
                created_by="admin",
            )
            # Publish the new asset
            published = publish_asset(session, new_asset, "admin")
            print(f"✓ Created and published new asset: {published.asset_id}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    update_planner_asset()
