#!/usr/bin/env python3
"""
Test document search directly using the document_search tool asset.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "apps/api"))

from core.db import get_session

from apps.api.app.modules.ops.services.ci.tools.base import get_tool_registry
from apps.api.app.modules.ops.services.ci.tools.registry_init import initialize_tools


async def test_document_search():
    """Test document search tool directly"""

    # Initialize tools
    initialize_tools()
    registry = get_tool_registry()

    # Get database session
    session = next(get_session())

    try:
        # Get the document_search tool
        document_search_tool = registry.get_tool("document_search")
        if not document_search_tool:
            print("❌ document_search tool not found")
            return

        print("✅ document_search tool found")
        print(f"Tool type: {document_search_tool.tool_type}")

        # Test parameters
        test_params = {
            "query": "아키텍처",
            "top_k": 5,
            "search_type": "hybrid"
        }

        # Create tool context
        from app.modules.ops.services.ci.tools.base import ToolContext
        context = ToolContext(
            session=session,
            tenant_id="default",
            user_id="system",
            trace_id="test-trace"
        )

        # Execute the tool
        print("\n🔍 Executing document search...")
        result = await document_search_tool.execute(context, test_params)

        print(f"Result success: {result.success}")
        print(f"Result data: {result.data}")
        print(f"Used tools: {result.used_tools}")

        if result.data and "results" in result.data:
            print(f"\n📄 Found {len(result.data['results'])} results:")
            for i, doc in enumerate(result.data["results"][:3], 1):
                print(f"\n{i}. Document: {doc.get('document_name', 'Unknown')}")
                print(f"   Page: {doc.get('page_number', 'N/A')}")
                print(f"   Text: {doc.get('chunk_text', '')[:100]}...")
        else:
            print("❌ No results found")

    except Exception as e:
        print(f"❌ Error testing document search: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(test_document_search())