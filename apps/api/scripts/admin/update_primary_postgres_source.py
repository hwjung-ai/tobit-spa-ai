#!/usr/bin/env python3
"""
Update primary_postgres Source Asset and primary_postgres_schema with source_ref
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, '.')

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_path)

from core.db import get_session_context
from core.encryption import get_encryption_manager
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select
from uuid import uuid4

def encrypt_password(password: str) -> str:
    """Encrypt password using EncryptionManager"""
    manager = get_encryption_manager()
    return manager.encrypt(password)

def main():
    # Read .env for PostgreSQL credentials
    pg_host = os.getenv("PG_HOST")
    pg_port = int(os.getenv("PG_PORT", "5432"))
    pg_db = os.getenv("PG_DB")
    pg_user = os.getenv("PG_USER")
    pg_password = os.getenv("PG_PASSWORD")
    
    print("=" * 80)
    print("Updating primary_postgres Source Asset")
    print("=" * 80)
    print(f"Host: {pg_host}")
    print(f"Port: {pg_port}")
    print(f"Database: {pg_db}")
    print(f"User: {pg_user}")
    print(f"Password: {'*' * len(pg_password)}")
    print("=" * 80)
    
    if not all([pg_host, pg_db, pg_user, pg_password]):
        print("ERROR: Missing PostgreSQL credentials in .env")
        print("Required: PG_HOST, PG_DB, PG_USER, PG_PASSWORD")
        sys.exit(1)
    
    # Encrypt password
    try:
        encrypted_password = encrypt_password(pg_password)
        print(f"Password encrypted successfully")
    except Exception as e:
        print(f"ERROR: Failed to encrypt password: {e}")
        sys.exit(1)
    
    with get_session_context() as session:
        # 1. Update or create primary_postgres Source Asset
        source = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "source")
            .where(TbAssetRegistry.name == "primary_postgres")
            .where(TbAssetRegistry.status == "published")
        ).first()
        
        source_content = {
            "source_type": "postgresql",
            "connection": {
                "host": pg_host,
                "port": pg_port,
                "database": pg_db,
                "username": pg_user,
                "password_encrypted": encrypted_password,
                "timeout": 30
            },
            "spec": {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 30,
                "pool_recycle": 3600
            }
        }
        
        if source:
            print(f"Found existing primary_postgres source (ID: {source.asset_id})")
            source.content = source_content
            print("Updated source content")
        else:
            print("Creating new primary_postgres source...")
            source = TbAssetRegistry(
                asset_id=uuid4(),
                asset_type="source",
                name="primary_postgres",
                description="Primary PostgreSQL database for system operations",
                version=1,
                status="published",
                scope="ops",
                content=source_content,
                tags={"environment": "production", "source_type": "postgresql"}
            )
            session.add(source)
            print("Created source asset")
        
        session.commit()
        print(f"primary_postgres source saved (ID: {source.asset_id})")
        
        # 2. Update primary_postgres_schema with source_ref
        print("\n" + "=" * 80)
        print("Updating primary_postgres_schema Asset")
        print("=" * 80)
        
        schema = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "schema")
            .where(TbAssetRegistry.name == "primary_postgres_schema")
            .where(TbAssetRegistry.status == "published")
        ).first()
        
        if schema:
            print(f"Found existing primary_postgres_schema (ID: {schema.asset_id})")
            # Add or update source_ref in content
            if schema.content is None:
                schema.content = {}
            schema.content["source_ref"] = "primary_postgres"
            print("Added source_ref: primary_postgres")
        else:
            print("ERROR: primary_postgres_schema not found!")
            print("Please create schema asset first")
            sys.exit(1)
        
        session.commit()
        print(f"primary_postgres_schema updated (ID: {schema.asset_id})")
        
        print("\n" + "=" * 80)
        print("✅ Update completed successfully!")
        print("=" * 80)
        print(f"Source Asset: primary_postgres (ID: {source.asset_id})")
        print(f"Schema Asset: primary_postgres_schema (ID: {schema.asset_id})")
        print(f"Schema source_ref: {schema.content.get('source_ref')}")
        print("=" * 80)

if __name__ == "__main__":
    main()