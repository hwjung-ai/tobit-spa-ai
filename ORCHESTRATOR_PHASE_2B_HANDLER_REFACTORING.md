# Orchestrator Phase 2B: Handler Refactoring Guide

**Status**: Ready for Implementation
**Date**: 2026-02-10
**Phase**: Phase 2B of Orchestrator Tool Asset Refactoring

---

## 🎯 Objective

Refactor orchestrator handlers to explicitly use Tool Assets instead of direct database operations.

## 📋 Handler Refactoring Tasks

### Task 1: _metric_blocks_async() Refactoring

**Location**: `/apps/api/app/modules/ops/services/ci/orchestrator/runner.py:3300-3435`

**Current Implementation** (Problem):
```python
async def _metric_blocks_async(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    ci_id = detail.get("ci_id")

    # ❌ Internal orchestration without explicit Tool Asset usage
    if self.plan.metric:
        metric_name = self.plan.metric.name
        agg = self.plan.metric.agg or "AVG"
        time_range = self.plan.metric.time_range

        # Direct database operation (unclear to LLM)
        result = await self._metric_series_table_async(
            ci_id, metric_name, time_range, limit
        )
```

**Refactored Implementation** (Solution):
```python
async def _metric_blocks_async(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    ci_id = detail.get("ci_id")
    ci_code = detail.get("ci_code")

    blocks = []

    # ✅ Explicit Tool Asset usage: metric_query
    if self.plan.metric:
        metric_name = self.plan.metric.name or "cpu_usage"
        time_range = self.plan.metric.time_range or {"days": 7}

        # Calculate time boundaries
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(**time_range)

        # Execute metric_query Tool Asset
        result = await self._execute_tool_asset_async(
            "metric_query",
            {
                "tenant_id": self.tenant_id,
                "ci_code": ci_code,
                "metric_name": metric_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": 100,
            },
        )

        if result.get("success") and result.get("data"):
            # Convert Tool Asset output to metric blocks
            blocks.extend(self._build_metric_blocks_from_data(
                result["data"],
                metric_name,
            ))
        else:
            self.logger.warning(
                f"metric_query Tool Asset failed: {result.get('error')}"
            )

    # ✅ Explicit Tool Asset usage: ci_aggregation for stats
    if self.plan.metric and self.plan.metric.scope == "comparison":
        agg_result = await self._execute_tool_asset_async(
            "ci_aggregation",
            {
                "tenant_id": self.tenant_id,
            },
        )

        if agg_result.get("success"):
            blocks.extend(self._build_aggregation_blocks(agg_result["data"]))

    return blocks
```

**Changes**:
1. Replace `_metric_series_table_async()` with `_execute_tool_asset_async("metric_query", ...)`
2. Use explicit Tool Asset call with clear parameters
3. Handle Tool Asset response format
4. Track tool usage through self.tool_calls (automatic)

---

### Task 2: _history_blocks_async() Refactoring

**Location**: `/apps/api/app/modules/ops/services/ci/orchestrator/runner.py:3705-3778`

**Current Implementation** (Problem):
```python
async def _history_blocks_async(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    ci_id = detail.get("ci_id")

    # ❌ Direct service call without explicit Tool Asset
    if self.plan.history.enabled:
        # Internal data retrieval (unclear)
        blocks = await self._ci_history_blocks_async(detail)
```

**Refactored Implementation** (Solution):
```python
async def _history_blocks_async(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    ci_id = detail.get("ci_id")
    ci_code = detail.get("ci_code")

    blocks = []

    # ✅ Explicit Tool Asset usage: work_history_query
    if self.plan.history.enabled:
        time_range = self.plan.history.time_range or {"days": 30}

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(**time_range)

        # Query work history via Tool Asset
        result = await self._execute_tool_asset_async(
            "work_history_query",
            {
                "tenant_id": self.tenant_id,
                "ci_code": ci_code,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": 50,
            },
        )

        if result.get("success") and result.get("data"):
            blocks.extend(self._build_history_blocks_from_data(
                result["data"],
                "work",
            ))
        else:
            self.logger.warning(
                f"work_history_query Tool Asset failed: {result.get('error')}"
            )

    # ✅ Explicit Tool Asset usage: history_combined_union
    if self.plan.history.enabled and self.plan.history.include_maintenance:
        combined_result = await self._execute_tool_asset_async(
            "history_combined_union",
            {
                "tenant_id": self.tenant_id,
                "ci_id": ci_id,
                "start_time": start_time.isoformat() if 'start_time' in locals() else None,
                "end_time": end_time.isoformat() if 'end_time' in locals() else None,
                "limit": 100,
            },
        )

        if combined_result.get("success") and combined_result.get("data"):
            blocks.extend(self._build_combined_history_blocks(
                combined_result["data"]
            ))

    return blocks
```

