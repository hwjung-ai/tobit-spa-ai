#!/usr/bin/env python
"""Delete duplicate ci_planner_output_parser from the database"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def delete_old_ci_planner() -> None:
    """Delete the older ci_planner_output_parser by changing status to draft"""
    with get_session_context() as session:
        planners = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "prompt")
            .where(TbAssetRegistry.scope == "ci")
            .where(TbAssetRegistry.engine == "planner")
            .where(TbAssetRegistry.name == "ci_planner_output_parser")
            .where(TbAssetRegistry.status == "published")
            .order_by(TbAssetRegistry.created_at.desc())  # Newest first
        ).all()

        if len(planners) <= 1:
            print("✓ Only one or no ci_planner_output_parser found. No deletion needed.")
            return

        latest = planners[0]
        old = planners[1]

        print("\n" + "=" * 80)
        print("DELETING DUPLICATE ci_planner_output_parser")
        print("=" * 80 + "\n")

        print(f"Keeping (newer):  {latest.asset_id}")
        print(f"  Created: {latest.created_at}\n")

        print(f"Deleting (older): {old.asset_id}")
        print(f"  Created: {old.created_at}\n")

        # Change status to draft (soft delete)
        old.status = "draft"
        old.updated_at = datetime.now()
        session.add(old)
        session.commit()

        print("✓ Successfully deleted old ci_planner_output_parser!")
        print("  (Changed status from 'published' to 'draft')\n")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    delete_old_ci_planner()
