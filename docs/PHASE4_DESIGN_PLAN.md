# Phase 4 Design Plan: Advanced Features

## Overview

Phase 4 introduces advanced features built on top of the optimized Phase 3 async/await infrastructure. These features enhance functionality, performance, and user experience through intelligent tool usage patterns.

## Phase 4 Components

### Component 4.1: Tool Result Caching

**Objective**: Cache frequently accessed tool results to reduce execution time and database load.

**Design**:

```python
# apps/api/app/modules/ops/services/ci/tools/cache.py (NEW)

from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json

@dataclass
class CacheEntry:
    """Represents a cached tool result."""
    key: str
    value: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    miss_count: int = 0

class ToolResultCache:
    """
    In-memory cache for tool results with TTL and LRU eviction.

    Features:
    - TTL (Time-to-Live) per cache entry
    - LRU (Least Recently Used) eviction policy
    - Cache hit/miss tracking
    - Configurable cache size limits
    """

    def __init__(self, max_size: int = 1000, default_ttl: timedelta = timedelta(minutes=5)):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get value from cache if exists and not expired.
        Updates access time for LRU tracking.
        """
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check expiration
            if datetime.now() > entry.expires_at:
                del self._cache[key]
                return None

            # Update hit count and move to end (LRU)
            entry.hit_count += 1
            return entry.value

    async def set(self, key: str, value: Dict[str, Any], ttl: Optional[timedelta] = None):
        """
        Set value in cache with TTL.
        Evicts LRU entry if cache is full.
        """
        async with self._lock:
            # Evict if needed
            if len(self._cache) >= self._max_size:
                # Find and remove least recently used
                lru_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at
                )
                del self._cache[lru_key]

            # Insert new entry
            ttl = ttl or self._default_ttl
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + ttl,
            )
            self._cache[key] = entry

    def _generate_key(self, tool_type: str, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key from tool parameters."""
        # Only include relevant params for cache key
        cacheable_params = {
            k: v for k, v in params.items()
            if k not in ['operation', 'request_id', 'trace_id']
        }
        key_str = json.dumps(
            {'tool': tool_type, 'op': operation, 'params': cacheable_params},
            sort_keys=True
        )
        return hashlib.md5(key_str.encode()).hexdigest()
```

**Integration with ToolExecutor**:

```python
# In ToolExecutor
class ToolExecutor:
    def __init__(self, registry: ToolRegistry, cache: Optional[ToolResultCache] = None):
        self._registry = registry
        self._cache = cache

    async def execute_async(
        self,
        tool_type: ToolType,
        context: ToolContext,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute tool with caching support."""
        # Generate cache key
        cache_key = self._cache._generate_key(
            tool_type.value,
            params.get('operation', ''),
            params
        )

        # Try cache first
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                context.metadata['cache_hit'] = True
                return cached

        # Execute tool
        operation = params.get("operation")
        if not operation:
            raise ValueError("operation parameter required")

        tool = self._registry.get_tool(tool_type, operation)
        if not tool:
            raise ValueError(f"Tool not found: {tool_type.value}/{operation}")

        result = await tool.safe_execute(context, params)
        if not result.success:
            raise ValueError(result.error or "Unknown tool error")

        # Cache successful result
        if self._cache and result.success:
            await self._cache.set(cache_key, result.data)

        return result.data
```

**Cache Policy Configuration**:

```python
# Configuration file (config/cache.yaml or settings)
cache:
  enabled: true
  max_size: 1000
  ttl_by_tool:
    CI:
      search: 5m      # CI search results cached for 5 minutes
      get: 10m        # CI items cached for 10 minutes
      aggregate: 5m
    METRIC:
      aggregate: 3m   # Metrics cached for 3 minutes (more dynamic)
      series: 2m
    GRAPH:
      expand: 10m     # Graph structure cached longer
      path: 10m
    HISTORY:
      event_log: 2m   # History is more dynamic
    CEP:
      simulate: 1m    # Simulations not cached (always fresh)
```

### Component 4.2: Smart Tool Selection by Planner

**Objective**: Optimize tool selection based on user intent and data characteristics.

**Design**:

