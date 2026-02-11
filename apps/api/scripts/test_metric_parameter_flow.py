"""
Test the metric tool parameter flow fix.

Tests:
1. Path resolution with wildcard syntax (aggregate.data.rows.*.ci_id)
2. Output mapping extracting ci_ids from aggregate results
3. Empty ci_ids handling (query without ci_id filter)
4. Metric query returning per-CI results grouped by ci_id
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.ops.services.ci.orchestrator.chain_executor import (
    StepResult,
    ToolChainExecutor,
)


def test_wildcard_path_resolution():
    """Test wildcard path resolution for extracting values from arrays."""
    print("\n=== Test 1: Wildcard Path Resolution ===")

    executor = ToolChainExecutor()

    # Simulate aggregate step results with multiple ci_ids
    aggregate_result = StepResult(
        step_id="aggregate",
        success=True,
        data={
            "rows": [
                {"ci_id": "ci-001", "ci_type": "server", "count": 5},
                {"ci_id": "ci-002", "ci_type": "server", "count": 3},
                {"ci_id": "ci-003", "ci_type": "network", "count": 2},
            ]
        },
    )

    results = {"aggregate": aggregate_result}

    # Test wildcard path resolution
    path = "aggregate.data.rows.*.ci_id"
    ci_ids = executor._resolve_path(path, results)

    print(f"  Path: {path}")
    print(f"  Result: {ci_ids}")
    print("  Expected: ['ci-001', 'ci-002', 'ci-003']")

    assert ci_ids == ["ci-001", "ci-002", "ci-003"], f"Expected ['ci-001', 'ci-002', 'ci-003'], got {ci_ids}"
    print("  ✅ PASS: Wildcard path resolution works correctly")


def test_empty_ci_ids_query_processing():
    """Test that empty ci_ids are handled by removing the filter clause."""
    print("\n=== Test 2: Empty CI_IDs Query Processing ===")

    from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

    tool = DynamicTool({
        "name": "metric_test",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": """
SELECT ci.ci_id, ci.ci_name, {function}(mv.value) AS metric_value
FROM metric_value mv
JOIN metric_def md ON mv.metric_id = md.metric_id
JOIN ci ON mv.ci_id = ci.ci_id
WHERE mv.tenant_id = '{tenant_id}'
  AND md.metric_name = '{metric_name}'
  AND mv.ci_id = ANY(ARRAY{ci_ids})
  AND mv.time >= '{start_time}'
  AND mv.time < '{end_time}'
GROUP BY ci.ci_id, ci.ci_name
ORDER BY metric_value DESC
LIMIT {limit}
""",
        },
    })

    input_data = {
        "metric_name": "cpu_usage",
        "function": "AVG",
        "tenant_id": "test-tenant",
        "start_time": "2025-01-24T00:00:00",
        "end_time": "2025-01-31T00:00:00",
        "ci_ids": [],  # Empty array!
        "limit": 10,
    }

    query = tool._process_query_template(tool.tool_config["query_template"], input_data)

    print(f"  Input ci_ids: {input_data['ci_ids']}")
    print(f"  Query (relevant part):\n{query[query.find('WHERE'):query.find('GROUP BY')+30]}")

    # Check that the ci_id filter has been removed
    assert "AND mv.ci_id = ANY(ARRAY" not in query, "ci_id filter should be removed for empty ci_ids"
    print("  ✅ PASS: Empty ci_ids filter is correctly removed")


def test_filled_ci_ids_query_processing():
    """Test that filled ci_ids are processed correctly."""
    print("\n=== Test 3: Filled CI_IDs Query Processing ===")

    from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

    tool = DynamicTool({
        "name": "metric_test",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "default_postgres",
            "query_template": """
SELECT ci.ci_id, ci.ci_name, {function}(mv.value) AS metric_value
FROM metric_value mv
WHERE mv.ci_id = ANY(ARRAY{ci_ids})
""",
        },
    })

    input_data = {
        "function": "AVG",
        "ci_ids": ["ci-001", "ci-002", "ci-003"],
    }

    query = tool._process_query_template(tool.tool_config["query_template"], input_data)

    print(f"  Input ci_ids: {input_data['ci_ids']}")
    print(f"  Query (ci_id part):\n{query[query.find('ANY'):]}")

    # Check that ci_ids are properly formatted
    assert "['ci-001', 'ci-002', 'ci-003']::uuid[]" in query, "ci_ids should be formatted as PostgreSQL array"
    print("  ✅ PASS: Filled ci_ids are correctly formatted for PostgreSQL")


def test_output_mapping_definition():
    """Test that metric tool output_mapping is defined."""
    print("\n=== Test 4: Metric Tool Output Mapping Definition ===")

    from app.modules.ops.services.ci.orchestrator.tool_orchestration import (
        DependencyAnalyzer,
    )
    from app.modules.ops.services.ci.planner.plan_schema import (
        AggregateSpec,
        MetricSpec,
        Plan,
    )

    analyzer = DependencyAnalyzer()

    # Create a plan with both aggregate and metric
    plan = Plan()
    plan.aggregate = AggregateSpec()
    plan.metric = MetricSpec(metric_name="cpu_usage", agg="avg", time_range="last_24h")

    deps = analyzer._infer_dependencies_from_plan(plan)

    # Find metric dependency
    metric_dep = next((d for d in deps if d.tool_id == "metric"), None)

    print(f"  Metric dependency found: {metric_dep is not None}")
    print(f"  Metric depends_on: {metric_dep.depends_on if metric_dep else 'N/A'}")
    print(f"  Metric output_mapping: {metric_dep.output_mapping if metric_dep else 'N/A'}")

    assert metric_dep is not None, "Metric dependency should exist"
    assert metric_dep.depends_on == ["aggregate"], "Metric should depend on aggregate"
    assert "ci_ids" in metric_dep.output_mapping, "output_mapping should contain ci_ids"
    assert metric_dep.output_mapping["ci_ids"] == "aggregate.data.rows.*.ci_id", "output_mapping should use wildcard syntax"

    print("  ✅ PASS: Metric tool output mapping is correctly defined")


def main():
    """Run all tests."""
    print("Testing Metric Tool Parameter Flow Fix")
    print("=" * 50)

    try:
        test_wildcard_path_resolution()
        test_empty_ci_ids_query_processing()
        test_filled_ci_ids_query_processing()
        test_output_mapping_definition()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
