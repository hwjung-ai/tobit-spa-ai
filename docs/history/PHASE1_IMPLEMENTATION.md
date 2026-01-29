# Phase 1 Implementation: Plan Schema Extension

## Overview

**Objective**: Add `tool_type` field to all Plan Spec classes to enable dynamic tool selection

**Duration**: 1 day

**Files to Modify**:
- `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`

**Files to Test**:
- `apps/api/tests/test_plan_schema.py` (existing or create new)

---

## Current State

### Current PrimarySpec (before)
```python
class PrimarySpec(SQLModel):
    """Specification for primary query in a plan."""

    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
```

### Current MetricSpec (before)
```python
class MetricSpec(SQLModel):
    """Specification for metric query in a plan."""

    metric_name: str
    agg: str = "avg"
    time_range: TimeRangeSpec
    mode: str = "metric"
    scope: Optional[str] = None
```

---

## Changes Required

### 1. Add to PrimarySpec

```python
class PrimarySpec(SQLModel):
    """Specification for primary query in a plan."""

    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for primary query execution"
    )
```

### 2. Add to SecondarySpec

```python
class SecondarySpec(SQLModel):
    """Specification for secondary query in a plan."""

    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for secondary query execution"
    )
```

### 3. Add to MetricSpec

```python
class MetricSpec(SQLModel):
    """Specification for metric query in a plan."""

    metric_name: str
    agg: str = "avg"
    time_range: TimeRangeSpec
    mode: str = "metric"
    scope: Optional[str] = None
    tool_type: str = Field(
        default="metric_query",
        description="Tool to use for metric query execution"
    )
```

### 4. Add to AggregateSpec

```python
class AggregateSpec(SQLModel):
    """Specification for aggregate query in a plan."""

    group_by: Optional[str] = None
    metrics: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    scope: Optional[str] = None
    top_n: Optional[int] = None
    tool_type: str = Field(
        default="metric_query",
        description="Tool to use for aggregate query execution"
    )
```

### 5. Add to HistorySpec (if exists)

```python
class HistorySpec(SQLModel):
    """Specification for historical data query in a plan."""

    keywords: List[str]
    time_range: TimeRangeSpec
    limit: int = 100
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for history query execution"
    )
```

### 6. Add to ListSpec (if exists)

```python
class ListSpec(SQLModel):
    """Specification for list query in a plan."""

    entity_type: str  # e.g., "servers", "services"
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 50
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for list query execution"
    )
```

### 7. Add to GraphSpec (if exists)

```python
class GraphSpec(SQLModel):
    """Specification for graph analysis in a plan."""

    scope: str
    view: View  # View enum: COMPOSITION, DEPENDENCY, IMPACT, PATH
    depth: int = 2
    filters: Optional[Dict[str, Any]] = None
    tool_type: str = Field(
        default="graph_analysis",
        description="Tool to use for graph analysis execution"
    )
```

### 8. Add to CepSpec (if exists)

```python
class CepSpec(SQLModel):
    """Specification for CEP (Complex Event Processing) query."""

    pattern: str
    keywords: List[str]
    time_window: Optional[str] = None
    tool_type: str = Field(
        default="cep_query",
        description="Tool to use for CEP query execution"
    )
```

---

## Step-by-Step Implementation

### Step 1: Read and Understand Current Structure

```bash
# Read the plan_schema.py file to see all Spec classes
cat apps/api/app/modules/ops/services/ci/planner/plan_schema.py

# Count lines to understand file size
wc -l apps/api/app/modules/ops/services/ci/planner/plan_schema.py

# Look for all SQLModel class definitions
grep -n "^class.*Spec.*SQLModel" apps/api/app/modules/ops/services/ci/planner/plan_schema.py
```

### Step 2: Identify All Spec Classes

Expected output:
```
class PrimarySpec(SQLModel)
class SecondarySpec(SQLModel)
class MetricSpec(SQLModel)
class AggregateSpec(SQLModel)
class HistorySpec(SQLModel)
class ListSpec(SQLModel)
class GraphSpec(SQLModel)
class CepSpec(SQLModel)
class AutoSpec(SQLModel)
class AutoPathSpec(SQLModel)
class AutoGraphScopeSpec(SQLModel)
```

