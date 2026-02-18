"""
Update default_resolver with sample rules.

This script updates the default_resolver asset with sample rules:
- 디비 → DB
- 와스 → WAS
- CI → 구성

Also marks it as a system asset (cannot be deleted or renamed).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry


DEFAULT_RESOLVER_CONTENT = {
    "name": "default_resolver",
    "description": "Default resolver rules for common entity mappings",
    "default_namespace": "default",
    "rules": [
        {
            "rule_type": "alias_mapping",
            "name": "디비 → DB",
            "description": "디비를 DB로 변환",
            "is_active": True,
            "priority": 1,
            "rule_data": {
                "source_entity": "디비",
                "target_entity": "DB",
            },
        },
        {
            "rule_type": "alias_mapping",
            "name": "와스 → WAS",
            "description": "와스를 WAS로 변환",
            "is_active": True,
            "priority": 2,
            "rule_data": {
                "source_entity": "와스",
                "target_entity": "WAS",
            },
        },
        {
            "rule_type": "alias_mapping",
            "name": "CI → 구성",
            "description": "CI를 구성으로 변환",
            "is_active": True,
            "priority": 3,
            "rule_data": {
                "source_entity": "CI",
                "target_entity": "구성",
            },
        },
    ],
}


def update_default_resolver():
    """Update default_resolver asset with sample rules."""
    with get_session_context() as session:
        # Find the default_resolver
        resolver = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "resolver")
            .where(TbAssetRegistry.name == "default_resolver")
        ).first()

        if not resolver:
            # Create new resolver
            resolver = TbAssetRegistry(
                name="default_resolver",
                description="Default resolver rules for common entity mappings",
                asset_type="resolver",
                content=DEFAULT_RESOLVER_CONTENT,
                status="published",
                is_system=True,
                tenant_id="default",
                scope="default",
                tags={"system": True},
            )
            session.add(resolver)
            print("[CREATE] default_resolver created with sample rules")
        else:
            # Update existing resolver
            resolver.content = DEFAULT_RESOLVER_CONTENT
            resolver.description = "Default resolver rules for common entity mappings"
            resolver.is_system = True
            resolver.status = "published"
            print("[UPDATE] default_resolver updated with sample rules")

        session.commit()
        print("\n✓ Default resolver updated!")
        print("  Rules:")
        for rule in DEFAULT_RESOLVER_CONTENT["rules"]:
            rd = rule.get("rule_data", {})
            print(f"    - {rd.get('source_entity', '?')} → {rd.get('target_entity', '?')}")
        print("  is_system: True (protected)")


if __name__ == "__main__":
    print("Updating default_resolver...")
    print("-" * 50)
    update_default_resolver()
