# LLM-Based Tool Selection & Parallel Execution - Complete Implementation Guide

## Quick Start

You now have **4 comprehensive documents** to guide the implementation:

### 📚 Document Overview

1. **SUMMARY.md** ← Start here!
   - 5-minute overview of the problem and solution
   - 3 key improvements explained
   - 6-phase implementation plan summary
   - Expected benefits and risks
   - **Best for**: Quick understanding of the big picture

2. **ARCHITECTURE_DIAGRAM.md** ← Visual learner?
   - Detailed flow diagrams (Before vs After)
   - Component interaction diagrams
   - Timeline comparisons (Sequential vs Parallel)
   - Code flow and implementation phases
   - **Best for**: Understanding the system architecture visually

3. **CATALOG_TO_LLM_ARCHITECTURE.md** ← Need technical details?
   - Complete data structure specifications
   - Prompt composition guide
   - Execution flow examples
   - Validation and error handling strategies
   - **Best for**: Understanding technical details and data structures

4. **IMPLEMENTATION_CHECKLIST.md** ← Ready to code?
   - Step-by-step implementation guidance for all 8 phases
   - Code examples for each phase
   - Testing strategy and test cases
   - Risk mitigation for each phase
   - **Best for**: Actual implementation with detailed checklists

5. **PHASE1_IMPLEMENTATION.md** ← Let's start coding!
   - Concrete code changes for Phase 1
   - Before/after code examples
   - Unit test templates
   - Integration test examples
   - Ready-to-use commit message
   - **Best for**: Getting started with Phase 1 immediately

---

## What Problem Are We Solving?

Your key insight:
> "LLM이 tool을 선택하고, catalog 정보를 받아서 parameters를 정의해야 한다"

**Current Issues**:
1. ❌ Tool selection is hardcoded (always "ci_lookup")
2. ❌ LLM doesn't see available tools
3. ❌ LLM doesn't know database structure
4. ❌ Tools execute sequentially (slow)

**Target Solution**:
1. ✅ LLM selects tool dynamically
2. ✅ LLM receives tools info
3. ✅ LLM receives catalog info (table/column metadata)
4. ✅ Tools execute in parallel (fast)

---

## 3 Key Improvements

### 1️⃣ Dynamic Tool Selection
- **What**: Add `tool_type` field to Plan
- **How**: LLM chooses tool from available options
- **Result**: New tools can be added without code changes

### 2️⃣ Intelligent Parameters
- **What**: Include catalog info in LLM prompt
- **How**: LLM sees actual table/column names
- **Result**: Better filters and parameter definitions

### 3️⃣ Parallel Execution
- **What**: Use asyncio.gather() instead of sequential
- **How**: Execute multiple tools simultaneously
- **Result**: 2x faster response time for 2 tools

---

## Implementation Roadmap

### Phase 1: Plan Schema (TODAY) ⭐ HIGH PRIORITY
```
[ ] Read docs/PHASE1_IMPLEMENTATION.md
[ ] Add tool_type field to all Specs in plan_schema.py
[ ] Write unit tests for tool_type
[ ] Run tests: pytest test_plan_schema.py
[ ] Commit: "feat: Add tool_type field to Plan specifications"
Time: 2-4 hours | Difficulty: LOW | Risk: VERY LOW
```

### Phase 2: Tool Registry (NEXT WEEK) ⭐ HIGH PRIORITY
```
[ ] Add input_schema field to Tool class
[ ] Add get_tool_info() and get_all_tools_info() methods
[ ] Add validate_tool_type() method
[ ] Write tests
[ ] Commit: "feat: Enhance Tool Registry with info methods"
Time: 1 day | Difficulty: LOW | Risk: LOW
```

### Phase 3: Catalog Loading (NEXT WEEK)
```
[ ] Add load_catalog_for_source() function
[ ] Add catalog summarization logic
[ ] Add caching with @lru_cache
[ ] Write tests
[ ] Commit: "feat: Add catalog loading from Asset Registry"
Time: 1 day | Difficulty: MEDIUM | Risk: LOW
```

### Phase 4: Planner Prompt (NEXT WEEK) ⭐ HIGH PRIORITY
```
[ ] Modify build_planner_prompt() to accept tools_info
[ ] Modify build_planner_prompt() to accept catalog_info
[ ] Add formatting helper functions
[ ] Update LLM prompt text
[ ] Modify plan_llm_query() to load and pass context
[ ] Add Plan validation with _validate_plan()
[ ] Write tests
[ ] Commit: "feat: Enhance Planner Prompt with tools & catalog info"
Time: 1-2 days | Difficulty: MEDIUM | Risk: MEDIUM
```

