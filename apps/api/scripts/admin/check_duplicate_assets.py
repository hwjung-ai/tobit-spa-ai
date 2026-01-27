#!/usr/bin/env python3
"""
Check for duplicate published assets in database
"""
import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select
from collections import Counter

def main():
    with get_session_context() as session:
        assets = session.exec(select(TbAssetRegistry).where(TbAssetRegistry.status == 'published')).all()
        
        # 이름별 중복 확인
        names = [a.name for a in assets]
        duplicates = {k:v for k,v in Counter(names).items() if v > 1}
        
        print("=" * 80)
        print("중복된 Published Assets")
        print("=" * 80)
        
        if duplicates:
            for name, count in sorted(duplicates.items()):
                print(f"\n  ⚠️  {name} ({count}개)")
                # 중복된 asset들의 상세 정보
                dup_assets = [a for a in assets if a.name == name]
                for i, a in enumerate(dup_assets):
                    print(f"    [{i+1}] ID={str(a.asset_id)[:8]}..., type={a.asset_type}, policy={a.policy_type}, mapping={a.mapping_type}")
        else:
            print("  ✅ 중복된 asset이 없습니다.")
        
        print("\n" + "=" * 80)
        print(f"총 Published Assets: {len(assets)}개")
        print("=" * 80)
        
        # 전체 목록 출력
        print("\n전체 Published Assets 목록:")
        print("-" * 80)
        for a in sorted(assets, key=lambda x: (x.asset_type, x.name)):
            print(f"{a.asset_type:15} | {a.name:30} | {str(a.asset_id)[:8]}... | {a.policy_type}")

if __name__ == "__main__":
    main()