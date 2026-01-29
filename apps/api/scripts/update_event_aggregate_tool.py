"""
Update event_aggregate tool with proper query template for generic orchestration.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry
from sqlmodel import select, update


def main():
    """Update event_aggregate tool with proper query template."""
    with get_session_context() as session:
        # Find existing event_aggregate tool
        query = select(TbAssetRegistry).where(TbAssetRegistry.name == "event_aggregate")
        tool = session.exec(query).first()

        if not tool:
            print("event_aggregate tool not found, creating...")
            tool = TbAssetRegistry(
                asset_type="tool",
                name="event_aggregate",
                description="Aggregate event_log data by event_type, severity, or other fields",
                tool_type="database_query",
                status="published",
                version=1,
            )
            session.add(tool)
        else:
            print(f"Found event_aggregate tool v{tool.version}, updating...")

        # Update tool_config with proper query template
        tool.tool_config = {
            "source_ref": "default_postgres",
            "query_template": """
SELECT {group_field}, COUNT(*) as count
FROM event_log
WHERE tenant_id = '{tenant_id}' AND deleted_at IS NULL {time_filter}
GROUP BY {group_field}
ORDER BY count DESC
LIMIT {limit}
""",
        }

        # Update input schema for generic use
        tool.tool_input_schema = {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "enum": ["event_type", "severity", "source"],
                    "description": "Field to group by",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                },
                "time_range": {
                    "type": "string",
                    "description": "Optional time range filter",
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
        print("✅ event_aggregate tool updated successfully!")


if __name__ == "__main__":
    main()
