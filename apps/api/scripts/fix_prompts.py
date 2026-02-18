"""Fix prompt assets - remove old ci_universal_present and set is_system=False."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from core.logging import get_logger
from app.modules.asset_registry.models import TbAssetRegistry

logger = get_logger(__name__)


def main():
    with get_session_context() as session:
        # 1. Delete ci_universal_present
        universal = (
            session.query(TbAssetRegistry)
            .filter(
                TbAssetRegistry.asset_type == "prompt",
                TbAssetRegistry.name == "ci_universal_present",
            )
            .all()
        )
        for u in universal:
            session.delete(u)
            logger.info(f"Deleted: {u.name}")

        # 2. Set is_system=False for all prompts (for UI visibility)
        prompts = (
            session.query(TbAssetRegistry)
            .filter(TbAssetRegistry.asset_type == "prompt")
            .all()
        )
        for p in prompts:
            if p.is_system:
                p.is_system = False
                logger.info(f"Set is_system=False: {p.name}")

        session.commit()

        # 3. Show final state
        final_prompts = (
            session.query(TbAssetRegistry)
            .filter(TbAssetRegistry.asset_type == "prompt")
            .all()
        )
        print(f"\n✅ Final prompt assets ({len(final_prompts)}):")
        print("-" * 80)
        for p in final_prompts:
            print(
                f"  name: {p.name}, scope: {p.scope}, is_system: {p.is_system}, status: {p.status}"
            )


if __name__ == "__main__":
    main()