### Phase 5: Parallel Execution (NEXT WEEK) ⭐ HIGH PRIORITY
```
[ ] Modify _execute_execute() to read tool_type from Plan
[ ] Remove hardcoded tool_type values
[ ] Implement asyncio.gather() for parallel execution
[ ] Add _execute_tool_async() helper
[ ] Add error handling for parallel tasks
[ ] Write tests
[ ] Commit: "feat: Implement parallel tool execution with asyncio.gather"
Time: 1 day | Difficulty: MEDIUM | Risk: MEDIUM
```

### Phase 6: Testing (WEEK 2)
```
[ ] Write comprehensive unit tests
[ ] Write integration tests
[ ] Write E2E tests
[ ] Test backward compatibility
[ ] Commit: "test: Add comprehensive tests for tool selection"
Time: 2-3 days | Difficulty: MEDIUM | Risk: LOW
```

### Phase 7: Documentation (WEEK 2)
```
[ ] Update API documentation
[ ] Update deployment guide
[ ] Update tool registry documentation
[ ] Commit: "docs: Update documentation for tool selection feature"
Time: 1 day | Difficulty: LOW | Risk: NONE
```

### Phase 8: Performance (ONGOING)
```
[ ] Benchmark parallel vs sequential
[ ] Optimize catalog loading
[ ] Optimize prompt size
[ ] Monitor performance metrics
Time: Ongoing | Difficulty: MEDIUM | Risk: LOW
```

---

## Quick Start: Phase 1

**If you want to start implementing immediately:**

1. **Read this** → `docs/PHASE1_IMPLEMENTATION.md` (15 minutes)
2. **Edit** → `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`
   - Add `tool_type` field to each Spec class
3. **Test** → Run `pytest apps/api/tests/test_plan_schema.py -v`
4. **Commit** → Use provided commit message from Phase 1 doc

That's it! Phase 1 should take 2-4 hours.

---

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────┐
│ User: "Show CPU usage for production servers"       │
└────────────────┬─────────────────────────────────────┘
                 │
      ┌──────────▼──────────┐
      │ Load Context:       │
      │ • Tools Info        │
      │ • Tool Schemas      │
      │ • Catalog Info      │
      └──────────┬──────────┘
                 │
      ┌──────────▼──────────────────────────────┐
      │ Planner LLM (with full context)        │
      │ → Decides: Which tools? What params?   │
      └──────────┬──────────────────────────────┘
                 │
      ┌──────────▼────────────────────────────┐
      │ Plan {                                 │
      │   primary: {tool_type: "ci_lookup"}   │
      │   metric: {tool_type: "metric_query"} │
      │ }                                      │
      └──────────┬────────────────────────────┘
                 │
      ┌──────────▼──────────────────────┐
      │ Execute Stage (parallel!)       │
      │ Task 1: ci_lookup [100ms]      │
      │ Task 2: metric_query [100ms]   │
      │ Total: ~100ms (not 200!)       │
      └──────────┬──────────────────────┘
                 │
      ┌──────────▼────────────────────┐
      │ Results to User               │
      │ Response Time: 2x Faster!     │
      └───────────────────────────────┘
