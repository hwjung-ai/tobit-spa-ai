#!/usr/bin/env python3
"""
Document Search Tool Publishing Script

Publishes the document_search tool in the asset registry.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from the correct paths
sys.path.insert(0, str(project_root / "apps/api"))

from app.modules.asset_registry.crud import list_assets, publish_asset
from core.db import get_session


async def publish_document_search():
    """Publish document search tool"""

    # Get database session
    session = next(get_session())

    try:
        # Get the tool asset by name and published status
        tools = list_assets(session, asset_type="tool")
        tool_asset = None
        for tool in tools:
            if tool.name == "document_search" and tool.status == "published":
                tool_asset = tool
                break

        if not tool_asset:
            print("❌ Published document_search tool not found")
            return

        print(f"✅ document_search tool found (status: {tool_asset.status})")

        # Check if already published
        if tool_asset.is_published:
            print("✅ document_search tool is already published")
            return

        # Publish the tool
        result = publish_asset(
            session=session,
            asset=tool_asset,
            published_by="system"
        )
        print("✅ document_search tool published successfully")
        print(f"Status: {result.status}")
        print(f"Published at: {result.published_at}")
    except Exception as e:
        print(f"❌ Failed to publish tool: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(publish_document_search())