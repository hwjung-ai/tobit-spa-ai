# Phase 3 Design Plan: Async/Await Optimization

## Overview

Phase 3 removes the `asyncio.run()` overhead by converting the ToolExecutor to native async/await. This enables full async request handling with potential 5-10% performance improvement. All external APIs remain unchanged through async-to-sync wrappers.

## Current State (End of Phase 2D)

```
Primary Methods (_ci_search, etc.)
  ↓
Try-Catch Block
  ├─ Success: Call _ci_search_via_registry()
  └─ Error: Fall back to ci_tools.ci_search()
    ↓
_ci_search_via_registry() [SYNC]
  ↓
self._execute_tool(ToolType.CI, "search", ...) [SYNC]
  ↓
self._tool_executor.execute() [SYNC wrapper]
  ↓
asyncio.run(tool.safe_execute()) [ASYNC → SYNC conversion - OVERHEAD]
  ↓
BaseTool.safe_execute() [ASYNC]
  ↓
Tool.execute() [ASYNC - actual implementation]
```

## Phase 3 Target State

```
Primary Methods (_ci_search, etc.)
  ↓
Try-Catch Block
  ├─ Success: Call _ci_search_via_registry_async()
  └─ Error: Fall back to ci_tools.ci_search()
    ↓
_ci_search_via_registry_async() [ASYNC]
  ↓
await self._execute_tool_async(ToolType.CI, "search", ...) [ASYNC]
  ↓
await self._tool_executor.execute_async() [ASYNC]
  ↓
await tool.safe_execute() [ASYNC - NO conversion overhead]
  ↓
BaseTool.safe_execute() [ASYNC]
  ↓
Tool.execute() [ASYNC - actual implementation]
```

## Phase 3 Implementation Steps

### Step 3.1: Create Async Helper Methods

**File**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**Location**: After `_execute_tool()` method (around line 2770)

**What to Add**:

```python
def _execute_tool_async(
    self,
    tool_type: ToolType,
    operation: str,
    **params
) -> Coroutine[Any, Any, Dict[str, Any]]:
    """
    Execute a tool asynchronously through ToolRegistry.
    Returns a coroutine that must be awaited.

    Args:
        tool_type: The type of tool (CI, METRIC, GRAPH, HISTORY, CEP)
        operation: The operation name within the tool
        **params: Parameters to pass to the tool

    Returns:
        Coroutine that resolves to tool result dict
    """
    context = ToolContext(
        tenant_id=self.tenant_id,
        request_id=get_request_context().get("request_id"),
        trace_id=get_request_context().get("trace_id"),
    )
    params_with_op = {"operation": operation, **params}

    # Return coroutine directly - caller will await it
    return self._tool_executor.execute_async(
        tool_type,
        context,
        params_with_op
    )
```

### Step 3.2: Modify ToolExecutor for Async Support

**File**: `apps/api/app/modules/ops/services/ci/tools/executor.py`

**What to Add** (after existing `execute()` method):

```python
async def execute_async(
    self,
    tool_type: ToolType,
    context: ToolContext,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a tool asynchronously without asyncio.run() overhead.

    Args:
        tool_type: Type of tool to execute
        context: Request context (tenant, user, trace IDs)
        params: Tool parameters including operation name

    Returns:
        Tool result dictionary

    Raises:
        ValueError: If tool not found or execution fails
    """
    operation = params.get("operation")
    if not operation:
        raise ValueError("operation parameter required")

    # Get tool from registry
    tool = self._registry.get_tool(tool_type, operation)
    if not tool:
        raise ValueError(f"Tool not found: {tool_type.value}/{operation}")

    # Execute directly without asyncio.run() wrapper
    result = await tool.safe_execute(context, params)

    if not result.success:
        raise ValueError(result.error or "Unknown tool error")

    return result.data
```

### Step 3.3: Create Async Via-Registry Methods

**File**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**Location**: After existing `_*_via_registry()` methods (around line 3000)

**Pattern for each method**:

```python
async def _ci_search_via_registry_async(
    self,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = None,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Execute CI search asynchronously through ToolRegistry.
    Returns same format as primary _ci_search.
    """
    result = await self._execute_tool_async(
        ToolType.CI,
        "search",
        keywords=keywords,
        filters=filters,
        limit=limit,
        sort=sort,
    )
    return [r.dict() if hasattr(r, "dict") else r for r in result.records]
```

