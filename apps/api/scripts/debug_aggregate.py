"""
Debug aggregate tool parameters and query processing
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.ops.services.orchestration.tools.dynamic_tool import DynamicTool


def test_aggregate_query_processing():
    """Test aggregate tool query processing with sample data."""
    print("=== Test Aggregate Tool Query Processing ===")

    # Load aggregate tool from asset registry
    tool = DynamicTool({
        "name": "ci_aggregate",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": """
SELECT {select_field}, COUNT(*) as count
FROM ci
WHERE tenant_id = '{tenant_id}' AND deleted_at IS NULL
GROUP BY {select_field}
ORDER BY count DESC
LIMIT {limit}
""",
        },
    })

    # Sample input data
    input_data = {
        "tenant_id": "test-tenant",
        "group_by": ["ci_type"],
        "limit": 10,
        "metrics": ["count"]
    }

    print(f"Input data: {input_data}")
    print(f"\nQuery template:\n{tool.tool_config['query_template']}")

    # Process the query
    processed_query = tool._process_query_template(tool.tool_config["query_template"], input_data)

    print(f"\nProcessed query:\n{processed_query}")

    # Verify placeholders are replaced
    print("\n=== Verification ===")
    if "{select_field}" in processed_query:
        print("❌ select_field NOT replaced")
    else:
        print("✅ select_field replaced")

    if "{tenant_id}" in processed_query:
        print("❌ tenant_id NOT replaced")
    else:
        print("✅ tenant_id replaced")

    if "{limit}" in processed_query:
        print("❌ limit NOT replaced")
    else:
        print("✅ limit replaced")


if __name__ == "__main__":
    test_aggregate_query_processing()
