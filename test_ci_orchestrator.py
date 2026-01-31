#!/usr/bin/env python
"""
Test the CI Orchestrator with the user's query.
Query: "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"
"""
import sys
import os

# Add API directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps', 'api'))

import asyncio
import json
from app.modules.ops.services.ci.orchestrator.runner import CIOrchestratorRunner

async def main():
    query = "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"

    print(f"Query: {query}")
    print("=" * 80)

    runner = CIOrchestratorRunner(tenant_id="default")
    result = await runner.ask(question=query)

    print(f"\nTrace ID: {result.trace_id}")
    print(f"Status: {result.status}")
    print(f"Error: {result.error}")
    print(f"Summary: {result.summary}")
    print("\n" + "=" * 80)
    print("ANSWER:")
    print("=" * 80)

    # Print answer blocks
    for i, block in enumerate(result.blocks, 1):
        if isinstance(block, dict):
            print(f"\n[Block {i}] {block.get('title', 'Untitled')}")
            print("-" * 80)
            content = block.get('content')
            if isinstance(content, (list, dict)):
                print(json.dumps(content, indent=2, ensure_ascii=False, default=str))
            else:
                print(content)
        else:
            print(f"\n[Block {i}]")
            print("-" * 80)
            if hasattr(block, 'title') and hasattr(block, 'content'):
                print(f"Title: {block.title}")
                print(f"Content: {block.content}")
            else:
                print(str(block))

    print("\n" + "=" * 80)
    print(f"Tools used: {result.used_tools}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
