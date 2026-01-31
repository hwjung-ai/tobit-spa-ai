#!/usr/bin/env python
"""
Test the CI Ask endpoint with the user's query.
This uses the CI orchestration runner, not LangGraph.
"""
import requests
import json

def main():
    query = "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"
    
    print(f"Query: {query}")
    print("=" * 80)
    
    response = requests.post(
        "http://localhost:8000/ops/ci/ask",
        json={"question": query},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()["data"]
    
    print(f"\nTrace ID: {data['trace']['trace_id']}")
    print(f"Status: {data['trace'].get('status', 'unknown')}")
    print(f"Route: {data['trace'].get('route', 'unknown')}")
    print("\n" + "=" * 80)
    print("ANSWER:")
    print("=" * 80)
    
    # Print answer blocks
    blocks = data.get('answer', {}).get('blocks', [])
    for i, block in enumerate(blocks, 1):
        title = block.get('title', 'Untitled')
        content = block.get('content', '')
        print(f"\n[Block {i}] {title}")
        print("-" * 80)
        if isinstance(content, str):
            print(content[:500])
        else:
            print(json.dumps(content, indent=2, ensure_ascii=False)[:500])
    
    print("\n" + "=" * 80)
    print(f"Tools used: {data.get('answer', {}).get('meta', {}).get('used_tools', [])}")
    print("=" * 80)

if __name__ == "__main__":
    main()
