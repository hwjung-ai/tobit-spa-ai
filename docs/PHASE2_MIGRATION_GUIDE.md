# Phase 2 Migration Guide: Orchestrator Generalization

## Overview

Phase 2 focuses on migrating the CIOrchestratorRunner from hard-coded tool imports to dynamic tool invocation through the ToolRegistry. This enables the orchestrator to work with any registered tool without modification.

## Architecture Change

### Before (Current - Hard-coded imports)
```python
from app.modules.ops.services.ci.tools import ci as ci_tools
from app.modules.ops.services.ci.tools import metric as metric_tools

class CIOrchestratorRunner:
    def _ci_search(self, keywords, filters, limit, sort):
        result = ci_tools.ci_search(self.tenant_id, keywords, filters, limit, sort)
        return [r.dict() for r in result.records]
```

### After (New - ToolRegistry-based)
```python
from app.modules.ops.services.ci.tools import ToolContext, ToolType, get_tool_executor

class CIOrchestratorRunner:
    def __init__(self, ...):
        self._tool_executor = get_tool_executor()

    def _ci_search(self, keywords, filters, limit, sort):
        context = ToolContext(tenant_id=self.tenant_id)
        params = {
            "operation": "search",
            "keywords": keywords,
            "filters": filters,
            "limit": limit,
            "sort": sort,
        }
        result = self._tool_executor.execute(ToolType.CI, context, params)
        if not result.success:
            raise ValueError(result.error)
        return [r.dict() for r in result.data.records]
```

## Migration Strategy

### Phase 2A: Foundation (Week 1)
1. Add ToolExecutor to runner ✓ (Already done in implementation)
2. Create compatibility adapters for tool result formats ✓ (Already done)
3. Implement gradual migration pattern for tool calls

### Phase 2B: Tool Integration (Weeks 2-3)
4. Refactor CI tool calls (_ci_search, _ci_get, etc.)
5. Refactor Metric tool calls (_metric_aggregate, _metric_series_table, etc.)
6. Refactor Graph tool calls (_graph_expand, _graph_path, etc.)
7. Refactor History tool calls (_history_recent, etc.)
8. Refactor CEP tool calls (_cep_simulate, etc.)

### Phase 2C: Cleanup (Week 4)
9. Remove direct tool imports (optional, can keep for fallback)
10. Update documentation
11. Test backward compatibility

## Implementation Pattern

### Pattern 1: Simple Tool Call Migration

**Old Code:**
```python
def _ci_get(self, ci_id: str) -> Dict[str, Any] | None:
    with self._tool_context("ci.get", input_params={"ci_id": ci_id}, ci_id=ci_id) as meta:
        detail = ci_tools.ci_get(self.tenant_id, ci_id)
        meta["found"] = bool(detail)
    return detail.dict() if detail else None
```

**New Code:**
```python
def _ci_get(self, ci_id: str) -> Dict[str, Any] | None:
    with self._tool_context("ci.get", input_params={"ci_id": ci_id}, ci_id=ci_id) as meta:
        context = ToolContext(tenant_id=self.tenant_id, request_id=get_request_context().get("request_id"))
        params = {
            "operation": "get",
            "ci_id": ci_id,
        }
        tool_result = self._tool_executor.execute(ToolType.CI, context, params)

        if not tool_result.success:
            # Log error but maintain graceful fallback
            self.logger.warning(f"CI get failed: {tool_result.error}")
            return None

        detail = tool_result.data
        meta["found"] = bool(detail)
    return detail.dict() if detail else None
```

## Tool Operation Mappings

### CI Tool

| Current Function | Operation | Parameters |
|---|---|---|
| `ci_search()` | `search` | keywords, filters, limit, sort |
| `ci_search_broad_or()` | `search_broad_or` | keywords, filters, limit, sort |
| `ci_get()` | `get` | ci_id |
| `ci_get_by_code()` | `get_by_code` | ci_code |
| `ci_aggregate()` | `aggregate` | group_by, metrics, filters, ci_ids, top_n |
| `ci_list_preview()` | `list_preview` | limit, offset, filters |