**Methods to create** (11 total):
- `_ci_search_via_registry_async`
- `_ci_get_via_registry_async`
- `_ci_get_by_code_via_registry_async`
- `_ci_aggregate_via_registry_async`
- `_ci_list_preview_via_registry_async`
- `_metric_aggregate_via_registry_async`
- `_metric_series_table_via_registry_async`
- `_graph_expand_via_registry_async`
- `_graph_path_via_registry_async`
- `_history_recent_via_registry_async`
- `_cep_simulate_via_registry_async`

### Step 3.4: Update Primary Methods to Use Async Helpers

**File**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**Strategy**: Update primary methods to be async and use async helpers

**Example - _ci_search()**:

```python
async def _ci_search(
    self,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = None,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> List[Dict[str, Any]]:
    keywords_tuple = tuple(keywords or ())
    filters_tuple = tuple(filters or ())
    input_params = {
        "keywords": list(keywords_tuple),
        "filter_count": len(filters_tuple),
        "limit": limit,
        "sort": sort,
    }
    with self._tool_context(
        "ci.search",
        input_params=input_params,
        keyword_count=len(keywords_tuple),
        filter_count=len(filters_tuple),
        limit=limit,
        sort_column=sort[0] if sort else None,
    ) as meta:
        # ASYNC REGISTRY PATH (Phase 3)
        try:
            result_data = await self._ci_search_via_registry_async(
                keywords=keywords_tuple,
                filters=filters_tuple,
                limit=limit,
                sort=sort,
            )
            meta["row_count"] = len(result_data)
            result_records = result_data
        except Exception as e:
            self.logger.warning(f"CI search via registry failed, falling back: {e}")
            # Fallback to direct call (sync)
            result = ci_tools.ci_search(
                self.tenant_id,
                keywords=keywords_tuple,
                filters=filters_tuple,
                limit=limit,
                sort=sort,
            )
            meta["row_count"] = len(result.records)
            meta["fallback"] = True
            result_records = [r.dict() for r in result.records]

    if not result_records and not self._ci_search_recovery:
        recovered = self._recover_ci_identifiers()
        if recovered:
            self._ci_search_recovery = True
            self.logger.info("ci.runner.ci_search_recovery", extra={"recovery_keywords": recovered})
            self.plan = self.plan.copy(
                update={"primary": self.plan.primary.copy(update={"keywords": list(recovered)})}
            )
            return await self._ci_search(keywords=recovered, filters=filters, limit=limit, sort=sort)
    return result_records
```

**All 11 primary methods to update**:
- `_ci_search` → add `async`, use `await _ci_search_via_registry_async()`
- `_ci_get` → add `async`, use `await _ci_get_via_registry_async()`
- `_ci_get_by_code` → add `async`, use `await _ci_get_by_code_via_registry_async()`
- `_ci_aggregate` → add `async`, use `await _ci_aggregate_via_registry_async()`
- `_ci_list_preview` → add `async`, use `await _ci_list_preview_via_registry_async()`
- `_metric_aggregate` → add `async`, use `await _metric_aggregate_via_registry_async()`
- `_metric_series_table` → add `async`, use `await _metric_series_table_via_registry_async()`
- `_graph_expand` → add `async`, use `await _graph_expand_via_registry_async()`
- `_graph_path` → add `async`, use `await _graph_path_via_registry_async()`
- `_history_recent` → add `async`, use `await _history_recent_via_registry_async()`
- `_cep_simulate` → add `async`, use `await _cep_simulate_via_registry_async()`

### Step 3.5: Create Sync Wrappers for Backward Compatibility

**File**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**Location**: At the end of the class (around line 3100)

**Purpose**: Maintain backward compatibility with callers that expect sync methods

```python
def _ci_search_sync(
    self,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = None,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for _ci_search (backward compatibility).
    Internally uses async implementation with asyncio.run().
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If already in async context, use current loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return loop.run_in_executor(
                pool,
                asyncio.run,
                self._ci_search(keywords, filters, limit, sort)
            )
    else:
        # Normal case: run async function synchronously
        return asyncio.run(self._ci_search(keywords, filters, limit, sort))
```

**Alternative simpler approach** (recommended):

```python
def _ci_search_sync(
    self,
    keywords: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    limit: int | None = None,
    sort: tuple[str, Literal["ASC", "DESC"]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for _ci_search (backward compatibility).
    """
    return asyncio.run(self._ci_search(keywords, filters, limit, sort))
```

