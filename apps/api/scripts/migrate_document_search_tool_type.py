#!/usr/bin/env python3
"""
Migrate document_search Tool Asset to standard http_api type.

This script keeps the tool name as `document_search` (used by plans/tool selector)
and updates execution type + tags for capability-based routing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlmodel import Session, select

# Add project root to path for `app.*` imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import engine


def migrate() -> None:
    with Session(engine) as session:
        tool = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "tool")
            .where(TbAssetRegistry.name == "document_search")
        ).first()

        if not tool:
            print("document_search tool not found")
            return

        tags = dict(tool.tags or {})
        capabilities = tags.get("capabilities")
        if not isinstance(capabilities, list):
            capabilities = []
        if "document_search" not in capabilities:
            capabilities.append("document_search")
        tags["capabilities"] = capabilities

        supported_modes = tags.get("supported_modes")
        if not isinstance(supported_modes, list):
            supported_modes = []
        for mode in ["document", "all"]:
            if mode not in supported_modes:
                supported_modes.append(mode)
        tags["supported_modes"] = supported_modes

        tool_config = dict(tool.tool_config or {})
        # Tool validator for http_api requires `url`.
        if not tool_config.get("url") and tool_config.get("endpoint"):
            tool_config["url"] = tool_config["endpoint"]

        old_type = tool.tool_type
        tool.tool_type = "http_api"
        tool.tags = tags
        tool.tool_config = tool_config
        session.add(tool)
        session.commit()
        session.refresh(tool)

        print(
            "migrated",
            {
                "asset_id": str(tool.asset_id),
                "name": tool.name,
                "old_tool_type": old_type,
                "new_tool_type": tool.tool_type,
                "capabilities": tags.get("capabilities"),
                "supported_modes": tags.get("supported_modes"),
            },
        )


if __name__ == "__main__":
    migrate()
