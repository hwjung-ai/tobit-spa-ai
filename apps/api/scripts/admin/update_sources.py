#!/usr/bin/env python3
"""
Update PostgreSQL and Neo4j Source Assets with plain text passwords
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
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select
from uuid import uuid4

def main():
    # Read .env for PostgreSQL credentials
    pg_host = os.getenv("PG_HOST")
    pg_port = int(os.getenv("PG_PORT", "5432"))
    pg_db = os.getenv("PG_DB")
    pg_user = os.getenv("PG_USER")
    pg_password = os.getenv("PG_PASSWORD")
    
    # Read .env for Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    # Parse Neo4j URI
    neo4j_host = None
    neo4j_port = None
    if neo4j_uri and "://" in neo4j_uri:
        # Format: bolt://host:port
        parts = neo4j_uri.split("://")[1].split(":")
        neo4j_host = parts[0]
        neo4j_port = parts[1] if len(parts) > 1 else "7687"
    
    print("=" * 80)
    print("Updating PostgreSQL and Neo4j Source Assets (PLAIN TEXT PASSWORDS)")
    print("=" * 80)
    
    with get_session_context() as session:
        # 1. Update PostgreSQL Source Asset
        print("\n" + "=" * 80)
        print("1. Updating primary_postgres Source Asset")
        print("=" * 80)
        print(f"Host: {pg_host}")
        print(f"Port: {pg_port}")
        print(f"Database: {pg_db}")
        print(f"User: {pg_user}")
        print(f"Password: {'*' * len(pg_password) if pg_password else 'None'}")
        
        if not all([pg_host, pg_db, pg_user, pg_password]):
            print("ERROR: Missing PostgreSQL credentials in .env")
            print("Required: PG_HOST, PG_DB, PG_USER, PG_PASSWORD")
        else:
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
                    "password": pg_password,  # PLAIN TEXT
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
                print("Updated source content (PLAIN TEXT)")
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
                .where(TbAssetRegistry.asset_type == "catalog")
                .where(TbAssetRegistry.name == "primary_postgres_schema")
                .where(TbAssetRegistry.status == "published")
            ).first()
            
            if schema:
                print(f"Found existing primary_postgres_schema (ID: {schema.asset_id})")
                if schema.content is None:
                    schema.content = {}
                schema.content["source_ref"] = "primary_postgres"
                print("Added source_ref: primary_postgres")
                session.commit()
                print(f"primary_postgres_schema updated (ID: {schema.asset_id})")
            else:
                print("WARNING: primary_postgres_schema not found!")
        
        # 3. Update Neo4j Source Asset
        print("\n" + "=" * 80)
        print("2. Updating primary_neo4j Source Asset")
        print("=" * 80)
        print(f"URI: {neo4j_uri}")
        print(f"Host: {neo4j_host}")
        print(f"Port: {neo4j_port}")
        print(f"User: {neo4j_user}")
        print(f"Password: {'*' * len(neo4j_password) if neo4j_password else 'None'}")
        
        if not all([neo4j_uri, neo4j_user, neo4j_password]):
            print("ERROR: Missing Neo4j credentials in .env")
            print("Required: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        else:
            source = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "source")
                .where(TbAssetRegistry.name == "primary_neo4j")
                .where(TbAssetRegistry.status == "published")
            ).first()
            
            source_content = {
                "source_type": "neo4j",
                "connection": {
                    "uri": neo4j_uri,
                    "host": neo4j_host,
                    "port": int(neo4j_port) if neo4j_port else 7687,
                    "username": neo4j_user,
                    "password": neo4j_password,  # PLAIN TEXT
                    "database": "neo4j"
                },
                "spec": {
                    "max_connection_lifetime": 3600,
                    "max_connection_pool_size": 50,
                    "connection_timeout": 30
                }
            }
            
            if source:
                print(f"Found existing primary_neo4j source (ID: {source.asset_id})")
                source.content = source_content
                print("Updated source content (PLAIN TEXT)")
            else:
                print("Creating new primary_neo4j source...")
                source = TbAssetRegistry(
                    asset_id=uuid4(),
                    asset_type="source",
                    name="primary_neo4j",
                    description="Primary Neo4j graph database for system operations",
                    version=1,
                    status="published",
                    scope="ops",
                    content=source_content,
                    tags={"environment": "production", "source_type": "neo4j"}
                )
                session.add(source)
                print("Created source asset")
            
            session.commit()
            print(f"primary_neo4j source saved (ID: {source.asset_id})")
            
            # 4. Update primary_neo4j_schema with source_ref
            print("\n" + "=" * 80)
            print("Updating primary_neo4j_schema Asset")
            print("=" * 80)
            
            schema = session.exec(
                select(TbAssetRegistry)
                .where(TbAssetRegistry.asset_type == "catalog")
                .where(TbAssetRegistry.name == "primary_neo4j_schema")
                .where(TbAssetRegistry.status == "published")
            ).first()
            
            if schema:
                print(f"Found existing primary_neo4j_schema (ID: {schema.asset_id})")
                if schema.content is None:
                    schema.content = {}
                schema.content["source_ref"] = "primary_neo4j"
                print("Added source_ref: primary_neo4j")
                session.commit()
                print(f"primary_neo4j_schema updated (ID: {schema.asset_id})")
            else:
                print("WARNING: primary_neo4j_schema not found!")
        
        print("\n" + "=" * 80)
        print("✅ Update completed successfully!")
        print("=" * 80)
        print("Source Assets updated with PLAIN TEXT passwords")
        print("=" * 80)

if __name__ == "__main__":
    main()