### Metric Tool

| Current Function | Operation | Parameters |
|---|---|---|
| `metric_aggregate()` | `aggregate` | metric_name, time_range, agg, ci_id, ci_ids |
| `metric_series_table()` | `series` | ci_id, metric_name, time_range, limit |
| `metric_exists()` | `exists` | metric_name |
| `list_metric_names()` | `list` | limit |

### Graph Tool

| Current Function | Operation | Parameters |
|---|---|---|
| `graph_expand()` | `expand` | ci_id, view, depth, limits |
| `graph_path()` | `path` | ci_id, target_ci_id, max_hops |

### History Tool

| Current Function | Operation | Parameters |
|---|---|---|
| `event_log_recent()` | `event_log` | ci, time_range, limit, ci_ids |
| `recent_work_and_maintenance()` | `work_and_maintenance` | time_range, limit |
| `detect_history_sections()` | `detect_sections` | question |

### CEP Tool

| Current Function | Operation | Parameters |
|---|---|---|
| `cep_simulate()` | `simulate` | rule_id, ci_context, metric_context, history_context, test_payload |

## Error Handling Strategy

### Option 1: Strict (Recommended initially)
```python
if not result.success:
    raise ValueError(result.error)
```

### Option 2: Graceful Fallback
```python
if not result.success:
    self.logger.warning(f"Tool failed: {result.error}")
    # Return safe default or skip this step
    return None
```

### Option 3: Partial Failure with Warnings
```python
if not result.success:
    result.add_warning(f"Tool failed: {result.error}")
    # Continue with partial data
    return partial_data
```

## Testing Strategy

### Unit Tests
- Test each refactored method in isolation
- Mock ToolExecutor to verify parameter passing
- Test error handling paths

### Integration Tests
- Test entire query flow with real tools
- Verify backward compatibility with existing tests
- Test error recovery

### Regression Tests
- Run existing test suite to ensure no breaking changes
- Compare results before/after refactoring
- Measure performance impact

## Rollback Plan

If issues arise during Phase 2:

1. **Immediate Rollback**:
   - Revert runner.py imports to use direct tool functions
   - Direct function calls remain available for fallback

2. **Partial Rollback**:
   - Revert specific tool integrations while keeping others
   - Maintain compatibility layer for gradual migration

3. **Full Rollback**:
   - Remove ToolExecutor and compat layer from runner
   - Remove imports added in Phase 2

## Success Criteria

✅ All tool calls work through ToolRegistry
✅ Backward compatibility maintained (existing tests pass)
✅ Error handling is graceful and informative
✅ Performance impact is negligible (<5% overhead)
✅ Code complexity reduced (fewer tool imports, cleaner flow)
✅ Extensibility improved (new tools don't require runner changes)

## Future Improvements (Phase 3+)

1. **Async Execution**: Use async/await for tool calls in orchestrator
2. **Tool Caching**: Cache tool results for frequently accessed data
3. **Smart Tool Selection**: Let planner specify preferred tools/strategies
4. **Tool Composition**: Chain tools automatically for complex queries
5. **Observability**: Enhanced tracing and metrics collection

## Current Implementation Status

✅ Phase 1: Tool Interface Unification
  - BaseTool abstract class
  - ToolRegistry for dynamic tool management
  - All tools refactored to implement BaseTool interface

🔄 Phase 2: Orchestrator Generalization (In Progress)
  - ToolExecutor helper class ✓
  - Compatibility adapters ✓
  - Migration of tool calls (pending)

⏳ Phase 3: Document Search Integration
  - DocumentTool implementation
  - Integration with document search backend

⏳ Phase 4: UX & Error Handling Improvements
  - Graceful degradation
  - Progressive disclosure
  - Enhanced error messages