```python
# apps/api/app/modules/ops/services/ci/orchestrator/tool_selector.py (NEW)

from enum import Enum
from dataclasses import dataclass

class SelectionStrategy(Enum):
    """Strategy for selecting tools."""
    FASTEST = "fastest"           # Choose fastest tool
    MOST_ACCURATE = "most_accurate"  # Choose most accurate
    MOST_COMPLETE = "most_complete"  # Choose most comprehensive
    LEAST_LOAD = "least_load"     # Choose tool with least current load

@dataclass
class ToolSelectionContext:
    """Context for tool selection decision."""
    intent: Intent
    user_pref: SelectionStrategy
    current_load: Dict[str, float]  # Tool → load percentage
    cache_status: Dict[str, bool]   # Tool → is_cached
    estimated_time: Dict[str, float]  # Tool → est. execution time

class SmartToolSelector:
    """
    Intelligently selects tools based on multiple factors:
    - Intent type and specificity
    - Data characteristics
    - Performance profile
    - Current system load
    - Cache availability
    - User preferences
    """

    def __init__(self):
        self._tool_profiles = self._load_tool_profiles()
        self._performance_history = {}

    async def select_tools(
        self,
        context: ToolSelectionContext,
    ) -> List[Tuple[str, float]]:  # [(tool_name, confidence), ...]
        """
        Select best tools for intent.
        Returns list of tools with confidence scores.
        """
        candidates = self._get_candidate_tools(context.intent)

        # Score each candidate
        scores = {}
        for tool_name in candidates:
            score = await self._score_tool(tool_name, context)
            scores[tool_name] = score

        # Sort by score and return
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    async def _score_tool(
        self,
        tool_name: str,
        context: ToolSelectionContext,
    ) -> float:
        """Score tool for given context."""
        score = 0.0

        # 1. Accuracy score (base)
        accuracy = self._tool_profiles[tool_name]['accuracy']
        score += accuracy * 0.3

        # 2. Performance score
        est_time = context.estimated_time.get(tool_name, 100)
        performance = 1.0 / (1.0 + est_time / 1000)  # Normalize
        score += performance * 0.25

        # 3. Cache score
        is_cached = context.cache_status.get(tool_name, False)
        cache_bonus = 0.5 if is_cached else 0.0
        score += cache_bonus * 0.15

        # 4. Load score
        load = context.current_load.get(tool_name, 0.0)
        load_bonus = 1.0 - load  # Prefer less loaded tools
        score += load_bonus * 0.2

        # 5. Intent-specific bonuses
        intent_bonus = self._get_intent_bonus(tool_name, context.intent)
        score += intent_bonus * 0.1

        return min(score, 1.0)  # Cap at 1.0

    def _get_candidate_tools(self, intent: Intent) -> List[str]:
        """Get candidate tools for intent type."""
        mapping = {
            IntentType.SEARCH: ['CI_SEARCH', 'CI_FILTER'],
            IntentType.METRIC: ['METRIC_AGGREGATE', 'METRIC_SERIES'],
            IntentType.RELATIONSHIP: ['GRAPH_EXPAND', 'GRAPH_PATH'],
            IntentType.HISTORY: ['HISTORY_EVENT_LOG'],
            IntentType.ANALYSIS: ['CEP_SIMULATE'],
            # ... etc
        }
        return mapping.get(intent.type, [])
```

**Usage in Runner**:

```python
# In CIOrchestratorRunner
class CIOrchestratorRunner:
    def __init__(self, ...):
        self._tool_selector = SmartToolSelector()
        self._tool_executor = get_tool_executor()

    async def _select_best_tools(self) -> List[str]:
        """Select optimal tools for current intent."""
        context = ToolSelectionContext(
            intent=self.plan.primary.intent,
            user_pref=self.plan.mode,  # User preference
            current_load=await self._get_system_load(),
            cache_status=await self._check_cache_status(),
            estimated_time=self._tool_profiles,
        )
        ranked_tools = await self._tool_selector.select_tools(context)
        return [tool for tool, _ in ranked_tools]
```

### Component 4.3: Tool Composition & Chaining

**Objective**: Enable intelligent composition of multiple tools to provide more comprehensive results.

**Design**:

```python
# apps/api/app/modules/ops/services/ci/orchestrator/tool_composition.py (NEW)

from typing import Callable, List, Dict, Any
from dataclasses import dataclass

@dataclass
class CompositionStep:
    """Single step in a composition."""
    tool_name: str
    operation: str
    params_transform: Callable[[Dict[str, Any]], Dict[str, Any]]  # Transform previous result
    error_handling: str = "fail_fast"  # "fail_fast", "skip", "fallback"

class CompositionPipeline:
    """
    Chain multiple tools together, passing results through pipeline.

    Example:
        1. CI Search → Find services
        2. Graph Expand → Get relationships
        3. Metric Aggregate → Get metrics for all related services
        4. History Recent → Get recent events for context
    """

    def __init__(self, steps: List[CompositionStep]):
        self.steps = steps
        self.results = []

    async def execute(self, executor: ToolExecutor, initial_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute composition pipeline."""
        current_result = initial_params

        for step in self.steps:
            try:
                # Transform params based on previous result
                params = step.params_transform(current_result)

                # Execute tool
                result = await executor.execute_async(
                    ToolType[step.tool_name],
                    step.operation,
                    **params
                )

                # Store result
                self.results.append({
                    'step': step.tool_name,
                    'result': result
                })

                # Use result for next step
                current_result = result

            except Exception as e:
                self._handle_step_error(step, e)

        return self._aggregate_results()

    def _handle_step_error(self, step: CompositionStep, error: Exception):
        """Handle error based on step configuration."""
        if step.error_handling == "fail_fast":
            raise error
        elif step.error_handling == "skip":
            self.logger.warning(f"Skipping {step.tool_name}: {error}")
        elif step.error_handling == "fallback":
            # Try fallback tool or operation
            self.logger.info(f"Falling back for {step.tool_name}")

    def _aggregate_results(self) -> Dict[str, Any]:
        """Combine results from all steps."""
        return {
            'primary': self.results[0]['result'] if self.results else None,
            'enriched': {r['step']: r['result'] for r in self.results[1:]},
            'execution_trace': [r['step'] for r in self.results],
        }
```