### Step 3: Prepare Edit Template

For each Spec class, add this field before the last line of the class:

```python
tool_type: str = Field(
    default="<appropriate_default>",
    description="Tool to use for this query execution"
)
```

**Default tool_type mapping**:
- `PrimarySpec` → `"ci_lookup"`
- `SecondarySpec` → `"ci_lookup"`
- `MetricSpec` → `"metric_query"`
- `AggregateSpec` → `"metric_query"`
- `HistorySpec` → `"ci_lookup"`
- `ListSpec` → `"ci_lookup"`
- `GraphSpec` → `"graph_analysis"`
- `CepSpec` → `"cep_query"`
- `AutoSpec` → `"ci_lookup"` (default, overridable)
- `AutoPathSpec` → `"graph_analysis"`
- `AutoGraphScopeSpec` → `"graph_analysis"`

### Step 4: Make Changes

Use Edit tool for each Spec class. Example pattern:

**For PrimarySpec**:
```python
# BEFORE
class PrimarySpec(SQLModel):
    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10

# AFTER
class PrimarySpec(SQLModel):
    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    tool_type: str = Field(
        default="ci_lookup",
        description="Tool to use for primary query execution"
    )
```

---

## Code Review Checklist

After making changes, verify:

### ✅ Syntax & Structure
- [ ] All Spec classes compile without errors
- [ ] All default tool_type values are strings
- [ ] Field descriptions are clear and concise
- [ ] Imports are still valid (sqlmodel.Field still used)

### ✅ Defaults Are Sensible
- [ ] `PrimarySpec` defaults to `"ci_lookup"` (infrastructure lookup)
- [ ] `MetricSpec` defaults to `"metric_query"` (metric tool)
- [ ] `GraphSpec` defaults to `"graph_analysis"` (graph tool)
- [ ] Others default to their most common tool

### ✅ Consistency
- [ ] All tool_type fields use same pattern
- [ ] All have default values (no Optional)
- [ ] All have descriptions
- [ ] All use Field() with explicit parameters

### ✅ Backward Compatibility
- [ ] All fields have defaults (no breaking changes)
- [ ] Existing code that creates Plans still works
- [ ] JSON parsing still works (defaults apply)

### ✅ Documentation
- [ ] Class docstrings mention tool_type
- [ ] Field descriptions are accurate
- [ ] Example Plan JSON shows tool_type usage

---

## Example Plan JSON After Changes

### Example 1: Simple Query Plan

**Before**:
```json
{
  "intent": "QueryMetrics",
  "mode": "complete",
  "primary": {
    "keywords": ["cpu"],
    "filters": {"environment": "prod"},
    "limit": 10
  }
}
```

**After**:
```json
{
  "intent": "QueryMetrics",
  "mode": "complete",
  "primary": {
    "keywords": ["cpu"],
    "filters": {"environment": "prod"},
    "limit": 10,
    "tool_type": "ci_lookup"
  }
}
```

### Example 2: Complex Query Plan

**Before**:
```json
{
  "intent": "QueryMetrics",
  "mode": "complete",
  "primary": {
    "keywords": ["server"],
    "filters": {"status": "running"},
    "limit": 5
  },
  "metric": {
    "metric_name": "cpu_usage",
    "agg": "avg",
    "time_range": {
      "start": "2024-01-20T00:00:00Z",
      "end": "2024-01-29T00:00:00Z"
    },
    "scope": "server"
  }
}
```

**After**:
```json
{
  "intent": "QueryMetrics",
  "mode": "complete",
  "primary": {
    "keywords": ["server"],
    "filters": {"status": "running"},
    "limit": 5,
    "tool_type": "ci_lookup"
  },
  "metric": {
    "metric_name": "cpu_usage",
    "agg": "avg",
    "time_range": {
      "start": "2024-01-20T00:00:00Z",
      "end": "2024-01-29T00:00:00Z"
    },
    "scope": "server",
    "tool_type": "metric_query"
  }
}
```