**Changes**:
1. Replace `_ci_history_blocks_async()` with `_execute_tool_asset_async("work_history_query", ...)`
2. Add support for `history_combined_union` Tool Asset
3. Use explicit Tool Asset parameters matching schema
4. Handle both work and maintenance history

---

### Task 3: _build_graph_blocks_async() Refactoring

**Location**: `/apps/api/app/modules/ops/services/ci/orchestrator/runner.py:1756-1850`

**Current Implementation** (Problem):
```python
async def _build_graph_blocks_async(
    self, detail: Dict[str, Any], graph_view: View
) -> tuple[List[Block], Dict[str, Any] | None]:
    # ❌ No explicit Tool Asset for relationship queries
    # Uses internal graph expansion without clear Tool tracking
    if self._graph_expand_requested():
        payload = await self._graph_expand_async(...)
```

**Refactored Implementation** (Solution):
```python
async def _build_graph_blocks_async(
    self, detail: Dict[str, Any], graph_view: View
) -> tuple[List[Block], Dict[str, Any] | None]:
    ci_code = detail.get("ci_code")
    ci_id = detail.get("ci_id")

    # ✅ Explicit Tool Asset usage: ci_graph_query
    if self._graph_expand_requested():
        # Determine relationship types based on view
        relationship_types = self._map_view_to_relationship_types(graph_view)

        # Execute ci_graph_query Tool Asset
        graph_result = await self._execute_tool_asset_async(
            "ci_graph_query",
            {
                "tenant_id": self.tenant_id,
                "ci_code": ci_code,
                "ci_id": ci_id,
                "relationship_types": relationship_types,
                "limit": 500,
            },
        )

        if graph_result.get("success") and graph_result.get("data"):
            # Convert Tool Asset output to graph visualization
            payload = self._build_graph_payload_from_tool_data(
                graph_result["data"],
                detail,
                graph_view,
            )
            blocks = [graph_block(payload=payload)]
            return blocks, payload
        else:
            self.logger.warning(
                f"ci_graph_query Tool Asset failed: {graph_result.get('error')}"
            )
            # Fallback to mock graph
            payload = self._mock_graph()
            blocks = [graph_block(payload=payload)]
            return blocks, payload

    return [], None

def _map_view_to_relationship_types(self, view: View) -> list[str]:
    """Map graph view type to relationship types for query"""
    mapping = {
        View.COMPOSITION: ["composition", "part_of"],
        View.DEPENDENCY: ["depends_on", "depends_on_reverse"],
        View.IMPACT: ["impacts", "impacts_reverse"],
        View.NEIGHBORS: ["composition", "depends_on", "impacts"],
        View.PATH: ["depends_on", "depends_on_reverse"],
    }
    return mapping.get(view, ["composition", "depends_on", "impacts"])
```

**Changes**:
1. Replace `_graph_expand_async()` with `_execute_tool_asset_async("ci_graph_query", ...)`
2. Add mapping from graph view to relationship types
3. Convert Tool Asset result to graph payload format
4. Maintain mock fallback for UI consistency

---

## 🔧 Helper Methods to Create

### Helper 1: _build_metric_blocks_from_data()

```python
def _build_metric_blocks_from_data(
    self,
    data: Dict[str, Any],
    metric_name: str,
) -> List[Block]:
    """Convert metric_query Tool Asset output to display blocks"""
    rows = data.get("rows", [])

    if not rows:
        return []

    blocks = []

    # Create time series chart if we have multiple data points
    if len(rows) > 1:
        times = [r["time"] for r in rows]
        values = [r["value"] for r in rows]

        blocks.append(chart_block(
            type="timeseries",
            title=f"{metric_name} Trend",
            data={
                "time": times,
                "value": values,
                "unit": rows[0].get("unit", ""),
            },
        ))

    # Create summary table
    blocks.append(table_block(
        title=f"{metric_name} Details",
        columns=["Time", "Value", "Unit"],
        rows=[
            [r["time"], r["value"], r.get("unit", "")]
            for r in rows
        ],
    ))

    return blocks
```

### Helper 2: _build_history_blocks_from_data()

