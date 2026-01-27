#!/usr/bin/env python3
"""
Test keyword mapping assets loading from planner_llm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    print("\n" + "=" * 70)
    print("   KEYWORD MAPPING ASSETS 로딩 테스트")
    print("=" * 70)

    from app.modules.ops.services.ci.planner.planner_llm import (
        _get_metric_aliases,
        _get_agg_keywords,
        _get_series_keywords,
        _get_history_keywords,
        _get_list_keywords,
        _get_table_hints,
        _get_cep_keywords,
        _get_graph_scope_keywords,
        _get_auto_keywords,
        _get_filterable_fields,
    )

    tests = []

    # 1. metric_aliases
    print("\n1️⃣  metric_aliases")
    try:
        data = _get_metric_aliases()
        aliases = data.get("aliases", {})
        keywords = data.get("keywords", [])
        print(f"   ✅ Loaded: {len(aliases)} aliases, {len(keywords)} keywords")
        print(f"   Sample: cpu → {aliases.get('cpu')}, memory → {aliases.get('memory')}")
        tests.append(("metric_aliases", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("metric_aliases", False))

    # 2. agg_keywords
    print("\n2️⃣  agg_keywords")
    try:
        data = _get_agg_keywords()
        print(f"   ✅ Loaded: {len(data)} mappings")
        print(f"   Sample: 최대 → {data.get('최대')}, 평균 → {data.get('평균')}")
        tests.append(("agg_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("agg_keywords", False))

    # 3. series_keywords
    print("\n3️⃣  series_keywords")
    try:
        data = _get_series_keywords()
        print(f"   ✅ Loaded: {len(data)} keywords")
        print(f"   Sample: {list(data)[:3]}")
        tests.append(("series_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("series_keywords", False))

    # 4. history_keywords
    print("\n4️⃣  history_keywords")
    try:
        data = _get_history_keywords()
        keywords = data.get("keywords", set())
        time_map = data.get("time_map", {})
        print(f"   ✅ Loaded: {len(keywords)} keywords, {len(time_map)} time mappings")
        print(f"   Sample keywords: {list(keywords)[:2]}")
        tests.append(("history_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("history_keywords", False))

    # 5. list_keywords
    print("\n5️⃣  list_keywords")
    try:
        data = _get_list_keywords()
        print(f"   ✅ Loaded: {len(data)} keywords")
        print(f"   Sample: {list(data)[:3]}")
        tests.append(("list_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("list_keywords", False))

    # 6. table_hints
    print("\n6️⃣  table_hints")
    try:
        data = _get_table_hints()
        print(f"   ✅ Loaded: {len(data)} hints")
        print(f"   Sample: {list(data)[:3]}")
        tests.append(("table_hints", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("table_hints", False))

    # 7. cep_keywords
    print("\n7️⃣  cep_keywords")
    try:
        data = _get_cep_keywords()
        print(f"   ✅ Loaded: {len(data)} keywords")
        print(f"   Sample: {list(data)[:3]}")
        tests.append(("cep_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("cep_keywords", False))

    # 8. graph_scope_keywords
    print("\n8️⃣  graph_scope_keywords")
    try:
        data = _get_graph_scope_keywords()
        scope_kw = data.get("scope_keywords", set())
        metric_kw = data.get("metric_keywords", set())
        print(f"   ✅ Loaded: {len(scope_kw)} scope keywords, {len(metric_kw)} metric keywords")
        tests.append(("graph_scope_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("graph_scope_keywords", False))

    # 9. auto_keywords
    print("\n9️⃣  auto_keywords")
    try:
        data = _get_auto_keywords()
        print(f"   ✅ Loaded: {len(data)} keywords")
        print(f"   Sample: {list(data)[:3]}")
        tests.append(("auto_keywords", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("auto_keywords", False))

    # 10. filterable_fields
    print("\n🔟 filterable_fields")
    try:
        data = _get_filterable_fields()
        tag_keys = data.get("tag_keys", set())
        attr_keys = data.get("attr_keys", set())
        print(f"   ✅ Loaded: {len(tag_keys)} tag keys, {len(attr_keys)} attr keys")
        tests.append(("filterable_fields", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        tests.append(("filterable_fields", False))

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
        print("\n🎉 All keyword mapping assets are loading correctly!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
