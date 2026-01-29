"""
Test tool loading from Asset Registry.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.ops.services.ci.tools.base import get_tool_registry
from app.modules.ops.services.ci.tools.registry_init import initialize_tools


def main():
    """Test tool loading and registry."""
    print("Testing tool loading from Asset Registry...")
    print()

    # Initialize tools (this happens at module import, but we call it explicitly for testing)
    initialize_tools()

    # Get registry
    registry = get_tool_registry()

    # List all tools
    all_tools = registry.get_available_tools()
    print(f"Total tools loaded: {len(all_tools)}")
    print()

    # Group by type
    tools_by_type = {}
    for tool_name, tool_instance in all_tools.items():
        tool_type = getattr(tool_instance, 'tool_type', 'unknown')
        if tool_type not in tools_by_type:
            tools_by_type[tool_type] = []
        tools_by_type[tool_type].append(tool_name)

    # Display tools by type
    for tool_type, tool_names in sorted(tools_by_type.items()):
        print(f"{tool_type}:")
        for name in sorted(tool_names):
            tool = all_tools[name]
            desc = getattr(tool, 'description', 'No description')
            print(f"  - {name}: {desc}")
        print()

    # Check for CI-related tools
    ci_tools = ['ci_search', 'ci_aggregate']
    metric_tools = ['metric_aggregate', 'metric_list']
    event_tools = ['event_log', 'event_aggregate']

    print("Checking for expected tools:")
    for tool_name in ci_tools + metric_tools + event_tools:
        if tool_name in all_tools:
            print(f"  ✓ {tool_name} found")
        else:
            print(f"  ✗ {tool_name} NOT found")

    print()
    print("✅ Tool loading test complete!")


if __name__ == "__main__":
    main()
