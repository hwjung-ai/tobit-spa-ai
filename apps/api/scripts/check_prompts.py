"""Check prompt assets in database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context


def main():
    with get_session_context() as session:
        prompts = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.asset_type == 'prompt'
        ).all()
        
        print(f'총 {len(prompts)}개의 프롬프트 asset:')
        print('-' * 80)
        for p in prompts:
            print(f'  name: {p.name}, scope: {p.scope}, is_system: {p.is_system}, status: {p.status}')

if __name__ == "__main__":
    main()