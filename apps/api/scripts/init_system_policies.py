"""
Initialize system-required Policy Assets.

These policies are required for OPS orchestration to function properly:
- plan_budget: Execution limits (max_steps, timeout, max_depth) - applied at Validate stage
- view_depth: View depth policies (SUMMARY, COMPOSITION, etc.) - applied at Execute stage

System policies:
- is_system = True (cannot be deleted or renamed)
- Content can be modified by admin

Run this script during initial setup or after database reset.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry


# System Policy Types (fixed, cannot be changed without code modification)
SYSTEM_POLICY_TYPES = ["plan_budget", "view_depth", "discovery_config"]

# Policy data
PLAN_BUDGET_DATA = {
    "name": "plan_budget",
    "description": "Execution budget constraints for OPS orchestration (applied at Validate stage)",
    "policy_type": "plan_budget",
    "scope": "ops",
    "limits": {
        "max_steps": 10,
        "timeout_ms": 120000,
        "max_depth": 5,
        "max_branches": 3,
        "max_iterations": 100,
    },
}

VIEW_DEPTH_DATA = {
    "name": "view_depth",
    "description": "Depth constraints for graph views (applied at Execute stage)",
    "policy_type": "view_depth",
    "scope": "ops",
    "limits": {
        "views": {
            "SUMMARY": {
                "default_depth": 1,
                "max_depth": 1,
                "direction_default": "both",
                "description": "Top-level overview with key statistics",
            },
            "COMPOSITION": {
                "default_depth": 2,
                "max_depth": 3,
                "direction_default": "out",
                "description": "System/component composition",
            },
            "DEPENDENCY": {
                "default_depth": 2,
                "max_depth": 3,
                "direction_default": "both",
                "description": "Bidirectional dependency relationships",
            },
            "IMPACT": {
                "default_depth": 2,
                "max_depth": 2,
                "direction_default": "out",
                "description": "Propagated impact along dependencies",
            },
            "PATH": {
                "default_depth": 3,
                "max_depth": 6,
                "direction_default": "both",
                "max_hops": 6,
                "description": "Path discovery with hop limit",
            },
            "NEIGHBORS": {
                "default_depth": 1,
                "max_depth": 2,
                "direction_default": "both",
                "description": "Immediate neighbors",
            },
        }
    },
}


DISCOVERY_CONFIG_DATA = {
    "name": "discovery_config",
    "description": "CI discovery configuration (applied at Execute stage)",
    "policy_type": "discovery_config",
    "scope": "ops",
    # Use 'content' field, not 'limits' - code expects policy.get("content", {})
    "content": {
        "neo4j": {
            "rel_types": ["COMPOSED_OF", "DEPENDS_ON", "RUNS_ON", "DEPLOYED_ON", "USES", "PROTECTED_BY", "CONNECTED_TO"],
            "target_labels": ["CI"],
            "expected_ci_properties": ["ci_id", "ci_code", "tenant_id"],
        },
        "postgres": {
            "target_tables": ["ci", "ci_ext"],
            "agg_columns": ["ci_type", "ci_subtype", "ci_category", "status", "location", "owner"],
        },
    },
}


def init_system_policies():
    """Initialize system-required policy assets."""
    with get_session_context() as session:
        policies_to_create = [PLAN_BUDGET_DATA, VIEW_DEPTH_DATA, DISCOVERY_CONFIG_DATA]

        for policy_data in policies_to_create:
            policy_type = policy_data["policy_type"]

            # Check if already exists
            existing = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "policy")
                .where(TbAssetRegistry.policy_type == policy_type)
            ).first()

            if existing:
                # Update is_system flag if not set
                if not existing.is_system:
                    existing.is_system = True
                    print(f"[UPDATE] Policy '{policy_type}' marked as system")
                else:
                    print(f"[SKIP] Policy '{policy_type}' already exists (system)")
                continue

            # Create new system policy
            policy = TbAssetRegistry(
                name=policy_data["name"],
                description=policy_data.get("description", ""),
                asset_type="policy",
                policy_type=policy_type,
                scope=policy_data.get("scope"),
                limits=policy_data.get("limits"),
                content=policy_data.get("content"),  # For discovery_config
                status="published",
                is_system=True,  # Cannot be deleted or renamed
                tenant_id="default",  # Use default tenant so it's visible in UI
            )

            session.add(policy)
            print(f"[CREATE] System policy '{policy_type}' created")

        session.commit()
        print("\n✓ System policies initialized!")
        print("  - plan_budget: Execution limits (Validate stage)")
        print("  - view_depth: View depth policies (Execute stage)")
        print("  - discovery_config: CI discovery configuration (Execute stage)")


if __name__ == "__main__":
    print("Initializing system-required policies...")
    print("-" * 50)
    init_system_policies()
