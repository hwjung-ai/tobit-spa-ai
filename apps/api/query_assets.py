import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Build connection string
db_host = os.getenv("PG_HOST")
db_port = os.getenv("PG_PORT")
db_name = os.getenv("PG_DB")
db_user = os.getenv("PG_USER")
db_password = os.getenv("PG_PASSWORD")

connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

try:
    engine = create_engine(connection_string)
    
    # Query to check asset types
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset_type, COUNT(*) as count, status, created_at 
            FROM tb_asset_registry 
            GROUP BY asset_type, status, created_at
            ORDER BY asset_type, status, created_at DESC
        """))
        
        print("Asset Registry Contents:")
        print("-" * 80)
        for row in result:
            print(f"Type: {row[0]:15} | Status: {row[2]:10} | Count: {row[1]:3} | Created: {row[3]}")
        
        # Get detailed list of assets
        print("\n\nDetailed Asset List:")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT id, asset_type, asset_name, status, created_at, updated_at
            FROM tb_asset_registry
            ORDER BY asset_type, created_at DESC
            LIMIT 30
        """))
        
        for row in result:
            print(f"ID: {row[0]:20} | Type: {row[1]:10} | Name: {row[2]:30} | Status: {row[3]:10} | Updated: {row[5]}")
        
except Exception as e:
    print(f"Error: {e}")
