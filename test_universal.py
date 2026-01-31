#!/usr/bin/env python
"""
Test the Universal Executor with the user's query.
Query: "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"
"""
import sys
import os

# Add API directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

import json
from app.modules.ops.services import execute_universal

def main():
    query = "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"

    print(f"Query: {query}")
    print("=" * 80)

    # Test with different modes
    for mode in ["metric", "history", "relation"]:
        print(f"\n### Testing mode: {mode} ###\n")

        result = execute_universal(
            question=query,
            mode=mode,
            tenant_id="default"
        )

        print(f"Trace ID: {result.trace_id}")
        print(f"Status: {result.status}")
        print(f"Error: {result.error}")
        print(f"Summary: {result.summary}")
        print(f"Blocks: {len(result.blocks)}")
        print(f"Tools used: {result.used_tools}")

        # Print first block detail
        if result.blocks:
            first_block = result.blocks[0]
            if isinstance(first_block, dict):
                print(f"\nFirst block: {first_block.get('title', 'Untitled')}")
                content = first_block.get('content')
                if isinstance(content, list) and len(content) > 0:
                    print(f"Content (first 3 items): {json.dumps(content[:3], indent=2, ensure_ascii=False, default=str)}")
                elif isinstance(content, str):
                    print(f"Content: {content[:500]}")

        print("\n" + "-" * 80)

if __name__ == "__main__":
    main()
