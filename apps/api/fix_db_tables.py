
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.append(project_root)

from sqlmodel import SQLModel, create_engine, text
from apps.api.core.config import get_settings

# Import all models
from apps.api.app.modules.auth.models import TbUser, TbRefreshToken
from apps.api.app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from apps.api.app.modules.ui_creator.models import TbUiDef
from apps.api.app.modules.permissions.models import TbResourcePermission

settings = get_settings()
engine = create_engine(settings.postgres_dsn)

def recreate_tables():
    print("Re-creating tables individually...")
    
    # Try to drop target tables first
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS tb_asset_version_history CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS tb_asset_registry CASCADE"))
        conn.commit()
        
    # Get all tables from metadata
    tables = SQLModel.metadata.sorted_tables
    
    for table in tables:
        print(f"Checking/Creating table: {table.name}")
        try:
            table.create(engine)
            print(f"  - Created {table.name}")
        except Exception as e:
            msg = str(e)
            if "already exists" in msg or "DuplicateTable" in msg:
                 print(f"  - Table {table.name} already exists (likely)")
            else:
                 print(f"  - Error creationg {table.name}: {e}")

if __name__ == "__main__":
    recreate_tables()