---

## Testing Phase 1

### Unit Tests to Write/Update

**File**: `apps/api/tests/test_plan_schema.py`

```python
import pytest
from app.modules.ops.services.ci.planner.plan_schema import (
    PrimarySpec, SecondarySpec, MetricSpec, AggregateSpec,
    HistorySpec, ListSpec, GraphSpec, CepSpec,
    AutoSpec, AutoPathSpec, AutoGraphScopeSpec,
    Plan, Intent, PlanMode
)

class TestSpecToolType:
    """Test tool_type field in all Spec classes."""

    def test_primary_spec_has_tool_type_field(self):
        """PrimarySpec should have tool_type field with default."""
        spec = PrimarySpec(keywords=["test"])
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "ci_lookup"

    def test_primary_spec_tool_type_override(self):
        """PrimarySpec tool_type should be overridable."""
        spec = PrimarySpec(
            keywords=["test"],
            tool_type="custom_tool"
        )
        assert spec.tool_type == "custom_tool"

    def test_metric_spec_has_tool_type_field(self):
        """MetricSpec should have tool_type field with default."""
        spec = MetricSpec(
            metric_name="cpu_usage",
            agg="avg",
            time_range=TimeRangeSpec(...)
        )
        assert hasattr(spec, "tool_type")
        assert spec.tool_type == "metric_query"

    def test_metric_spec_tool_type_override(self):
        """MetricSpec tool_type should be overridable."""
        spec = MetricSpec(
            metric_name="cpu_usage",
            agg="avg",
            time_range=TimeRangeSpec(...),
            tool_type="custom_metric_tool"
        )
        assert spec.tool_type == "custom_metric_tool"

    def test_aggregate_spec_has_tool_type_field(self):
        """AggregateSpec should have tool_type field."""
        spec = AggregateSpec(metrics=["cpu", "memory"])
        assert spec.tool_type == "metric_query"

    def test_history_spec_has_tool_type_field(self):
        """HistorySpec should have tool_type field."""
        spec = HistorySpec(
            keywords=["test"],
            time_range=TimeRangeSpec(...)
        )
        assert spec.tool_type == "ci_lookup"

    def test_list_spec_has_tool_type_field(self):
        """ListSpec should have tool_type field."""
        spec = ListSpec(entity_type="servers")
        assert spec.tool_type == "ci_lookup"

    def test_graph_spec_has_tool_type_field(self):
        """GraphSpec should have tool_type field."""
        spec = GraphSpec(
            scope="server-1",
            view=View.COMPOSITION
        )
        assert spec.tool_type == "graph_analysis"

    def test_plan_with_tool_types(self):
        """Plan with multiple specs should preserve tool_type."""
        plan = Plan(
            intent=Intent.QUERY,
            mode=PlanMode.COMPLETE,
            primary=PrimarySpec(keywords=["test"]),
            metric=MetricSpec(
                metric_name="cpu",
                agg="avg",
                time_range=TimeRangeSpec(...)
            )
        )
        assert plan.primary.tool_type == "ci_lookup"
        assert plan.metric.tool_type == "metric_query"

    def test_plan_json_includes_tool_type(self):
        """Plan JSON serialization should include tool_type."""
        plan = Plan(
            intent=Intent.QUERY,
            mode=PlanMode.COMPLETE,
            primary=PrimarySpec(keywords=["test"])
        )
        plan_dict = plan.model_dump()
        assert "tool_type" in plan_dict["primary"]
        assert plan_dict["primary"]["tool_type"] == "ci_lookup"

    def test_plan_json_parse_with_tool_type(self):
        """Plan should parse JSON with tool_type."""
        plan_json = {
            "intent": "QUERY",
            "mode": "COMPLETE",
            "primary": {
                "keywords": ["test"],
                "filters": {},
                "limit": 10,
                "tool_type": "custom_ci_lookup"
            }
        }
        plan = Plan(**plan_json)
        assert plan.primary.tool_type == "custom_ci_lookup"

    def test_plan_json_parse_without_tool_type(self):
        """Plan should use default tool_type if not in JSON."""
        plan_json = {
            "intent": "QUERY",
            "mode": "COMPLETE",
            "primary": {
                "keywords": ["test"],
                "filters": {},
                "limit": 10
            }
        }
        plan = Plan(**plan_json)
        assert plan.primary.tool_type == "ci_lookup"  # Default

    def test_all_spec_types_have_tool_type(self):
        """All Spec types should have tool_type field."""
        specs = [
            PrimarySpec(keywords=["test"]),
            SecondarySpec(keywords=["test"]),
            MetricSpec(metric_name="cpu", agg="avg", time_range=...),
            AggregateSpec(metrics=["cpu"]),
            # Add others as needed
        ]
        for spec in specs:
            assert hasattr(spec, "tool_type"), f"{spec.__class__.__name__} missing tool_type"
            assert isinstance(spec.tool_type, str), f"{spec.__class__.__name__} tool_type not string"
            assert len(spec.tool_type) > 0, f"{spec.__class__.__name__} tool_type empty"
```

