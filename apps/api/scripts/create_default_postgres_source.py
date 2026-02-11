"""
Create default_postgres source asset for generic orchestration tools.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def main():
    """Create default_postgres source asset."""
    with get_session_context() as session:
        # Check if already exists
        query = select(TbAssetRegistry).where(TbAssetRegistry.name == "default_postgres")
        existing = session.exec(query).first()

        if existing:
            print(f"Source 'default_postgres' already exists (v{existing.version}), skipping...")
            return

        # Get DB connection from settings
        from core.config import get_settings
        settings = get_settings()

        source = TbAssetRegistry(
            asset_type="source",
            name="default_postgres",
            description="Default PostgreSQL database connection for generic orchestration",
            source_type="postgres",
            status="published",
            version=1,
            # Connection params
            connection_params={
                "host": settings.pg_host,
                "port": settings.pg_port,
                "database": settings.pg_db,
                "user": settings.pg_user,
                "password": settings.pg_password,
            },
        )
        session.add(source)
        session.commit()
        print("✅ Created default_postgres source asset")


if __name__ == "__main__":
    main()
