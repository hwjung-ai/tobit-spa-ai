"""
Update ci_aggregate tool with proper query template for generic orchestration.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def main():
    """Update ci_aggregate tool with proper query template."""
    with get_session_context() as session:
        query = select(TbAssetRegistry).where(TbAssetRegistry.name == "ci_aggregate")
        tool = session.exec(query).first()

        if not tool:
            print("ci_aggregate tool not found, creating...")
            tool = TbAssetRegistry(
                asset_type="tool",
                name="ci_aggregate",
                description="Aggregate CI data with COUNT, GROUP BY operations",
                tool_type="database_query",
                status="published",
                version=1,
            )
            session.add(tool)
        else:
            print(f"Found ci_aggregate tool v{tool.version}, updating...")

        # Update tool_config with proper query template
        tool.tool_config = {
            "source_ref": "default_postgres",
            "query_template": """
SELECT {select_field}, COUNT(*) as count
FROM ci
WHERE tenant_id = '{tenant_id}' AND deleted_at IS NULL
GROUP BY {select_field}
ORDER BY count DESC
LIMIT {limit}
""",
        }

        # Update input schema for generic use
        tool.tool_input_schema = {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to group by (e.g., ci_type, status)",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                },
            },
        }

        tool.tool_output_schema = {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {"type": "object"},
                }
            },
        }

        session.commit()
        print("✅ ci_aggregate tool updated successfully!")


if __name__ == "__main__":
    main()