**All 11 sync wrappers needed**:
- `_ci_search_sync`
- `_ci_get_sync`
- `_ci_get_by_code_sync`
- `_ci_aggregate_sync`
- `_ci_list_preview_sync`
- `_metric_aggregate_sync`
- `_metric_series_table_sync`
- `_graph_expand_sync`
- `_graph_path_sync`
- `_history_recent_sync`
- `_cep_simulate_sync`

### Step 3.6: Update Method Callers Within Runner

**File**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**Strategy**: Update internal calls to async methods

**Calls to update** (~100+ occurrences):
- `self._ci_search(...)` → `await self._ci_search(...)`
- `self._ci_get(...)` → `await self._ci_get(...)`
- `self._metric_aggregate(...)` → `await self._metric_aggregate(...)`
- All other tool method calls → add `await`

**Methods that call these to make async**:
- `run()` → `async def run()`
- `_run_primary_search()` → `async def _run_primary_search()`
- `_run_secondary_operations()` → `async def _run_secondary_operations()`
- `_metric_operations()` → `async def _metric_operations()`
- `_graph_operations()` → `async def _graph_operations()`
- `_history_operations()` → `async def _history_operations()`
- `_cep_operations()` → `async def _cep_operations()`
- And all other orchestration methods

### Step 3.7: Update Entry Points

**File**: `apps/api/app/modules/ops/services/ci/orchestrator/runner.py`

**Strategy**: Provide sync entry points that wrap async methods

```python
def run_sync(self) -> RunResult:
    """
    Synchronous entry point for backward compatibility.
    """
    return asyncio.run(self.run())

def run_primary_search_sync(self) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for primary search (backward compatibility).
    """
    return asyncio.run(self._run_primary_search())
```

**Methods to wrap**:
- `run()` → provide `run_sync()` wrapper
- All public orchestration methods → provide `_sync()` variants

### Step 3.8: Update Callers (Outside Runner)

**Files to update**:
- `apps/api/app/modules/ops/services/ci/orchestrator/*.py`
- Any files that call `runner.run()` or other methods

**Strategy**:

Option A (Recommended - Gradual Migration):
- Keep `run()` as sync wrapper for now
- Mark as "will become async in Phase 3"
- Update callers gradually in Phase 3

Option B (Immediate Full Async):
- Make `run()` async immediately
- Update all callers to use `await runner.run()`
- Might require more changes in calling code

**Recommended approach**: Option A

```python
# runner.py
async def _run_async(self) -> RunResult:
    """Actual async implementation."""
    # ... async implementation ...

def run(self) -> RunResult:
    """
    Public sync entry point (backward compatibility).
    Uses async implementation internally.
    """
    return asyncio.run(self._run_async())
```

## Phase 3 File Changes Summary

### Modified Files

**apps/api/app/modules/ops/services/ci/tools/executor.py**
- Add `execute_async()` method (~20 lines)
- No changes to existing `execute()` method

**apps/api/app/modules/ops/services/ci/orchestrator/runner.py**
- Add `_execute_tool_async()` method (~15 lines)
- Add 11 `_*_via_registry_async()` async methods (~200 lines)
- Make 11 primary methods async, update calls (~300 lines)
- Add 11 `_*_sync()` wrapper methods (~80 lines)
- Update ~100+ internal method calls to use `await`
- Make key orchestration methods async (~200 lines)

**Total additions**: ~815 lines

### No Files to Delete

All existing sync implementations remain for:
- Fallback support
- Backward compatibility
- Direct tool calls

## Phase 3 Testing Strategy

### Unit Tests

```python
# Test async execution
async def test_ci_search_async():
    runner = CIOrchestratorRunner(...)
    results = await runner._ci_search(keywords=["service"])
    assert len(results) > 0

# Test sync wrapper
def test_ci_search_sync():
    runner = CIOrchestratorRunner(...)
    results = runner._ci_search_sync(keywords=["service"])
    assert len(results) > 0

# Test fallback with async
async def test_ci_search_fallback():
    runner = CIOrchestratorRunner(...)
    # Mock registry failure
    with patch.object(runner._tool_executor, 'execute_async', side_effect=Exception()):
        results = await runner._ci_search(keywords=["service"])
        assert len(results) > 0  # Falls back to direct call
```

### Integration Tests