```

---

## Key Files to Understand

### Before You Start Coding

Read these to understand the current structure:

1. **Plan Schema**
   - `apps/api/app/modules/ops/services/ci/planner/plan_schema.py`
   - Lines 1-100: Spec classes that need tool_type

2. **Stage Executor**
   - `apps/api/app/modules/ops/services/ci/orchestrator/stage_executor.py`
   - Lines 300-400: _execute_execute() method that needs modification

3. **Planner LLM**
   - `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`
   - Lines 50-150: build_planner_prompt() function
   - Lines 200-300: plan_llm_query() function

4. **Tool Registry**
   - `apps/api/app/modules/ops/services/ci/tools/registry.py`
   - Tool class and ToolRegistry class

5. **Catalog Models**
   - `apps/api/app/modules/asset_registry/schema_models.py`
   - SchemaColumn, SchemaTable, SchemaCatalog classes

---

## Success Criteria

After complete implementation, verify:

- ✅ All existing tests pass (backward compatibility)
- ✅ Plan JSON includes tool_type field
- ✅ LLM selects valid tool_type from available tools
- ✅ Invalid tool_type values are caught and corrected
- ✅ Parallel execution works (verify with timing tests)
- ✅ Catalog information loads correctly
- ✅ Prompt includes tools & catalog information
- ✅ E2E test passes: Query → Plan → Execution → Results
- ✅ No performance regression in single-tool scenarios
- ✅ Documentation is updated

---

## Risk Mitigation Summary

| Risk | Severity | Mitigation |
|------|----------|-----------|
| LLM selects invalid tool | Medium | Validation + defaults |
| Catalog too large | Medium | Summarization + pagination |
| Parallel execution fails | Low | Error handling + fallback |
| Performance regression | Low | Benchmarking + optimization |
| Backward compatibility | Low | Default values in all fields |

---

## Testing Strategy

### Unit Tests (Phase 1-2)
- Tool_type field defaults
- Tool validation
- Catalog loading

### Integration Tests (Phase 4-5)
- Planner with tools info
- LLM returns valid tool_type
- Parallel execution timing

### E2E Tests (Phase 6)
- Full query → plan → execution → results
- Multiple tool selections
- Error scenarios

### Performance Tests (Phase 8)
- Parallel vs sequential timing
- Catalog loading performance
- Token usage monitoring

---

## Document Reference Map

```
Start Here
    │
    ├─→ docs/SUMMARY.md (5-10 min read)
    │   Quick overview of what, why, how
    │
    ├─→ docs/ARCHITECTURE_DIAGRAM.md (15-20 min read)
    │   Visual understanding of system flow
    │
    ├─→ docs/CATALOG_TO_LLM_ARCHITECTURE.md (30-40 min read)
    │   Technical details and data structures
    │
    ├─→ docs/IMPLEMENTATION_CHECKLIST.md (60+ min read)
    │   Complete reference with all phases
    │
    └─→ docs/PHASE1_IMPLEMENTATION.md (when ready to code)
        Concrete code changes and testing
```

---

## Getting Help

If you have questions while implementing:

1. **Understanding the flow?**
   - Read: `ARCHITECTURE_DIAGRAM.md`

2. **Need to know what data structure?**
   - Read: `CATALOG_TO_LLM_ARCHITECTURE.md` → Section 3

3. **How do I implement Phase X?**
   - Read: `IMPLEMENTATION_CHECKLIST.md` → Phase X section

4. **Ready to code Phase 1?**
   - Read: `PHASE1_IMPLEMENTATION.md`

5. **Need sample code?**
   - Check: `CATALOG_TO_LLM_ARCHITECTURE.md` → Section 4-6

---

## Implementation Timeline

| Phase | Duration | Priority | Status |
|-------|----------|----------|--------|
| 1: Plan Schema | 1 day | HIGH | ⏳ TODO |
| 2: Tool Registry | 1 day | HIGH | ⏳ TODO |
| 3: Catalog Loading | 1 day | MEDIUM | ⏳ TODO |
| 4: Planner Prompt | 1-2 days | HIGH | ⏳ TODO |
| 5: Parallel Exec | 1 day | HIGH | ⏳ TODO |
| 6: Testing | 2-3 days | MEDIUM | ⏳ TODO |
| 7: Documentation | 1 day | MEDIUM | ⏳ TODO |
| 8: Optimization | Ongoing | LOW | ⏳ TODO |
| **Total** | **8-10 days** | | |

---

## Next Action

**Start now:**

1. Read `docs/SUMMARY.md` (5 minutes)
2. Read `docs/PHASE1_IMPLEMENTATION.md` (15 minutes)
3. Follow Phase 1 checklist (2-4 hours)

**That's it! You'll have the first piece done today.**

Then move to Phase 2 next week.

---

## Key Insights to Remember

From your analysis:
- ✅ "LLM이 tool을 선택하고" → Phase 1, 4, 5
- ✅ "catalog 정보를 받아서" → Phase 3, 4
- ✅ "parameters를 정의해야 한다" → Phase 4
- ✅ "병렬로 진행하는 것이겠구나" → Phase 5

You've identified exactly what needs to be done. These documents provide the complete roadmap to implement it.

---

## Document Maintenance

All documents are stored in `/home/spa/tobit-spa-ai/docs/`:
- `SUMMARY.md` - Overview (this level)
- `ARCHITECTURE_DIAGRAM.md` - Visuals
- `CATALOG_TO_LLM_ARCHITECTURE.md` - Technical specs
- `IMPLEMENTATION_CHECKLIST.md` - Detailed checklists
- `PHASE1_IMPLEMENTATION.md` - Phase 1 code
- `README_IMPLEMENTATION.md` - This file

As you implement, you can update these docs with:
- Actual code snippets tested
- Performance benchmarks
- Known issues and solutions
- Lessons learned

---

## 🎯 Ready to Start?

1. Open `docs/PHASE1_IMPLEMENTATION.md`
2. Follow the checklist
3. Implement Phase 1
4. Run tests
5. Commit
6. Move to Phase 2

**Let's make the system truly dynamic!**
