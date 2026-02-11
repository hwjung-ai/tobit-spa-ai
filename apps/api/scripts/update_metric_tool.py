"""
Update metric tool with improved query template for per-CI metrics.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select


def main():
    """Update metric tool with improved query template."""
    with get_session_context() as session:
        query = select(TbAssetRegistry).where(TbAssetRegistry.name == "metric")
        tool = session.exec(query).first()

        if not tool:
            print("metric tool not found!")
            return

        print(f"Found metric tool v{tool.version}, updating...")

        # Update tool_config with improved query template
        tool.tool_config = {
            "source_ref": "default_postgres",
            "query_template": """
SELECT ci.ci_id, ci.ci_name, {function}(mv.value) AS metric_value
FROM metric_value mv
JOIN metric_def md ON mv.metric_id = md.metric_id
JOIN ci ON mv.ci_id = ci.ci_id
WHERE mv.tenant_id = '{tenant_id}'
  AND md.metric_name = '{metric_name}'
  AND mv.ci_id = ANY(ARRAY{ci_ids})
  AND mv.time >= '{start_time}'
  AND mv.time < '{end_time}'
GROUP BY ci.ci_id, ci.ci_name
ORDER BY metric_value DESC
LIMIT {limit}
""",
        }

        # Update description
        tool.description = "Query metric values grouped by CI, ordered by value (highest first)"

        session.commit()
        print("✅ metric tool updated successfully with per-CI metrics query!")


if __name__ == "__main__":
    main()
