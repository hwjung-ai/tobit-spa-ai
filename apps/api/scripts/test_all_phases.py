#!/usr/bin/env python3
"""
Comprehensive test for all phases of hardcoding removal.

Tests:
Phase 1: Tenant ID validation and Timezone configuration
Phase 2: View policy and Relation allowlist loading from DB
Phase 3: Tool limits and Time ranges loading from DB
Phase 4: Column allowlist and Discovery config loading from DB
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_phase3_tool_limits():
    """Test Phase 3: Tool limits loading from DB."""
    print("\n" + "=" * 60)
    print("TEST: Phase 3 - Tool Limits Loading")
    print("=" * 60)

    # Test CI tool limits
    try:
        from app.modules.ops.services.ci.tools.ci import _get_limits as ci_get_limits
        limits = ci_get_limits()
        print(f"✅ CI tool limits loaded: {limits}")
        assert "max_search_limit" in limits
        assert "max_agg_rows" in limits
        print(f"   ✓ max_search_limit: {limits['max_search_limit']}")
        print(f"   ✓ max_agg_rows: {limits['max_agg_rows']}")
    except Exception as e:
        print(f"❌ FAILED: CI tool limits: {e}")
        return False

    # Test History tool limits
    try:
        from app.modules.ops.services.ci.tools.history import _get_limits as history_get_limits
        limits = history_get_limits()
        print(f"✅ History tool limits loaded: {limits}")
        assert "max_limit" in limits
        print(f"   ✓ max_limit: {limits['max_limit']}")
    except Exception as e:
        print(f"❌ FAILED: History tool limits: {e}")
        return False

    # Test Graph tool limits
    try:
        from app.modules.ops.services.ci.tools.graph import _get_limits as graph_get_limits
        limits = graph_get_limits()
        print(f"✅ Graph tool limits loaded: {limits}")
        assert "max_nodes" in limits
        assert "max_edges" in limits
        assert "max_paths" in limits
        print(f"   ✓ max_nodes: {limits['max_nodes']}")
        print(f"   ✓ max_edges: {limits['max_edges']}")
        print(f"   ✓ max_paths: {limits['max_paths']}")
    except Exception as e:
        print(f"❌ FAILED: Graph tool limits: {e}")
        return False

    # Test Metric tool limits
    try:
        from app.modules.ops.services.ci.tools.metric import _get_limits as metric_get_limits
        limits = metric_get_limits()
        print(f"✅ Metric tool limits loaded: {limits}")
        assert "max_ci_ids" in limits
        print(f"   ✓ max_ci_ids: {limits['max_ci_ids']}")
    except Exception as e:
        print(f"❌ FAILED: Metric tool limits: {e}")
        return False

    return True


def test_phase3_time_ranges():
    """Test Phase 3: Time ranges loading from DB."""
    print("\n" + "=" * 60)
    print("TEST: Phase 3 - Time Ranges Loading")
    print("=" * 60)

    # Test History time ranges
    try:
        from app.modules.ops.services.ci.tools.history import _get_time_ranges as history_get_time_ranges
        time_ranges = history_get_time_ranges()
        print(f"✅ History time ranges loaded: {len(time_ranges)} ranges")
        for key, delta in time_ranges.items():
            print(f"   ✓ {key}: {delta}")
    except Exception as e:
        print(f"❌ FAILED: History time ranges: {e}")
        return False

    # Test Metric time ranges
    try:
        from app.modules.ops.services.ci.tools.metric import _get_time_ranges as metric_get_time_ranges
        time_ranges = metric_get_time_ranges()
        print(f"✅ Metric time ranges loaded: {len(time_ranges)} ranges")
        for key, delta in time_ranges.items():
            print(f"   ✓ {key}: {delta}")
    except Exception as e:
        print(f"❌ FAILED: Metric time ranges: {e}")
        return False

    return True


def test_phase3_column_allowlist():
    """Test Phase 3: Column allowlist loading from DB."""
    print("\n" + "=" * 60)
    print("TEST: Phase 3 - Column Allowlist Loading")
    print("=" * 60)

    try:
        from app.modules.ops.services.ci.tools.ci import _get_column_allowlist
        allowlist = _get_column_allowlist()
        print(f"✅ CI column allowlist loaded")
        assert "search_columns" in allowlist
        assert "filter_fields" in allowlist
        assert "jsonb_tag_keys" in allowlist
        assert "jsonb_attr_keys" in allowlist
        print(f"   ✓ search_columns: {len(allowlist['search_columns'])} columns")
        print(f"   ✓ filter_fields: {len(allowlist['filter_fields'])} fields")
        print(f"   ✓ jsonb_tag_keys: {len(allowlist['jsonb_tag_keys'])} keys")
        print(f"   ✓ jsonb_attr_keys: {len(allowlist['jsonb_attr_keys'])} keys")
        return True
    except Exception as e:
        print(f"❌ FAILED: Column allowlist: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase4_discovery_config():
    """Test Phase 4: Discovery config loading from DB."""
    print("\n" + "=" * 60)
    print("TEST: Phase 4 - Discovery Config Loading")
    print("=" * 60)

    # Test PostgreSQL discovery config
    try:
        from app.modules.ops.services.ci.discovery.postgres_catalog import _get_discovery_config as postgres_get_discovery_config
        config = postgres_get_discovery_config()
        print(f"✅ PostgreSQL discovery config loaded")
        assert "target_tables" in config
        assert "agg_columns" in config
        print(f"   ✓ target_tables: {config['target_tables']}")
        print(f"   ✓ agg_columns: {config['agg_columns']}")
    except Exception as e:
        print(f"❌ FAILED: PostgreSQL discovery config: {e}")
        return False

    # Test Neo4j discovery config
    try:
        from app.modules.ops.services.ci.discovery.neo4j_catalog import _get_discovery_config as neo4j_get_discovery_config
        config = neo4j_get_discovery_config()
        print(f"✅ Neo4j discovery config loaded")
        assert "expected_ci_properties" in config
        print(f"   ✓ expected_ci_properties: {config['expected_ci_properties']}")
    except Exception as e:
        print(f"❌ FAILED: Neo4j discovery config: {e}")
        return False

    return True


def main():
    """Run all phase tests."""
    print("\n" + "🧪 " + "=" * 58)
    print("   COMPREHENSIVE HARDCODING REMOVAL TESTS")
    print("=" * 60)

    # Phase 1 & 2 were already tested in test_phase1_phase2.py
    # We'll focus on Phase 3 & 4 here

    tests = [
        ("Phase 3 - Tool Limits", test_phase3_tool_limits),
        ("Phase 3 - Time Ranges", test_phase3_time_ranges),
        ("Phase 3 - Column Allowlist", test_phase3_column_allowlist),
        ("Phase 4 - Discovery Config", test_phase4_discovery_config),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("   TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