```python
# Test full async flow
async def test_full_orchestration_async():
    runner = CIOrchestratorRunner(...)
    result = await runner.run()
    assert result.success

# Test sync wrapper end-to-end
def test_full_orchestration_sync():
    runner = CIOrchestratorRunner(...)
    result = runner.run()  # Uses sync wrapper
    assert result.success
```

### Performance Tests

```python
# Measure improvement
async def test_performance_async():
    import time
    runner = CIOrchestratorRunner(...)
    start = time.perf_counter()
    await runner._ci_search(keywords=["service"])
    async_time = time.perf_counter() - start

    # Should be ~5-10% faster than sync
    return async_time

def test_performance_sync():
    import time
    runner = CIOrchestratorRunner(...)
    start = time.perf_counter()
    runner._ci_search_sync(keywords=["service"])
    sync_time = time.perf_counter() - start
    return sync_time
```

## Phase 3 Validation Checklist

### Code Quality
- [ ] All 11 async via-registry methods implemented
- [ ] All 11 sync wrapper methods implemented
- [ ] Async methods properly use `await`
- [ ] No blocking calls in async methods
- [ ] Proper error handling in async context
- [ ] Docstrings updated to indicate async/sync

### Backward Compatibility
- [ ] All sync wrappers work correctly
- [ ] Existing callers still work (via sync wrappers)
- [ ] Direct tool imports still available for fallback
- [ ] No breaking changes to public APIs

### Performance
- [ ] Asyncio.run() overhead removed from registry path
- [ ] Performance improvement measured (~5-10%)
- [ ] No regression in fallback path
- [ ] Load testing passes

### Testing
- [ ] Unit tests for async methods pass
- [ ] Unit tests for sync wrappers pass
- [ ] Fallback tests pass
- [ ] Integration tests pass
- [ ] Performance benchmarks show improvement

### Documentation
- [ ] PHASE3_IMPLEMENTATION_SUMMARY.md created
- [ ] Docstrings updated for all async methods
- [ ] Comments explain async/sync pattern
- [ ] Architecture diagrams updated
- [ ] Performance impact documented

## Phase 3 Potential Issues & Solutions

### Issue 1: Event Loop Already Running

**Problem**: When calling async code from sync context where event loop is already running.

**Solution**:
```python
def _ensure_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - use nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
    except RuntimeError:
        # No event loop - create one
        asyncio.new_event_loop()
```

### Issue 2: Multiple asyncio.run() Calls

**Problem**: Multiple nested `asyncio.run()` calls fail in Python.

**Solution**: Use single event loop manager:
```python
class AsyncRunner:
    _loop = None

    @classmethod
    def get_loop(cls):
        if cls._loop is None or cls._loop.is_closed():
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
        return cls._loop

    @classmethod
    def run_async(cls, coro):
        loop = cls.get_loop()
        return loop.run_until_complete(coro)
```

### Issue 3: Context Variables in Async

**Problem**: Request context (tenant_id, user_id) might be lost in async context.

**Solution**: Capture context before async call:
```python
def _execute_tool_async(self, tool_type, operation, **params):
    # Capture context before going async
    context = ToolContext(
        tenant_id=self.tenant_id,  # Already captured
        request_id=get_request_context().get("request_id"),
        trace_id=get_request_context().get("trace_id"),
    )
    # Pass context explicitly
    return self._tool_executor.execute_async(tool_type, context, params)
```

### Issue 4: Distributed Tracing in Async

**Problem**: Tracing spans might not work correctly in async context.

**Solution**: Use async-aware tracing:
```python
async def _ci_search(self, ...):
    with self._tool_context(...) as meta:
        # _tool_context must support async
        # Or wrap span management differently
        try:
            result = await self._ci_search_via_registry_async(...)
        except Exception:
            result = ci_tools.ci_search(...)  # sync fallback
    return result
```

## Phase 3 Rollback Plan

### Rollback to Phase 2D

```bash
# Revert Phase 3 commit
git revert <Phase3 commit>

# System reverts to sync implementation with asyncio.run() overhead
# Zero functionality loss
# Performance returns to Phase 2D baseline
```

### Rollback to Phase 1 (if needed)

```bash
# Revert entire Phase 2
git revert <Phase3 commit>
git revert <Phase2D commit>
git revert <Phase2C commit>
git revert <Phase2B commit>
git revert <Phase2A commit>

# System returns to original direct tool call implementation
# Zero functionality loss
```

