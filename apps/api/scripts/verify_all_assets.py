#!/usr/bin/env python3
"""
Verify all policy assets are properly loaded from DB.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    print("\n" + "=" * 70)
    print("   FINAL VERIFICATION: All Policy Assets Loading from DB")
    print("=" * 70)

    tests = []

    # 1. View Registry
    print("\n1️⃣  View Registry (view_depth)")
    try:
        from app.modules.ops.services.orchestration.view_registry import get_view_registry
        registry = get_view_registry()
        print(f"   ✅ Loaded {len(registry)} views from DB")
        tests.append(("View Registry", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("View Registry", False))

    # 2. Tool Limits
    print("\n2️⃣  Tool Limits (tool_limits)")
    try:
        from app.modules.ops.services.orchestration.tools.ci import _get_limits as ci_limits
        from app.modules.ops.services.orchestration.tools.graph import _get_limits as graph_limits
        from app.modules.ops.services.orchestration.tools.history import (
            _get_limits as history_limits,
        )
        from app.modules.ops.services.orchestration.tools.metric import (
            _get_limits as metric_limits,
        )

        ci = ci_limits()
        hist = history_limits()
        graph = graph_limits()
        metric = metric_limits()

        print(f"   ✅ CI: {ci}")
        print(f"   ✅ History: {hist}")
        print(f"   ✅ Graph: {graph}")
        print(f"   ✅ Metric: {metric}")
        tests.append(("Tool Limits", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("Tool Limits", False))

    # 3. Time Ranges
    print("\n3️⃣  Time Ranges (time_ranges)")
    try:
        from app.modules.ops.services.orchestration.tools.history import (
            _get_time_ranges as history_ranges,
        )
        from app.modules.ops.services.orchestration.tools.metric import (
            _get_time_ranges as metric_ranges,
        )

        hist_ranges = history_ranges()
        metric_ranges = metric_ranges()

        print(f"   ✅ History: {len(hist_ranges)} ranges")
        print(f"   ✅ Metric: {len(metric_ranges)} ranges")
        tests.append(("Time Ranges", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("Time Ranges", False))

    # 4. Column Allowlist
    print("\n4️⃣  Column Allowlist (column_allowlist)")
    try:
        from app.modules.ops.services.orchestration.tools.ci import _get_column_allowlist
        allowlist = _get_column_allowlist()
        print(f"   ✅ Search columns: {len(allowlist['search_columns'])}")
        print(f"   ✅ Filter fields: {len(allowlist['filter_fields'])}")
        tests.append(("Column Allowlist", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("Column Allowlist", False))

    # 5. Discovery Config
    print("\n5️⃣  Discovery Config (discovery_config)")
    try:
        from app.modules.ops.services.orchestration.discovery.neo4j_catalog import (
            _get_discovery_config as neo4j_config,
        )
        from app.modules.ops.services.orchestration.discovery.postgres_catalog import (
            _get_discovery_config as pg_config,
        )

        pg = pg_config()
        neo4j = neo4j_config()

        print(f"   ✅ PostgreSQL: {pg['target_tables']}")
        print(f"   ✅ Neo4j: {neo4j['expected_ci_properties']}")
        tests.append(("Discovery Config", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("Discovery Config", False))

    # Summary
    print("\n" + "=" * 70)
    print("   SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All policy assets are loading correctly from DB!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
