# LLM-Based Tool Selection & Parallel Execution Implementation Checklist

## Phase 1: Plan Schema Extension (Priority: HIGH)

### ✅ 1.1 Extend PrimarySpec with tool_type
**File**: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`

```python
class PrimarySpec(SQLModel):
    keywords: List[str]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 10
    tool_type: str = Field(default="ci_lookup")  # ← ADD THIS
    # Optional: add validation
    # @field_validator('tool_type')
    # def validate_tool_type(cls, v):
    #     valid_types = ["ci_lookup", "metric_query", "graph_analysis"]
    #     if v not in valid_types:
    #         raise ValueError(f"Invalid tool_type: {v}")
    #     return v
```

**Checklist**:
- [ ] Read plan_schema.py to understand current structure
- [ ] Add tool_type field to PrimarySpec
- [ ] Add tool_type field to SecondarySpec
- [ ] Add tool_type field to MetricSpec
- [ ] Add tool_type field to AggregateSpec
- [ ] Add tool_type field to any other applicable Specs
- [ ] Add comments explaining tool_type
- [ ] Verify Plan model still validates correctly

### ✅ 1.2 Update Plan JSON examples in docstrings
**File**: `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`

- [ ] Update example Plan JSON in docstrings to show tool_type
- [ ] Document expected tool_type values
- [ ] Document default tool_type values

---

## Phase 2: Tool Registry Enhancement (Priority: HIGH)

### ✅ 2.1 Add input_schema to Tool class
**File**: `apps/api/app/modules/ops/services/ci/tools/base.py`

```python
class Tool(SQLModel):
    # ... existing fields ...
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON Schema defining tool input parameters"
    )
```

**Checklist**:
- [ ] Read tools/base.py to see current Tool class structure
- [ ] Add input_schema field
- [ ] Add get_input_schema() method if needed
- [ ] Document expected format

### ✅ 2.2 Add methods to ToolRegistry for tool info retrieval
**File**: `apps/api/app/modules/ops/services/ci/tools/registry.py`

```python
class ToolRegistry:
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool info including description and input_schema"""
        if tool_name not in self._tools:
            return None
        tool = self._tools[tool_name]
        return {
            "name": tool_name,
            "description": tool.get("description"),
            "input_schema": tool.get("input_schema"),
        }

    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """Get info for all registered tools"""
        return [
            self.get_tool_info(name)
            for name in self._tools.keys()
        ]

    def validate_tool_type(self, tool_type: str) -> bool:
        """Check if tool_type is valid"""
        return tool_type in self._tools
```

**Checklist**:
- [ ] Read tools/registry.py to understand current structure
- [ ] Add get_tool_info() method
- [ ] Add get_all_tools_info() method
- [ ] Add validate_tool_type() method
- [ ] Add docstrings and type hints
- [ ] Test methods with existing tools

---

## Phase 3: Catalog Loading (Priority: MEDIUM)

### ✅ 3.1 Create catalog loader function
**File**: `apps/api/app/modules/asset_registry/loader.py`

```python
def load_catalog_for_source(source_ref: str) -> Optional[Dict[str, Any]]:
    """
    Load catalog information for a specific data source.

    Args:
        source_ref: Reference to the data source (e.g., 'postgres_prod')

    Returns:
        Simplified catalog dict suitable for LLM prompt or None if not found
    """
    with get_session_context() as session:
        # Query for schema asset with matching source_ref
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "catalog")
            .where(TbAssetRegistry.status == "published")
        )
        assets = session.exec(query).all()

        for asset in assets:
            catalog_obj = asset.content.get("catalog", {}) if asset.content else {}
            if catalog_obj.get("source_ref") == source_ref:
                return _simplify_catalog_for_llm(catalog_obj)

        return None

def _simplify_catalog_for_llm(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert full catalog to simplified version suitable for LLM prompt.

    - Limit number of tables (top 5-10)
    - Limit number of columns per table
    - Include descriptions
    - Omit internal metadata
    """
    return {
        "source_ref": catalog.get("source_ref"),
        "tables": [
            {
                "name": table["name"],
                "description": table.get("description"),
                "columns": [
                    {
                        "name": col["name"],
                        "data_type": col.get("data_type"),
                        "description": col.get("description"),
                    }
                    for col in table.get("columns", [])[:10]  # Limit columns
                ]
            }
            for table in catalog.get("tables", [])[:10]  # Limit tables
        ]
    }
