import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.append(project_root)

from sqlmodel import SQLModel, create_engine, text

# Import all models
from apps.api.core.config import get_settings

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
