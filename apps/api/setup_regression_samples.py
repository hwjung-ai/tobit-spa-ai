#!/usr/bin/env python
"""
Setup sample Golden Queries for Regression Watch demonstration
"""
import sys
from uuid import uuid4
from datetime import datetime

# Add the project to path
sys.path.insert(0, '/home/spa/tobit-spa-ai/apps/api')

from core.db import engine, get_session_context
from app.modules.inspector.models import TbGoldenQuery, TbRegressionBaseline

# Sample Golden Queries to create
SAMPLE_QUERIES = [
    {
        "name": "RCA Analysis Quality Check",
        "query_text": "Run RCA on execution trace and verify hypothesis generation",
        "ops_type": "all",
        "description": "Monitors RCA engine hypothesis quality"
    },
    {
        "name": "Inspector Trace Retrieval",
        "query_text": "Fetch execution trace details from inspector API",
        "ops_type": "all",
        "description": "Verifies trace data retrieval performance"
    },
    {
        "name": "Asset Registry Query",
        "query_text": "Query published assets from registry",
        "ops_type": "all",
        "description": "Checks asset availability and performance"
    },
]

# Use real trace IDs from database
BASELINE_TRACE_ID = "6c9dcb5d-8e01-4b7f-b4f1-11b2b6bca1cd"  # Real trace

def setup_samples():
    """Create sample Golden Queries and set baselines"""

    with get_session_context() as session:
        print("🚀 Setting up Regression Watch sample data...\n")

        created_queries = []

        for i, query_config in enumerate(SAMPLE_QUERIES, 1):
            # Create Golden Query
            query_id = str(uuid4())
            golden_query = TbGoldenQuery(
                id=query_id,
                name=query_config["name"],
                query_text=query_config["query_text"],
                ops_type=query_config["ops_type"],
                enabled=True,
                options={
                    "description": query_config["description"],
                    "max_hypotheses": 5,
                    "timeout_seconds": 30
                }
            )

            session.add(golden_query)
            session.commit()

            print(f"✅ Created Golden Query {i}/3:")
            print(f"   Name: {query_config['name']}")
            print(f"   ID: {query_id}")

            # Set baseline
            baseline_id = str(uuid4())
            baseline = TbRegressionBaseline(
                id=baseline_id,
                golden_query_id=query_id,
                baseline_trace_id=BASELINE_TRACE_ID,
                baseline_status="success",
                asset_versions=["query@v1.0", "policy@v1.0"],
                created_by="system",
            )

            session.add(baseline)
            session.commit()

            print(f"   📌 Baseline set to trace: {BASELINE_TRACE_ID[:12]}...")
            print(f"   Status: Enabled ✓\n")

            created_queries.append(query_id)

        print("=" * 60)
        print("✅ Setup Complete!")
        print("=" * 60)
        print("\n📊 What's been created:\n")
        print("1️⃣  RCA Analysis Quality Check")
        print("   - Monitors: RCA hypothesis generation quality")
        print("   - Baseline: Current RCA engine output")
        print("   - Use: Run this to verify RCA engine stability\n")

        print("2️⃣  Inspector Trace Retrieval")
        print("   - Monitors: Trace API response time & accuracy")
        print("   - Baseline: Normal trace data format")
        print("   - Use: Run this to verify inspector API stability\n")

        print("3️⃣  Asset Registry Query")
        print("   - Monitors: Asset availability")
        print("   - Baseline: Published assets count")
        print("   - Use: Run this to verify asset registry\n")

        print("=" * 60)
        print("🎯 Next Steps:\n")
        print("1. Go to Admin > Regression page")
        print("2. You'll see 3 'Golden Queries' in the table")
        print("3. Click 'Run' on any query to:")
        print("   - Execute the query again")
        print("   - Compare against baseline")
        print("   - Get PASS/WARN/FAIL result")
        print("4. Multiple runs create a history in 'Recent Runs'\n")

        print("💡 Example Scenarios:\n")
        print("Scenario A - PASS (모두 정상):")
        print("  └─ Current result matches baseline → PASS\n")

        print("Scenario B - WARN (성능 저하):")
        print("  └─ Response time is 2x slower → WARN\n")

        print("Scenario C - FAIL (심각한 오류):")
        print("  └─ RCA fails or returns no data → FAIL\n")

if __name__ == "__main__":
    try:
        setup_samples()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
