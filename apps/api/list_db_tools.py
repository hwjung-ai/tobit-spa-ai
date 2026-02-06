"""
List all tools in database
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select


def list_tools():
    """List all tools in database"""
    with get_session_context() as session:
        query = select(TbAssetRegistry).where(TbAssetRegistry.asset_type == "tool")
        tools = session.exec(query).all()

        print(f"=== Total Tools: {len(tools)} ===")
        for tool in tools:
            print(f"Name: {tool.name}, Status: {tool.status}, Tool Type: {tool.tool_type}")


if __name__ == "__main__":
    list_tools()