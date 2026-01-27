#!/usr/bin/env python3
"""
Test Phase 1 and Phase 2 implementations.

Tests:
1. Phase 1: Tenant ID validation
2. Phase 1: Timezone configuration
3. Phase 2: View policy loading from DB
4. Phase 2: Relation allowlist loading from DB
5. Phase 2: Budget policy required (no fallback)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

def test_tenant_id_validation():
    """Test that tenant_id is required (no default 't1')."""
    print("\n" + "="*60)
    print("TEST 1: Tenant ID Validation")
    print("="*60)

    from app.modules.ops.services.ci.tools.query_registry import _get_required_tenant_id

    # Test 1.1: Should raise error when tenant_id is missing
    try:
        _get_required_tenant_id({})
        print("❌ FAILED: Should have raised ValueError for missing tenant_id")
        return False
    except ValueError as e:
        print(f"✅ PASSED: Correctly raised ValueError: {e}")

    # Test 1.2: Should return tenant_id when provided
    try:
        result = _get_required_tenant_id({"tenant_id": "test_tenant"})
        if result == "test_tenant":
            print(f"✅ PASSED: Correctly returned tenant_id: {result}")
        else:
            print(f"❌ FAILED: Expected 'test_tenant', got '{result}'")
            return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    return True


def test_timezone_configuration():
    """Test that timezone is loaded from configuration."""
    print("\n" + "="*60)
    print("TEST 2: Timezone Configuration")
    print("="*60)

    from datetime import timezone, timedelta
    from core.config import get_settings

    settings = get_settings()

    # Test 2.1: Check ops_timezone setting exists
    if hasattr(settings, 'ops_timezone'):
        print(f"✅ PASSED: ops_timezone setting exists: {settings.ops_timezone}")
    else:
        print("❌ FAILED: ops_timezone setting not found")
        return False

    # Test 2.2: Check timezone_offset property
    if hasattr(settings, 'timezone_offset'):
        tz_offset = settings.timezone_offset
        print(f"✅ PASSED: timezone_offset property exists: {tz_offset}")

        # For Asia/Seoul, should be UTC+9
        expected_offset = timezone(timedelta(hours=9))
        if tz_offset == expected_offset:
            print(f"✅ PASSED: Correctly returns UTC+9 for Asia/Seoul")
        else:
            print(f"⚠️  WARNING: Expected UTC+9, got {tz_offset}")
    else:
        print("❌ FAILED: timezone_offset property not found")
        return False

    return True


def test_view_policy_loading():
    """Test that view policies are loaded from DB."""
    print("\n" + "="*60)
    print("TEST 3: View Policy Loading from DB")
    print("="*60)

    from app.modules.ops.services.ci.view_registry import get_view_registry, get_view_policy

    # Test 3.1: Load all view policies
    try:
        registry = get_view_registry()
        print(f"✅ PASSED: Loaded view registry with {len(registry)} views")

        expected_views = ["SUMMARY", "COMPOSITION", "DEPENDENCY", "IMPACT", "PATH", "NEIGHBORS"]
        for view_name in expected_views:
            if view_name in registry:
                print(f"   ✓ {view_name}: depth={registry[view_name].default_depth}/{registry[view_name].max_depth}")
            else:
                print(f"   ✗ {view_name}: NOT FOUND")
                return False
    except Exception as e:
        print(f"❌ FAILED: Error loading view registry: {e}")
        return False

    # Test 3.2: Get specific view policy
    try:
        summary_policy = get_view_policy("SUMMARY")
        if summary_policy:
            print(f"✅ PASSED: get_view_policy('SUMMARY') returned: {summary_policy.name}")
        else:
            print("❌ FAILED: get_view_policy('SUMMARY') returned None")
            return False
    except Exception as e:
        print(f"❌ FAILED: Error getting view policy: {e}")
        return False

    return True


def test_relation_allowlist_loading():
    """Test that relation allowlist is loaded from DB."""
    print("\n" + "="*60)
    print("TEST 4: Relation Allowlist Loading from DB")
    print("="*60)

    from app.modules.ops.services.ci.policy import _ensure_summary_neighbors_allowlist

    try:
        allowlist = _ensure_summary_neighbors_allowlist()
        print(f"✅ PASSED: Loaded allowlist with {len(allowlist)} relation types:")
        for rel_type in allowlist:
            print(f"   • {rel_type}")

        # Check for expected relation types
        expected_types = ["COMPOSED_OF", "DEPENDS_ON", "RUNS_ON"]
        for rel_type in expected_types:
            if rel_type in allowlist:
                print(f"   ✓ {rel_type} found")
            else:
                print(f"   ⚠️  {rel_type} not found (may have been changed in DB)")

        return True
    except Exception as e:
        print(f"❌ FAILED: Error loading relation allowlist: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_budget_policy_required():
    """Test that budget policy is required (no fallback)."""
    print("\n" + "="*60)
    print("TEST 5: Budget Policy Required (No Fallback)")
    print("="*60)

    from app.modules.asset_registry.loader import load_policy_asset

    # Test 5.1: Load plan_budget policy (should succeed if exists in DB)
    try:
        # Try with the actual name in DB
        policy = load_policy_asset("plan_budget_default")
        if policy:
            print(f"✅ PASSED: Successfully loaded plan_budget_default policy from DB")
            print(f"   Policy keys: {list(policy.keys())}")
        else:
            print("⚠️  WARNING: plan_budget_default policy returned None")
    except Exception as e:
        print(f"⚠️  INFO: plan_budget_default not found: {e}")

    # Test 5.2: Try loading non-existent policy (should raise error, not fallback)
    try:
        policy = load_policy_asset("nonexistent_policy_xyz")
        print(f"❌ FAILED: Should have raised ValueError for non-existent policy, but got: {policy}")
        return False
    except ValueError as e:
        if "required but not found" in str(e):
            print(f"✅ PASSED: Correctly raised ValueError with proper message")
        else:
            print(f"⚠️  WARNING: Raised ValueError but message unclear: {e}")
    except Exception as e:
        print(f"❌ FAILED: Unexpected error type: {type(e).__name__}: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("\n" + "🧪 " + "="*58)
    print("   PHASE 1 & PHASE 2 IMPLEMENTATION TESTS")
    print("="*60)

    tests = [
        ("Tenant ID Validation", test_tenant_id_validation),
        ("Timezone Configuration", test_timezone_configuration),
        ("View Policy Loading", test_view_policy_loading),
        ("Relation Allowlist Loading", test_relation_allowlist_loading),
        ("Budget Policy Required", test_budget_policy_required),
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
    print("\n" + "="*60)
    print("   TEST SUMMARY")
    print("="*60)

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
