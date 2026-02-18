#!/usr/bin/env python3
"""Backfill is_system flags for Admin Asset policy.

Policy:
- source: always non-system
- prompt/mapping/policy/query/resolver: system
- prompt exceptions (non-system): ops_all, tool_selector
"""

from __future__ import annotations

import os
import sys

from sqlmodel import select

# Add apps/api to import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context

ADMIN_SYSTEM_ASSET_TYPES = {"prompt", "mapping", "policy", "query", "resolver"}
NON_SYSTEM_PROMPT_NAMES = {"ops_all", "tool_selector"}


def should_be_system(asset: TbAssetRegistry) -> bool:
    asset_type = (asset.asset_type or "").strip().lower()
    if asset_type not in ADMIN_SYSTEM_ASSET_TYPES:
        return False
    if asset_type == "prompt" and (asset.name or "").strip() in NON_SYSTEM_PROMPT_NAMES:
        return False
    return True


def main() -> None:
    updated = 0
    unchanged = 0

    with get_session_context() as session:
        assets = session.exec(select(TbAssetRegistry)).all()
        for asset in assets:
            target = should_be_system(asset)
            current = bool(asset.is_system)
            if current == target:
                unchanged += 1
                continue
            asset.is_system = target
            updated += 1
            print(
                f"updated: {asset.asset_type}:{asset.name} "
                f"is_system {current} -> {target}"
            )

        session.commit()

    print(f"done: updated={updated}, unchanged={unchanged}")


if __name__ == "__main__":
    main()