**Predefined Compositions**:

```python
# apps/api/app/modules/ops/services/ci/orchestrator/compositions.py

COMPOSITION_SEARCH_WITH_CONTEXT = CompositionPipeline([
    CompositionStep(
        tool_name="CI",
        operation="search",
        params_transform=lambda p: p,
        error_handling="fail_fast"
    ),
    CompositionStep(
        tool_name="METRIC",
        operation="aggregate",
        params_transform=lambda search_result: {
            'ci_ids': [ci['id'] for ci in search_result.get('records', [])],
            'metric_name': 'cpu_usage',
            'agg': 'avg',
            'time_range': 'last_1h'
        },
        error_handling="skip"
    ),
    CompositionStep(
        tool_name="HISTORY",
        operation="event_log",
        params_transform=lambda metric_result: {
            'ci_ids': metric_result.get('ci_ids', []),
            'time_range': 'last_1h',
            'limit': 10
        },
        error_handling="skip"
    ),
])

# Usage
result = await COMPOSITION_SEARCH_WITH_CONTEXT.execute(
    executor,
    {'keywords': ['database'], 'limit': 10}
)
```

### Component 4.4: Advanced Observability & Tracing

**Objective**: Enhanced monitoring and observability for tool execution and performance.

**Design**:

```python
# apps/api/app/modules/ops/services/ci/tools/observability.py (NEW)

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class ToolExecutionTrace:
    """Detailed trace of a single tool execution."""
    tool_type: str
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None
    cache_hit: bool = False
    input_params: Dict[str, Any] = field(default_factory=dict)
    result_size_bytes: int = 0
    result_count: Optional[int] = None  # For list results
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    fallback_used: bool = False

class ExecutionTracer:
    """
    Traces tool execution for monitoring and analysis.

    Tracks:
    - Execution time per tool
    - Cache hit rates
    - Error rates and types
    - Result sizes
    - Performance trends
    """

    def __init__(self):
        self.traces: List[ToolExecutionTrace] = []
        self._start_times: Dict[str, datetime] = {}

    def start_trace(self, tool_type: str, operation: str, params: Dict[str, Any]) -> str:
        """Start tracing a tool execution."""
        trace_id = f"{tool_type}_{operation}_{time.time()}"
        self._start_times[trace_id] = datetime.now()
        return trace_id

    def end_trace(
        self,
        trace_id: str,
        success: bool,
        error: Optional[str] = None,
        result_size: int = 0,
        result_count: Optional[int] = None,
        cache_hit: bool = False,
        **metadata
    ):
        """End tracing and store trace."""
        start_time = self._start_times.pop(trace_id)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000

        tool_type, operation, _ = trace_id.split('_', 2)
        trace = ToolExecutionTrace(
            tool_type=tool_type,
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration,
            success=success,
            error=error,
            cache_hit=cache_hit,
            result_size_bytes=result_size,
            result_count=result_count,
            metadata=metadata,
        )
        self.traces.append(trace)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.traces:
            return {}

        by_tool = {}
        for trace in self.traces:
            key = f"{trace.tool_type}/{trace.operation}"
            if key not in by_tool:
                by_tool[key] = {
                    'count': 0,
                    'success': 0,
                    'error': 0,
                    'total_time_ms': 0,
                    'avg_time_ms': 0,
                    'cache_hits': 0,
                    'cache_hit_rate': 0.0,
                }

            stats = by_tool[key]
            stats['count'] += 1
            if trace.success:
                stats['success'] += 1
            else:
                stats['error'] += 1
            stats['total_time_ms'] += trace.duration_ms
            if trace.cache_hit:
                stats['cache_hits'] += 1

        # Calculate averages
        for key in by_tool:
            stats = by_tool[key]
            stats['avg_time_ms'] = stats['total_time_ms'] / stats['count']
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['count']

        return by_tool

    def export_traces(self, format: str = "json") -> str:
        """Export traces for analysis."""
        if format == "json":
            return json.dumps([
                asdict(t) for t in self.traces
            ], default=str)
        elif format == "csv":
            # CSV export
            pass
        else:
            raise ValueError(f"Unknown format: {format}")
```