### Integration Tests

```python
class TestPlanWithToolType:
    """Integration tests for Plan with tool_type."""

    def test_plan_serialization_round_trip(self):
        """Plan should serialize/deserialize preserving tool_type."""
        original = Plan(
            intent=Intent.QUERY,
            primary=PrimarySpec(
                keywords=["server"],
                tool_type="custom_lookup"
            ),
            metric=MetricSpec(
                metric_name="cpu",
                tool_type="custom_metric"
            )
        )

        # Serialize
        serialized = original.model_dump_json()

        # Deserialize
        deserialized = Plan.model_validate_json(serialized)

        assert deserialized.primary.tool_type == "custom_lookup"
        assert deserialized.metric.tool_type == "custom_metric"

    def test_plan_backward_compatibility(self):
        """Old Plan JSON without tool_type should still work."""
        old_plan_json = '''
        {
            "intent": "QUERY",
            "mode": "COMPLETE",
            "primary": {
                "keywords": ["server"],
                "filters": {}
            }
        }
        '''
        plan = Plan.model_validate_json(old_plan_json)
        assert plan.primary.tool_type == "ci_lookup"  # Default value used
```

---

## Expected Test Results

All tests should **PASS**:
- ✅ All Spec classes have tool_type field
- ✅ Default values are correct
- ✅ Overrides work
- ✅ JSON serialization works
- ✅ JSON deserialization works
- ✅ Backward compatibility maintained

---

## Validation Checklist Before Committing

- [ ] Run all tests: `pytest apps/api/tests/test_plan_schema.py -v`
- [ ] All tests pass
- [ ] No type errors: `mypy apps/api/app/modules/ops/services/ci/planner/plan_schema.py`
- [ ] Code style: `black apps/api/app/modules/ops/services/ci/planner/plan_schema.py`
- [ ] Linting: `flake8 apps/api/app/modules/ops/services/ci/planner/plan_schema.py`
- [ ] Manual check: Read modified file to ensure quality
- [ ] Documentation: Update any docstrings/comments

---

## Commit Message

Once Phase 1 is complete, commit with:

```
feat: Add tool_type field to Plan specifications for dynamic tool selection

- Add tool_type field to all Spec classes (Primary, Secondary, Metric, etc.)
- Set sensible defaults (ci_lookup, metric_query, graph_analysis)
- Maintain backward compatibility with defaults
- Update tests to verify tool_type field works correctly

This enables LLM-based tool selection in Execute stage instead of hardcoded values.

Related: LLM-based tool selection implementation
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

---

## Next Steps After Phase 1

Once this phase is complete:
1. Verify all existing tests still pass (backward compatibility)
2. Move to Phase 2: Tool Registry enhancement
3. Keep this commit separate so it can be reviewed independently

**Expected time**: 2-4 hours including testing

**Difficulty**: Low (straightforward field additions)

**Risk**: Very Low (backward compatible with defaults)
