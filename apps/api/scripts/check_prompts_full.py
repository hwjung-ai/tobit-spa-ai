"""Check prompt assets with all details."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry

def main():
    with get_session_context() as session:
        prompts = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.asset_type == 'prompt'
        ).all()
        
        print(f'총 {len(prompts)}개의 프롬프트 asset:')
        print('=' * 100)
        for p in prompts:
            print(f'  name: {p.name}')
            print(f'  scope: {p.scope}')
            print(f'  engine: {p.engine}')
            print(f'  is_system: {p.is_system}')
            print(f'  status: {p.status}')
            print(f'  tenant_id: "{p.tenant_id}"')
            print(f'  asset_id: {p.asset_id}')
            print('-' * 100)

if __name__ == "__main__":
    main()