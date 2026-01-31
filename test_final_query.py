#!/usr/bin/env python
"""
Test the complete OPS orchestration with the user's query.
Query: "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"
"""
import sys
import os

# Add API directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

import json
from app.modules.ops.services import handle_ops_query

def main():
    query = "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"

    print(f"Query: {query}")
    print("=" * 80)

    envelope, trace_data = handle_ops_query(
        mode="all",
        question=query
    )

    result = envelope

    trace_id = result.meta.trace_id if result.meta else None
    print(f"\nTrace ID: {trace_id}")
    if trace_data:
        print(f"Status: {trace_data.get('status', 'unknown')}")
        print(f"Error: {trace_data.get('error')}")
    print("\n" + "=" * 80)
    print("ANSWER:")
    print("=" * 80)

    # Print answer blocks
    for i, block in enumerate(result.blocks, 1):
        if hasattr(block, 'title') and hasattr(block, 'content'):
            print(f"\n[Block {i}] {block.title}")
            print("-" * 80)
            print(block.content)
        elif isinstance(block, dict):
            print(f"\n[Block {i}] {block.get('title', 'Untitled')}")
            print("-" * 80)
            print(block.get('content', str(block)))
        else:
            print(f"\n[Block {i}]")
            print("-" * 80)
            print(str(block))

    print("\n" + "=" * 80)
    if result.meta and hasattr(result.meta, 'used_tools'):
        print(f"Tools used: {result.meta.used_tools}")
    print("=" * 80)

if __name__ == "__main__":
    main()
