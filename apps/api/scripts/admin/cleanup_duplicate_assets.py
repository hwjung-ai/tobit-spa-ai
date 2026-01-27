#!/usr/bin/env python3
"""
Cleanup duplicate published assets from database
"""
import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select

# Assets that are actually used in the code
USED_POLICY_ASSETS = {
    "column_allowlist",
    "discovery_config",
    "plan_budget",
    "time_ranges",
    "tool_limits",
    "view_depth",
}

USED_MAPPING_ASSETS = {
    "agg_keywords",
    "auto_keywords",
    "cep_keywords",
    "filterable_fields",
    "graph_relation",
    "graph_relation_allowlist",
    "graph_scope_keywords",
    "history_keywords",
    "list_keywords",
    "metric_aliases",
    "series_keywords",
    "table_hints",
}

# Test assets - delete all duplicates
TEST_ASSETS = {
    "test_publish",
}

def cleanup_assets():
    """Clean up duplicate published assets"""
    with get_session_context() as session:
        assets = session.exec(select(TbAssetRegistry).where(TbAssetRegistry.status == 'published')).all()
        
        # Group by name
        from collections import defaultdict
        name_groups = defaultdict(list)
        for a in assets:
            name_groups[a.name].append(a)
        
        print("=" * 80)
        print("중복된 Asset 정리")
        print("=" * 80)
        
        total_deleted = 0
        total_kept = 0
        
        for name, dup_assets in sorted(name_groups.items()):
            if len(dup_assets) <= 1:
                continue
            
            # Sort by created_at (keep the most recent)
            sorted_assets = sorted(dup_assets, key=lambda x: x.created_at, reverse=True)
            keep_asset = sorted_assets[0]
            delete_assets = sorted_assets[1:]
            
            # Special handling for view_depth_policies
            if name == "view_depth_policies":
                # Keep only the one we created (8f1edfe2...)
                keep_asset = next((a for a in dup_assets if str(a.asset_id).startswith("8f1edfe2")), None)
                if keep_asset:
                    delete_assets = [a for a in dup_assets if a.asset_id != keep_asset.asset_id]
                else:
                    # If our asset not found, keep the most recent
                    delete_assets = sorted_assets[1:]
                    keep_asset = sorted_assets[0]
            
            # Special handling for test_publish (delete all)
            elif name in TEST_ASSETS:
                # Delete all test_publish assets
                for a in dup_assets:
                    session.delete(a)
                    print(f"  🗑️  DELETED: {name} (ID={str(a.asset_id)[:8]}...)")
                total_deleted += len(dup_assets)
                continue
            
            # For policy assets, check if name is in USED_POLICY_ASSETS
            if name in USED_POLICY_ASSETS or name in USED_MAPPING_ASSETS:
                print(f"\n  🔍 {name} ({len(dup_assets)}개 duplicates)")
                print(f"    ✅ KEEP: {str(keep_asset.asset_id)[:8]}... (created_at={keep_asset.created_at})")
                
                for delete_asset in delete_assets:
                    session.delete(delete_asset)
                    print(f"    🗑️  DELETED: {str(delete_asset.asset_id)[:8]}... (created_at={delete_asset.created_at})")
                    total_deleted += 1
                
                total_kept += 1
            else:
                # For other assets (queries, etc.), keep the most recent
                print(f"\n  🔍 {name} ({len(dup_assets)}개 duplicates)")
                print(f"    ✅ KEEP: {str(keep_asset.asset_id)[:8]}... (created_at={keep_asset.created_at})")
                
                for delete_asset in delete_assets:
                    session.delete(delete_asset)
                    print(f"    🗑️  DELETED: {str(delete_asset.asset_id)[:8]}... (created_at={delete_asset.created_at})")
                    total_deleted += 1
                
                total_kept += 1
        
        session.commit()
        
        print("\n" + "=" * 80)
        print("정리 완료")
        print("=" * 80)
        print(f"  총 삭제된 assets: {total_deleted}개")
        print(f"  총 보존된 assets: {total_kept}개")
        print("=" * 80)

if __name__ == "__main__":
    cleanup_assets()