## Phase 3 Performance Impact

### Expected Improvements

| Operation | Phase 2D (Sync) | Phase 3 (Async) | Improvement |
|-----------|-----------------|-----------------|-------------|
| CI Search | ~15ms | ~13.5ms | ~10% |
| CI Get | ~8ms | ~7.2ms | ~10% |
| Metric Aggregate | ~12ms | ~10.8ms | ~10% |
| Graph Expand | ~20ms | ~18ms | ~10% |
| Full Orchestration | ~100ms | ~90ms | ~10% |

### Key Benefits

1. **Removed asyncio.run() overhead**: ~2ms per call
2. **Better concurrency**: Multiple operations can run in parallel
3. **Reduced thread context switching**: Fewer threads needed
4. **Scalability**: System can handle more concurrent requests

## Phase 3 Documentation

**Create**: `docs/PHASE3_IMPLEMENTATION_SUMMARY.md`
- Async/await migration details
- Performance improvements measured
- Backward compatibility guarantees
- Testing results
- Known issues and solutions

## Phase 3 Success Criteria

✅ **All criteria must be met**:

1. ✅ All 11 async via-registry methods implemented
2. ✅ All 11 sync wrapper methods implemented
3. ✅ Async method calls updated throughout runner
4. ✅ Performance improvement measured (~5-10%)
5. ✅ No functionality changes
6. ✅ 100% backward compatibility maintained
7. ✅ All tests pass (unit, integration, performance)
8. ✅ No breaking changes to external APIs
9. ✅ Documentation complete

## Phase 3 Commit Message Template

```
Phase 3: Async/Await Optimization - Remove asyncio.run() Overhead

Summary:
- Converted ToolExecutor to async/await infrastructure
- Implemented async via-registry methods (11 total)
- Added sync wrappers for backward compatibility
- Updated primary methods to use async paths
- Achieved ~5-10% performance improvement

Detailed Changes:

New Infrastructure:
✅ ToolExecutor.execute_async() - Native async tool execution
✅ _execute_tool_async() - Async helper method
✅ 11 async _*_via_registry_async() methods
✅ 11 sync _*_sync() wrapper methods

Updated Methods (async):
✅ _ci_search - async with await support
✅ _ci_get - async with await support
✅ _ci_get_by_code - async with await support
✅ _ci_aggregate - async with await support
✅ _ci_list_preview - async with await support
✅ _metric_aggregate - async with await support
✅ _metric_series_table - async with await support
✅ _graph_expand - async with await support
✅ _graph_path - async with await support
✅ _history_recent - async with await support
✅ _cep_simulate - async with await support

Performance:
✅ Removed asyncio.run() overhead (~2ms per call)
✅ Improved concurrency and parallelism
✅ Measured 5-10% overall improvement
✅ Better resource utilization

Backward Compatibility:
✅ 100% backward compatible via sync wrappers
✅ All existing callers continue to work
✅ No breaking changes to APIs
✅ Gradual migration path available

Testing:
✅ Unit tests for async methods pass
✅ Unit tests for sync wrappers pass
✅ Fallback mechanism tested
✅ Performance benchmarks confirm improvement
✅ Integration tests pass

Files Modified:
- apps/api/app/modules/ops/services/ci/tools/executor.py
  (Added execute_async() method)
- apps/api/app/modules/ops/services/ci/orchestrator/runner.py
  (Added async methods, sync wrappers, updated calls)

Documentation:
- docs/PHASE3_IMPLEMENTATION_SUMMARY.md (new)
  (Async migration details, performance metrics, testing results)

Next Steps:
- Phase 4: Advanced Features (caching, composition, etc.)

Status: Phase 3 Complete ✅ - Performance Optimized
```

---

## Summary

Phase 3 is a focused optimization that:

✅ **Removes asyncio.run() overhead** - Direct async execution
✅ **Maintains backward compatibility** - Sync wrappers for all methods
✅ **Improves performance** - ~5-10% improvement expected
✅ **Enables future optimization** - Foundation for parallel execution
✅ **Zero breaking changes** - All external APIs unchanged

The phase involves:
- 1 new async method in ToolExecutor
- 1 new async helper in Runner
- 11 new async via-registry methods
- 11 new sync wrapper methods
- ~100+ call sites updated to use `await`
- ~815 lines of code additions
- Full backward compatibility maintained

Ready for Phase 4 after completion.