**Integration with Runner**:

```python
# In CIOrchestratorRunner
class CIOrchestratorRunner:
    def __init__(self, ...):
        self._tracer = ExecutionTracer()

    async def _execute_with_tracing(self, tool_type, operation, **params):
        """Execute tool with full tracing."""
        trace_id = self._tracer.start_trace(tool_type, operation, params)

        try:
            result = await self._tool_executor.execute_async(
                tool_type, operation, **params
            )
            self._tracer.end_trace(
                trace_id,
                success=True,
                result_size=len(str(result)),
                result_count=len(result) if isinstance(result, list) else None,
            )
            return result
        except Exception as e:
            self._tracer.end_trace(
                trace_id,
                success=False,
                error=str(e),
            )
            raise

    async def run(self):
        """Run with full tracing."""
        # ... run logic ...

        # Get performance summary
        stats = self._tracer.get_performance_stats()
        self.logger.info(f"Execution stats: {stats}")
        return result
```

## Phase 4 Implementation Steps

### Step 4.1: Implement Tool Result Cache

1. Create `apps/api/app/modules/ops/services/ci/tools/cache.py`
2. Implement `ToolResultCache` class with TTL and LRU
3. Update `ToolExecutor` to use cache
4. Add cache configuration
5. Test cache hit/miss scenarios

### Step 4.2: Implement Smart Tool Selection

1. Create `apps/api/app/modules/ops/services/ci/orchestrator/tool_selector.py`
2. Implement `SmartToolSelector` class
3. Add tool profiling infrastructure
4. Integrate with planner
5. Test selection logic with various intents

### Step 4.3: Implement Tool Composition

1. Create `apps/api/app/modules/ops/services/ci/orchestrator/tool_composition.py`
2. Implement `CompositionPipeline` class
3. Define predefined compositions
4. Add composition registry
5. Test compositions end-to-end

### Step 4.4: Implement Advanced Observability

1. Create `apps/api/app/modules/ops/services/ci/tools/observability.py`
2. Implement `ExecutionTracer` class
3. Integrate with ToolExecutor
4. Add metrics export
5. Test trace collection and analysis

## Phase 4 Testing Strategy

```python
# Test caching
async def test_cache_hit():
    cache = ToolResultCache()
    result1 = await executor.execute_async(...)
    result2 = await executor.execute_async(...)  # Should hit cache
    assert result1 == result2

# Test tool selection
async def test_smart_selection():
    selector = SmartToolSelector()
    context = ToolSelectionContext(...)
    selected = await selector.select_tools(context)
    assert selected[0][1] > 0.8  # High confidence

# Test composition
async def test_composition():
    pipeline = CompositionPipeline([...])
    result = await pipeline.execute(executor, {})
    assert 'primary' in result
    assert 'enriched' in result

# Test observability
async def test_tracing():
    tracer = ExecutionTracer()
    # ... execute tools ...
    stats = tracer.get_performance_stats()
    assert stats['CI/search']['count'] > 0
```

## Phase 4 File Structure

```
apps/api/app/modules/ops/services/ci/
├── tools/
│   ├── cache.py (NEW)
│   ├── observability.py (NEW)
│   ├── executor.py (MODIFIED - add cache integration)
│   └── ...
├── orchestrator/
│   ├── tool_selector.py (NEW)
│   ├── tool_composition.py (NEW)
│   ├── compositions.py (NEW)
│   ├── runner.py (MODIFIED - use new features)
│   └── ...
└── ...
```

## Phase 4 Success Criteria

✅ **All criteria must be met**:

1. ✅ Tool result caching implemented with TTL and LRU
2. ✅ Smart tool selection working with scoring algorithm
3. ✅ Tool composition pipeline functional
4. ✅ Advanced observability with detailed tracing
5. ✅ All components tested and validated
6. ✅ Performance improvements measured
7. ✅ 100% backward compatibility maintained
8. ✅ Documentation complete

---

## Summary for Codex

Phase 4 adds advanced features on top of Phase 3's async infrastructure:

1. **Tool Result Caching**: In-memory cache with TTL and LRU eviction
2. **Smart Tool Selection**: Intelligent selection based on intent and load
3. **Tool Composition**: Chain multiple tools for comprehensive results
4. **Advanced Observability**: Detailed tracing and performance analysis

All components are optional enhancements that improve performance and UX without breaking existing functionality.
