
import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.append(project_root)

from sqlmodel import create_engine, text

from apps.api.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.postgres_dsn)

def check_db():
    print("Checking database...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [row[0] for row in result]
        print("Tables:", tables)
        
        if 'tb_asset_registry' in tables:
             print("\nDetails of tb_asset_registry:")
             cols = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tb_asset_registry'"))
             for col in cols:
                 print(f" - {col[0]}: {col[1]}")
        else:
             print("\n tb_asset_registry MISSING!")

if __name__ == "__main__":
    check_db()