```python
def _build_history_blocks_from_data(
    self,
    data: Dict[str, Any],
    history_type: str,
) -> List[Block]:
    """Convert work/maintenance history Tool Asset output to display blocks"""
    rows = data.get("rows", [])

    if not rows:
        return []

    blocks = []

    # Create summary text
    blocks.append(text_block(
        title=f"{history_type.capitalize()} History",
        content=f"Found {len(rows)} {history_type} records",
    ))

    # Create detailed table
    blocks.append(table_block(
        title=f"{history_type.capitalize()} Details",
        columns=["Type", "Summary", "Start Time", "Duration (min)", "Result"],
        rows=[
            [
                r.get("work_type", r.get("maint_type", "")),
                r.get("summary", "")[:50],
                r.get("start_time", ""),
                r.get("duration_min", 0),
                r.get("result", ""),
            ]
            for r in rows
        ],
    ))

    return blocks
```

### Helper 3: _build_graph_payload_from_tool_data()

```python
def _build_graph_payload_from_tool_data(
    self,
    data: Dict[str, Any],
    detail: Dict[str, Any],
    view: View,
) -> Dict[str, Any]:
    """Convert ci_graph_query Tool Asset output to graph visualization payload"""
    rows = data.get("rows", [])

    # Build nodes set
    nodes_set = {detail["ci_id"]}  # Start with source CI
    edges = []

    for row in rows:
        from_id = row["from_ci_id"]
        to_id = row["to_ci_id"]

        nodes_set.add(from_id)
        nodes_set.add(to_id)

        edges.append({
            "from": from_id,
            "to": to_id,
            "type": row["relationship_type"],
            "strength": row.get("strength", 1.0),
        })

    # Build nodes
    nodes = [
        {
            "id": node_id,
            "label": detail["ci_name"] if node_id == detail["ci_id"]
                    else node_id,
        }
        for node_id in nodes_set
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "depth": 1,
            "view": view.value,
        },
        "ids": [detail["ci_code"]],
    }
```

---

## 📊 Refactoring Checklist

- [ ] Task 1: _metric_blocks_async() refactoring
- [ ] Task 2: _history_blocks_async() refactoring
- [ ] Task 3: _build_graph_blocks_async() refactoring
- [ ] Create helper methods (3 helpers)
- [ ] Update imports if needed
- [ ] Run existing tests to verify no regression
- [ ] Create integration tests for Tool Asset usage
- [ ] Verify tool_calls tracking works correctly
- [ ] Remove old direct database methods if unused
- [ ] Document all Tool Asset → Block conversion patterns

---

## 🧪 Testing Strategy

### Unit Tests
```python
def test_metric_blocks_uses_metric_query_tool():
    """Verify _metric_blocks_async uses metric_query Tool Asset"""
    # Mock orchestrator with plan
    # Verify _execute_tool_asset_async called with "metric_query"
    # Verify tool_calls list contains the call

def test_history_blocks_uses_work_history_query_tool():
    """Verify _history_blocks_async uses work_history_query Tool Asset"""
    # Similar verification pattern

def test_graph_blocks_uses_ci_graph_query_tool():
    """Verify _build_graph_blocks_async uses ci_graph_query Tool Asset"""
    # Similar verification pattern
```

### Integration Tests
```python
async def test_end_to_end_metric_query():
    """Full flow: question → orchestrator → metric_query Tool → blocks"""
    # Create runner with metric mode plan
    # Execute
    # Verify blocks are built from Tool Asset data
    # Verify tool_calls tracked correctly
```

---

## 📈 Expected Outcomes

**Before Refactoring**:
- Handlers perform internal database operations
- Tool Assets defined but not used
- Data sources unclear to LLM
- Difficult to extend with new data operations

**After Refactoring**:
- ✅ All handlers use explicit Tool Assets via `_execute_tool_asset_async()`
- ✅ Tool Assets centrally managed and discoverable
- ✅ LLM can see and select available operations
- ✅ Clear data contracts with input/output schemas
- ✅ Easy to add new Tool Assets without handler modification

---

## 🚀 Implementation Timeline

- **Phase 1** (Done): Create 5 new Tool Assets with SQL files ✅
- **Phase 2A** (Done): Add `_execute_tool_asset_async()` method ✅
- **Phase 2B** (Next): Refactor handlers to use Tool Assets (3-4 hours)
- **Phase 3**: Remove old internal methods (1 hour)
- **Phase 4**: Testing and validation (2-3 hours)
- **Phase 5**: Documentation and knowledge transfer (1 hour)

---

## 💡 Key Principles

1. **Explicit over Implicit**: Every data operation is a clear Tool Asset call
2. **Trackable**: All tool usage recorded in tool_calls for visibility
3. **Extensible**: New data operations = new Tool Asset + registration
4. **Safe**: All queries parameterized, no SQL Injection vectors
5. **Clear Contracts**: Input/output schemas define exact expectations

---

This document is a complete guide for Phase 2B handler refactoring. Follow the patterns and helpers provided to ensure consistency across the orchestrator.