```

**Checklist**:
- [ ] Read loader.py to understand current structure and patterns
- [ ] Add load_catalog_for_source() function
- [ ] Add _simplify_catalog_for_llm() helper function
- [ ] Handle missing catalogs gracefully
- [ ] Test with real Asset Registry data
- [ ] Verify output is JSON-serializable for prompt

### ✅ 3.2 Cache catalog loading
**File**: `apps/api/app/modules/asset_registry/loader.py`

```python
from functools import lru_cache

@lru_cache(maxsize=32)
def load_catalog_for_source(source_ref: str) -> Optional[Dict[str, Any]]:
    """Load catalog information (cached)"""
    # ... implementation ...
```

**Checklist**:
- [ ] Add caching to avoid repeated DB queries
- [ ] Document cache behavior
- [ ] Consider cache invalidation strategy

---

## Phase 4: Planner Prompt Improvement (Priority: HIGH)

### ✅ 4.1 Enhance build_planner_prompt() function
**File**: `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`

```python
def build_planner_prompt(
    user_query: str,
    tool_registry_info: Optional[List[Dict[str, Any]]] = None,
    catalog_info: Optional[Dict[str, Any]] = None,
    mapping_assets: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build complete prompt for Planner LLM.

    Args:
        user_query: User's natural language query
        tool_registry_info: List of available tools with descriptions and schemas
        catalog_info: Database catalog with table/column information
        mapping_assets: Available keyword mappings

    Returns:
        Complete prompt string for LLM
    """

    # Existing prompt building logic...

    prompt = f"""
You are a CI/OPS Infrastructure Query Planner.

Your task is to:
1. Understand the user's infrastructure and metrics query
2. Select appropriate tools to execute
3. Define query parameters based on available data
4. Generate a structured Plan JSON

User Query:
{user_query}

======================================
AVAILABLE TOOLS (you must choose from these):
======================================
{_format_tools_info(tool_registry_info)}

======================================
DATABASE SCHEMA INFORMATION:
======================================
{_format_catalog_info(catalog_info)}

======================================
AVAILABLE KEYWORD MAPPINGS:
======================================
{_format_mapping_assets(mapping_assets)}

======================================
INSTRUCTIONS:
======================================
1. Analyze the user query
2. Determine the intent (QueryMetrics, QueryStructure, etc.)
3. Select tool_type from AVAILABLE TOOLS section
4. Define filters based on DATABASE SCHEMA (use actual column/table names)
5. Extract keywords using KEYWORD MAPPINGS where applicable
6. Return a valid Plan JSON with all required fields

Important: tool_type MUST be one of the tool names listed in AVAILABLE TOOLS.

Example output format (as JSON):
{{
    "intent": "QueryMetrics",
    "mode": "complete",
    "primary": {{
        "keywords": ["server", "prod"],
        "filters": {{"environment": "prod"}},
        "limit": 10,
        "tool_type": "ci_lookup"
    }},
    "metric": {{
        "metric_name": "cpu_usage",
        "agg": "avg",
        "time_range": {{...}},
        "tool_type": "metric_query"
    }}
}}
"""
    return prompt

def _format_tools_info(tools: Optional[List[Dict[str, Any]]]) -> str:
    """Format tool registry info for prompt"""
    if not tools:
        return "No tools available"

    lines = []
    for tool in tools:
        lines.append(f"- Name: {tool.get('name')}")
        lines.append(f"  Description: {tool.get('description')}")
        if tool.get('input_schema'):
            lines.append(f"  Input Schema: {json.dumps(tool['input_schema'], indent=4)}")

    return "\n".join(lines)

def _format_catalog_info(catalog: Optional[Dict[str, Any]]) -> str:
    """Format catalog info for prompt"""
    if not catalog:
        return "No catalog information available"

    lines = [f"Source: {catalog.get('source_ref')}"]
    for table in catalog.get('tables', []):
        lines.append(f"\nTable: {table['name']}")
        lines.append(f"  Description: {table.get('description')}")
        lines.append(f"  Columns:")
        for col in table.get('columns', []):
            lines.append(f"    - {col['name']} ({col.get('data_type')})")
            if col.get('description'):
                lines.append(f"      {col['description']}")

    return "\n".join(lines)

def _format_mapping_assets(mappings: Optional[Dict[str, Any]]) -> str:
    """Format mapping assets for prompt"""
    if not mappings:
        return "No mappings available"

    lines = []
    for mapping_type, mapping_data in mappings.items():
        lines.append(f"- {mapping_type}: {str(mapping_data)[:100]}...")

    return "\n".join(lines)
```

**Checklist**:
- [ ] Read current planner_llm.py build_planner_prompt() function
- [ ] Add tool_registry_info parameter
- [ ] Add catalog_info parameter
- [ ] Add formatting helper functions
- [ ] Update prompt text to instruct LLM about tool selection
- [ ] Add examples of tool_type in example Plan JSON
- [ ] Test prompt with sample data

### ✅ 4.2 Modify plan_llm_query() to load and pass context info
**File**: `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`

```python
async def plan_llm_query(
    query: str,
    tenant_id: str,
    context: Optional[Any] = None,
) -> Plan:
    """
    Generate a Plan from a natural language query using LLM.

    Now loads and includes:
    - Available tools info
    - Database catalog info
    - Mapping assets
    """

    # Load tool registry info
    from app.modules.ops.services.ci.tools.registry import get_tool_registry
    tool_registry = get_tool_registry()
    tools_info = tool_registry.get_all_tools_info()

    # Load catalog info (example: for 'postgres_prod' source)
    from app.modules.asset_registry.loader import load_catalog_for_source
    catalog_info = load_catalog_for_source("postgres_prod")

    # Load mapping assets (existing)
    mappings = {
        "metric_aliases": _get_metric_aliases(),
        "agg_keywords": _get_agg_keywords(),
        # ... other mappings
    }

    # Build enhanced prompt
    prompt = build_planner_prompt(
        user_query=query,
        tool_registry_info=tools_info,
        catalog_info=catalog_info,
        mapping_assets=mappings,
    )

    # Call LLM with enhanced prompt
    llm_client = get_llm_client()
    response = await llm_client.generate(prompt)

    # Parse response to Plan
    plan = _parse_plan_json(response)

    # Validate plan
    plan = _validate_plan(plan)

    return plan
```

**Checklist**:
- [ ] Find current plan_llm_query() function signature
- [ ] Add tool registry loading
- [ ] Add catalog loading
- [ ] Pass all context to build_planner_prompt()
- [ ] Update function docstring
- [ ] Test with sample queries

### ✅ 4.3 Add Plan validation
**File**: `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`

```python
def _validate_plan(plan: Plan) -> Plan:
    """
    Validate Plan structure and tool_type selections.

    Ensures:
    - tool_type values are valid (exist in tool registry)
    - required fields are present
    - filter structure is valid
    """
    from app.modules.ops.services.ci.tools.registry import get_tool_registry
    tool_registry = get_tool_registry()

    # Validate primary spec
    if plan.primary:
        if not tool_registry.validate_tool_type(plan.primary.tool_type):
            logger.warning(
                f"Invalid tool_type in primary spec: {plan.primary.tool_type}, "
                f"using default: ci_lookup"
            )
            plan.primary.tool_type = "ci_lookup"

    # Validate metric spec
    if plan.metric:
        if not tool_registry.validate_tool_type(plan.metric.tool_type):
            logger.warning(
                f"Invalid tool_type in metric spec: {plan.metric.tool_type}, "
                f"using default: metric_query"
            )
            plan.metric.tool_type = "metric_query"

    # ... validate other specs ...

    return plan
```

**Checklist**:
- [ ] Add _validate_plan() function
- [ ] Validate all tool_type fields
- [ ] Provide helpful defaults for invalid tool_type
- [ ] Log validation issues
- [ ] Test with both valid and invalid Plans

---

## Phase 5: Stage Executor Parallel Execution (Priority: HIGH)

### ✅ 5.1 Modify _execute_execute() to use dynamic tool_type
**File**: `apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py`

```python
async def _execute_execute(self, plan: Plan) -> ExecuteOutput:
    """
    Execute the Execute stage with dynamic tool selection and parallel execution.

    BEFORE: Hardcoded tool_type values
    AFTER:  Dynamic tool_type from Plan + Parallel execution
    """

    tasks = []
    results_map = {}

    # Primary query
    if plan.primary:
        tool_type = plan.primary.tool_type  # ← Dynamic (was: "ci_lookup")
        task = asyncio.create_task(
            self._execute_tool_async(
                tool_type=tool_type,
                params={
                    "keywords": plan.primary.keywords,
                    "filters": plan.primary.filters,
                    "limit": plan.primary.limit,
                }
            )
        )
        tasks.append(("primary", task))

    # Secondary query
    if plan.secondary:
        tool_type = plan.secondary.tool_type  # ← Dynamic (was: "ci_lookup")
        task = asyncio.create_task(
            self._execute_tool_async(
                tool_type=tool_type,
                params={
                    "keywords": plan.secondary.keywords,
                    "filters": plan.secondary.filters,
                    "limit": plan.secondary.limit,
                }
            )
        )
        tasks.append(("secondary", task))

    # Metric query
    if plan.metric:
        tool_type = plan.metric.tool_type  # ← Dynamic (was: "metric")
        task = asyncio.create_task(
            self._execute_tool_async(
                tool_type=tool_type,
                params={
                    "metric_name": plan.metric.metric_name,
                    "agg": plan.metric.agg,
                    "time_range": plan.metric.time_range,
                    "scope": plan.metric.scope,
                }
            )
        )
        tasks.append(("metric", task))

    # Execute all tasks in parallel
    if tasks:
        for key, task in tasks:
            try:
                result = await task
                results_map[key] = result
            except Exception as e:
                logger.error(f"Tool execution failed for {key}: {e}")
                results_map[key] = None

    return ExecuteOutput(
        primary_results=results_map.get("primary"),
        secondary_results=results_map.get("secondary"),
        metric_results=results_map.get("metric"),
    )

async def _execute_tool_async(
    self,
    tool_type: str,
    params: Dict[str, Any],
) -> Any:
    """Execute a single tool asynchronously"""
    # Get tool from registry
    tool = self.tool_registry.get_tool(tool_type)
    if not tool:
        raise ValueError(f"Tool not found: {tool_type}")

    # Execute tool (may be async)
    if asyncio.iscoroutinefunction(tool.execute):
        return await tool.execute(params)
    else:
        # Run sync tool in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(
            None, tool.execute, params
        )
```

**Checklist**:
- [ ] Read current _execute_execute() method
- [ ] Extract tool_type from Plan specs (not hardcoded)
- [ ] Convert sequential execution to parallel (asyncio.gather or similar)
- [ ] Add async task creation helper _execute_tool_async()
- [ ] Add proper error handling for parallel execution
- [ ] Add logging for debugging
- [ ] Test with multiple tools in parallel

### ✅ 5.2 Add asyncio.gather() based parallel execution alternative
**File**: `apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py`

```python
async def _execute_execute_parallel(self, plan: Plan) -> ExecuteOutput:
    """
    Alternative implementation using asyncio.gather for parallel execution.

    Benefits:
    - Simpler code
    - Returns all results as tuple
    - Automatic error handling options
    """

    primary_task = None
    secondary_task = None
    metric_task = None

    # Create tasks
    if plan.primary:
        primary_task = self._execute_tool_async(
            tool_type=plan.primary.tool_type,
            params={
                "keywords": plan.primary.keywords,
                "filters": plan.primary.filters,
                "limit": plan.primary.limit,
            }
        )

    if plan.secondary:
        secondary_task = self._execute_tool_async(
            tool_type=plan.secondary.tool_type,
            params={
                "keywords": plan.secondary.keywords,
                "filters": plan.secondary.filters,
                "limit": plan.secondary.limit,
            }
        )

    if plan.metric:
        metric_task = self._execute_tool_async(
            tool_type=plan.metric.tool_type,
            params={
                "metric_name": plan.metric.metric_name,
                "agg": plan.metric.agg,
                "time_range": plan.metric.time_range,
                "scope": plan.metric.scope,
            }
        )

    # Gather all tasks
    tasks = [t for t in [primary_task, secondary_task, metric_task] if t]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Map results back
    result_idx = 0
    primary_result = results[result_idx] if primary_task else None
    result_idx += 1
    secondary_result = results[result_idx] if secondary_task else None
    result_idx += 1
    metric_result = results[result_idx] if metric_task else None

    return ExecuteOutput(
        primary_results=primary_result,
        secondary_results=secondary_result,
        metric_results=metric_result,
    )
```

**Checklist**:
- [ ] Choose between task-based or gather-based approach
- [ ] Implement chosen approach
- [ ] Document the chosen approach and why
- [ ] Add performance metrics/logging

---

## Phase 6: Testing & Validation (Priority: MEDIUM)

### ✅ 6.1 Unit tests for Plan schema extension
**File**: `apps/api/tests/test_plan_schema.py`

```python
def test_primary_spec_has_tool_type():
    """Test that PrimarySpec includes tool_type field"""
    spec = PrimarySpec(
        keywords=["cpu"],
        filters={},
        limit=10,
        tool_type="ci_lookup"
    )
    assert spec.tool_type == "ci_lookup"
    assert spec.tool_type == "ci_lookup"  # Has default

def test_tool_type_default_value():
    """Test that tool_type has sensible default"""
    spec = PrimarySpec(
        keywords=["test"],
    )
    assert spec.tool_type == "ci_lookup"  # Default

def test_plan_with_multiple_tool_types():
    """Test Plan with different tool_types"""
    plan = Plan(
        intent=Intent.QUERY,
        mode=PlanMode.COMPLETE,
        primary=PrimarySpec(
            keywords=["server"],
            tool_type="ci_lookup"
        ),
        metric=MetricSpec(
            metric_name="cpu_usage",
            agg="avg",
            time_range=TimeRangeSpec(...),
            tool_type="metric_query"
        )
    )
    assert plan.primary.tool_type == "ci_lookup"
    assert plan.metric.tool_type == "metric_query"
```

**Checklist**:
- [ ] Create test_plan_schema.py if it doesn't exist
- [ ] Add tests for tool_type in each Spec class
- [ ] Test default values
- [ ] Test Plan validation with multiple specs

### ✅ 6.2 Integration test for Planner with tools info
**File**: `apps/api/tests/test_planner_with_tools.py`

```python
@pytest.mark.asyncio
async def test_planner_receives_tools_info():
    """Test that Planner builds prompt with tools info"""
    from app.modules.ops.services.ci.planner.planner_llm import build_planner_prompt

    tools_info = [
        {
            "name": "ci_lookup",
            "description": "Lookup CI assets",
            "input_schema": {...}
        },
        {
            "name": "metric_query",
            "description": "Query metrics",
            "input_schema": {...}
        }
    ]

    prompt = build_planner_prompt(
        user_query="Show me CPU usage",
        tool_registry_info=tools_info,
    )

    # Verify prompt includes tool info
    assert "ci_lookup" in prompt
    assert "metric_query" in prompt
    assert "Available tools" in prompt.lower() or "tool" in prompt.lower()

@pytest.mark.asyncio
async def test_planner_output_includes_tool_type():
    """Test that LLM output Plan includes tool_type"""
    plan = await plan_llm_query("Show CPU usage for prod servers")

    assert plan.primary.tool_type is not None
    assert plan.metric.tool_type is not None
```

**Checklist**:
- [ ] Create test_planner_with_tools.py
- [ ] Test prompt building with tools info
- [ ] Test that LLM returns valid tool_type values
- [ ] Test that invalid tool_type is corrected

### ✅ 6.3 Integration test for parallel execution
**File**: `apps/api/tests/test_parallel_execution.py`

```python
@pytest.mark.asyncio
async def test_parallel_tool_execution():
    """Test that tools execute in parallel"""
    import time

    plan = Plan(
        intent=Intent.QUERY,
        mode=PlanMode.COMPLETE,
        primary=PrimarySpec(..., tool_type="ci_lookup"),
        metric=MetricSpec(..., tool_type="metric_query"),
    )

    executor = StageExecutor(tool_registry)

    start = time.time()
    output = await executor._execute_execute(plan)
    elapsed = time.time() - start

    # Should complete faster than sequential (primary + metric)
    # Assume each tool takes ~100ms, parallel should be ~100ms, sequential ~200ms
    assert elapsed < 150  # Some margin for overhead
    assert output.primary_results is not None
    assert output.metric_results is not None

@pytest.mark.asyncio
async def test_tool_execution_error_handling():
    """Test that parallel execution handles tool errors gracefully"""
    plan = Plan(
        intent=Intent.QUERY,
        primary=PrimarySpec(..., tool_type="invalid_tool"),
    )

    executor = StageExecutor(tool_registry)
    output = await executor._execute_execute(plan)

    # Should not raise, but log error
    assert output.primary_results is None  # Or some error indication
```

**Checklist**:
- [ ] Create test_parallel_execution.py
- [ ] Test parallel execution timing
- [ ] Test error handling in parallel tasks
- [ ] Test that results are correctly mapped

### ✅ 6.4 End-to-end integration test
**File**: `apps/api/tests/test_e2e_tool_selection.py`

```python
@pytest.mark.asyncio
async def test_e2e_user_query_to_tool_execution():
    """
    End-to-end test:
    User Query → Planner → Plan (with tool_type) → Executor → Results
    """

    # Setup
    from app.modules.ops.services.ci.orchestrator.orchestrator import Orchestrator
    orchestrator = Orchestrator()

    # User query
    user_query = "Show CPU usage for production servers"

    # Full orchestration
    result = await orchestrator.execute_query(user_query, tenant_id="test")

    # Verify result
    assert result is not None
    assert result.status == "success"
    assert result.data is not None

    # Verify that Plan used dynamic tool_type (not hardcoded)
    # (may need to expose Plan in result for testing)
    assert result.plan.primary.tool_type in ["ci_lookup", "metric_query"]
    assert result.plan.metric.tool_type in ["ci_lookup", "metric_query"]
```

**Checklist**:
- [ ] Create test_e2e_tool_selection.py
- [ ] Test complete flow from query to results
- [ ] Verify tool_type is selected dynamically
- [ ] Verify parallel execution occurs
- [ ] Test with multiple different user queries

---

## Phase 7: Documentation & Deployment (Priority: MEDIUM)

### ✅ 7.1 Update Tool Registry documentation
**File**: `docs/TOOL_REGISTRY.md`

- [ ] Document Tool class with input_schema field
- [ ] Document get_tool_info() and get_all_tools_info() methods
- [ ] Provide examples of tool input schemas
- [ ] Document tool validation

### ✅ 7.2 Update Planner documentation
**File**: `docs/PLANNER.md`

- [ ] Document tool_type field in Plan specs
- [ ] Document how LLM selects tools
- [ ] Provide examples of Plan with tool_type
- [ ] Document validation and error handling

### ✅ 7.3 Create deployment guide
**File**: `docs/DEPLOYMENT_GUIDE.md`

- [ ] Document migration steps from old to new version
- [ ] Document how to handle existing Plans (backward compatibility?)
- [ ] Document rollback plan
- [ ] Document monitoring points

### ✅ 7.4 Update API documentation
**File**: Update OpenAPI/Swagger docs

- [ ] Update Plan schema in API docs
- [ ] Document new tool_type field
- [ ] Update examples

---

## Phase 8: Performance Optimization (Priority: LOW)

### ✅ 8.1 Benchmark parallel vs sequential execution
- [ ] Measure execution time with 1 tool vs 2 vs 3 tools
- [ ] Measure total response time improvement
- [ ] Identify bottlenecks

### ✅ 8.2 Optimize catalog loading
- [ ] Cache catalog data
- [ ] Consider pagination for large catalogs
- [ ] Monitor catalog query performance

### ✅ 8.3 Optimize prompt size
- [ ] Measure prompt token count
- [ ] Consider summarization of large catalogs
- [ ] Consider selective tool/table inclusion

---

## Implementation Priority Summary

### IMMEDIATE (This Week)
1. **Plan Schema Extension** - Add tool_type field ⭐⭐⭐
2. **Planner Prompt** - Include tools info + instruction ⭐⭐⭐
3. **Parallel Execution** - Modify stage_executor ⭐⭐⭐

### SHORT-TERM (Next Week)
4. **Tool Registry Enhancement** - Add input_schema support ⭐⭐
5. **Catalog Loading** - Create loader function ⭐⭐
6. **Validation** - Plan validation for tool_type ⭐⭐

### MEDIUM-TERM (2-3 Weeks)
7. **Comprehensive Testing** - Unit + integration tests ⭐
8. **Documentation** - API + deployment docs
9. **Performance Optimization** - Benchmarking + tuning

### LONG-TERM
10. Advanced features like dynamic tool selection based on cost/performance
11. Tool chaining and composition
12. Real-time tool status monitoring

---

## Risk Mitigation

### Risk: LLM generates invalid tool_type
**Mitigation**:
- Add validation in _validate_plan()
- Provide specific list in prompt with example
- Fallback to default tool_type if invalid

### Risk: Parallel execution breaks existing code
**Mitigation**:
- Maintain backward compatibility with sequential execution option
- Add feature flag to toggle between sequential/parallel
- Comprehensive testing before deployment

### Risk: Catalog info too large for prompt
**Mitigation**:
- Implement catalog summarization
- Limit tables and columns per source
- Consider separate catalog lookup API

### Risk: Performance degradation
**Mitigation**:
- Benchmark before/after
- Monitor token usage for LLM calls
- Implement caching where possible

---

## Success Criteria

- ✅ All existing tests pass
- ✅ New Plan schema with tool_type works
- ✅ LLM successfully selects tool_type from available tools
- ✅ Parallel execution is 30%+ faster than sequential for multiple tools
- ✅ Invalid tool_type values are caught and corrected
- ✅ E2E tests pass with multiple tool selections
- ✅ No performance regression in single-tool scenarios
- ✅ Documentation is complete and up-to-date
