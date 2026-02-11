"""Apply migrations 0050 and 0051 for API-Tools integration."""
import sys
from pathlib import Path

# Add apps/api to path (scripts is inside apps/api)
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from core.db import engine as db_engine
from sqlalchemy import create_engine, text

print("Connecting to DB...")
engine = create_engine(str(db_engine.url))

print("=" * 50)
print("Applying Migrations 0050 & 0051")
print("=" * 50)

with engine.connect() as conn:
    # 0050: Add tools linkage to api_definitions
    print("\n[0050] Adding columns to api_definitions...")
    try:
        conn.execute(text("ALTER TABLE api_definitions ADD COLUMN IF NOT EXISTS linked_to_tool_id UUID"))
        print("  ✓ linked_to_tool_id")
    except Exception as e:
        print(f"  ! linked_to_tool_id: {e}")
    
    try:
        conn.execute(text("ALTER TABLE api_definitions ADD COLUMN IF NOT EXISTS linked_to_tool_name TEXT"))
        print("  ✓ linked_to_tool_name")
    except Exception as e:
        print(f"  ! linked_to_tool_name: {e}")
    
    try:
        conn.execute(text("ALTER TABLE api_definitions ADD COLUMN IF NOT EXISTS linked_at TIMESTAMP"))
        print("  ✓ linked_at")
    except Exception as e:
        print(f"  ! linked_at: {e}")
    
    # 0051: Add API linkage to tb_asset_registry
    print("\n[0051] Adding columns to tb_asset_registry...")
    try:
        conn.execute(text("ALTER TABLE tb_asset_registry ADD COLUMN IF NOT EXISTS linked_from_api_id UUID"))
        print("  ✓ linked_from_api_id")
    except Exception as e:
        print(f"  ! linked_from_api_id: {e}")
    
    try:
        conn.execute(text("ALTER TABLE tb_asset_registry ADD COLUMN IF NOT EXISTS linked_from_api_name TEXT"))
        print("  ✓ linked_from_api_name")
    except Exception as e:
        print(f"  ! linked_from_api_name: {e}")
    
    try:
        conn.execute(text("ALTER TABLE tb_asset_registry ADD COLUMN IF NOT EXISTS linked_from_api_at TIMESTAMP WITH TIME ZONE"))
        print("  ✓ linked_from_api_at")
    except Exception as e:
        print(f"  ! linked_from_api_at: {e}")
    
    try:
        conn.execute(text("ALTER TABLE tb_asset_registry ADD COLUMN IF NOT EXISTS import_mode TEXT"))
        print("  ✓ import_mode")
    except Exception as e:
        print(f"  ! import_mode: {e}")
    
    try:
        conn.execute(text("ALTER TABLE tb_asset_registry ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP WITH TIME ZONE"))
        print("  ✓ last_synced_at")
    except Exception as e:
        print(f"  ! last_synced_at: {e}")
    
    # Update alembic_version
    print("\n[Update] Updating alembic_version...")
    try:
        conn.execute(text("UPDATE alembic_version SET version_num = '0051' WHERE version_num = '0049_add_api_definitions_runtime_policy'"))
        print("  ✓ alembic_version updated to 0051")
    except Exception as e:
        print(f"  ! alembic_version: {e}")
    
    conn.commit()
    print("\n" + "=" * 50)
    print("✅ Migration completed successfully!")
    print("=" * 50)
    
    # Verify
    print("\n[Verify] Checking migration status...")
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    print(f"Current DB version: {result.fetchone()[0]}")