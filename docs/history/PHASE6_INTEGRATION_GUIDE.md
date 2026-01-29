# Phase 6 Integration Guide - Add Orchestration Visualization to Inspector

## Quick Start: 3 Steps to Enable Orchestration Visualization

### Step 1: Install React Flow Dependency (If Not Already Installed)

```bash
cd /home/spa/tobit-spa-ai/apps/web
npm install reactflow
```

### Step 2: Update Inspector Page

Edit: `apps/web/src/app/admin/inspector/page.tsx`

**Add import at the top of the file:**

```typescript
import { OrchestrationSection } from '@/components/ops/OrchestrationSection';
```

**Add the orchestration section in the detail drawer:**

Find the existing "Flow" section (around line 1462) and add this after it:

```typescript
{/* Orchestration Section */}
{traceDetail && (
  <OrchestrationSection stageOutput={traceDetail} />
)}
```

### Step 3: Test

1. Go to Inspector page in admin dashboard
2. Select a trace with orchestration enabled
3. Should see new "Orchestration" section with:
   - Strategy badge (PARALLEL/SERIAL/DAG)
   - Execution groups and tools
   - Timeline and Graph view toggle
   - Tool details panel

---

## What Gets Displayed

### Timeline View (Default)
Shows execution groups organized hierarchically:
```
┌─ Group 0 (Parallel)
│  ├─ primary (ci_lookup)
│  └─ secondary (ci_lookup)
│
└─ Group 1 (Sequential)
   └─ aggregate (ci_aggregate) → Depends on: primary, secondary
```

### Graph View
Interactive dependency graph showing:
- Tool nodes positioned by group and dependencies
- Animated edges showing data flow
- Click to select tools and see details

### Tool Details
When a tool is selected, shows:
- Tool type
- Dependencies (which tools must complete first)
- Data flow mappings (input/output specifications)
- Execution group assignment

---

## Example Traces

### PARALLEL Execution
All tools execute simultaneously, no dependencies:
```json
{
  "strategy": "parallel",
  "execution_groups": [
    {
      "group_index": 0,
      "tools": [
        {
          "tool_id": "primary",
          "tool_type": "ci_lookup",
          "depends_on": [],
          "dependency_groups": [],
          "output_mapping": {}
        },
        {
          "tool_id": "secondary",
          "tool_type": "ci_lookup",
          "depends_on": [],
          "dependency_groups": [],
          "output_mapping": {}
        }
      ],
      "parallel_execution": true
    }
  ],
  "total_groups": 1,
  "total_tools": 2
}
```

### SERIAL Execution
Tools execute sequentially with data flow:
```json
{
  "strategy": "serial",
  "execution_groups": [
    {
      "group_index": 0,
      "tools": [
        {
          "tool_id": "primary",
          "tool_type": "ci_lookup",
          "depends_on": [],
          "dependency_groups": [],
          "output_mapping": {}
        }
      ],
      "parallel_execution": false
    },
    {
      "group_index": 1,
      "tools": [
        {
          "tool_id": "aggregate",
          "tool_type": "ci_aggregate",
          "depends_on": ["primary"],
          "dependency_groups": [0],
          "output_mapping": {
            "ci_type_filter": "{primary.data.rows[0].ci_type}"
          }
        }
      ],
      "parallel_execution": false
    }
  ],
  "total_groups": 2,
  "total_tools": 2
}
```

### DAG Execution
Complex with multiple branches and convergence:
```json
{
  "strategy": "dag",
  "execution_groups": [
    {
      "group_index": 0,
      "tools": [
        {"tool_id": "primary", ...},
        {"tool_id": "secondary", ...}
      ],
      "parallel_execution": true
    },
    {
      "group_index": 1,
      "tools": [
        {
          "tool_id": "aggregate",
          "depends_on": ["primary", "secondary"],
          "dependency_groups": [0],
          ...
        }
      ],
      "parallel_execution": false
    }
  ],
  "total_groups": 2,
  "total_tools": 3
}
```

---

## Component Files Reference

### OrchestrationVisualization.tsx
- **Location**: `apps/web/src/components/ops/OrchestrationVisualization.tsx`
- **Purpose**: Timeline view with expandable groups
- **Exports**: `OrchestrationVisualization` component
- **Props**: trace, expandedGroups, onGroupToggle, selectedTool, onToolSelect

### OrchestrationDependencyGraph.tsx
- **Location**: `apps/web/src/components/ops/OrchestrationDependencyGraph.tsx`
- **Purpose**: React Flow-based dependency graph
- **Exports**: `OrchestrationDependencyGraph` component
- **Props**: trace, selectedTool, onToolSelect

### OrchestrationSection.tsx
- **Location**: `apps/web/src/components/ops/OrchestrationSection.tsx`
- **Purpose**: Inspector drawer integration (wrapper)
- **Exports**: `OrchestrationSection` component
- **Props**: stageOutput
- **Features**: View toggle, tool details panel

### orchestrationTraceUtils.ts
- **Location**: `apps/web/src/lib/orchestrationTraceUtils.ts`
- **Purpose**: Utility functions for trace handling
- **Key Functions**:
  - `extractOrchestrationTrace(stageOutput)` - Extract trace
  - `isValidOrchestrationTrace(obj)` - Validate trace
  - `getStrategyDescription(strategy)` - Get description
  - `getStrategyBadge(strategy)` - Get badge info
  - `generateOrchestrationReport(trace)` - Generate text report

---

## Troubleshooting

### Orchestration Section Not Appearing

**Check**:
1. Backend is returning `orchestration_trace` in stage output
2. Trace structure matches expected format
3. Browser console for errors

**Debug**:
```typescript
// In browser console, after loading trace:
const trace = traceDetail.orchestration_trace;
console.log('Orchestration trace:', trace);
console.log('Is valid:', isValidOrchestrationTrace(trace));
```

### React Flow Not Loading

**Error**: "ReactFlow is not defined"

**Solution**:
1. Install reactflow: `npm install reactflow`
2. Verify import in component
3. Rebuild Next.js: `npm run build`

### Graphs Not Rendering Correctly

**Check**:
1. CSS for ReactFlow is loaded
2. Container has proper dimensions (500px height)
3. Trace has valid execution_groups

**Debug**:
```typescript
// Check trace structure
console.log(JSON.stringify(trace, null, 2));
```

---

## Customization Options

### Change Graph View Height

Edit `OrchestrationDependencyGraph.tsx`:
```typescript
// Line 65 - change height
<div className="w-full h-[500px] rounded-lg ...">
```

### Customize Colors

Edit `OrchestrationVisualization.tsx` or utility functions:
```typescript
const strategyColor = {
  'parallel': 'bg-emerald-900/40 text-emerald-200 border-emerald-400/50',
  'serial': 'bg-amber-900/40 text-amber-200 border-amber-400/50',
  'dag': 'bg-blue-900/40 text-blue-200 border-blue-400/50',
};
```

### Add Custom Tool Type Colors

Edit `orchestrationTraceUtils.ts`, function `getToolTypeColor()`:
```typescript
case 'my_custom_tool':
  return {
    bg: 'bg-pink-900/20',
    border: 'border-pink-400/50',
    text: 'text-pink-300',
  };
```

---

## Backend Requirements

For orchestration visualization to work, backend must:

1. **Generate execution plan trace** in ToolOrchestrator:
   ```python
   trace = orchestrator._create_execution_plan_trace(dependencies, strategy)
   ```

2. **Return trace in stage output**:
   ```python
   return {
       "execution_results": results,
       "orchestration_trace": {
           "strategy": plan.execution_strategy.value,
           "execution_plan": execution_plan,
       }
   }
   ```

3. **Structure matches expected format** (see Type Definitions below)

---

## Type Definitions

### OrchestrationTrace
```typescript
interface OrchestrationTrace {
  strategy: 'parallel' | 'serial' | 'dag';
  execution_groups: ExecutionGroup[];
  total_groups: number;
  total_tools: number;
  tool_ids: string[];
  error?: string;
}
```

### ExecutionGroup
```typescript
interface ExecutionGroup {
  group_index: number;
  tools: Tool[];
  parallel_execution: boolean;
}
```

### Tool
```typescript
interface Tool {
  tool_id: string;
  tool_type: string;
  depends_on: string[];
  dependency_groups: number[];
  output_mapping: Record<string, string>;
}
```

---

## Performance Tips

1. **Large Traces**: For traces with 20+ tools, consider pagination
2. **Graph View**: Disable for very large traces (50+ tools)
3. **Local Storage**: Cache expanded state to improve UX

### Implement Caching:
```typescript
const [expandedGroups, setExpandedGroups] = useState(() => {
  const saved = localStorage.getItem('orchestration-expanded');
  return saved ? JSON.parse(saved) : [];
});

const handleGroupToggle = (groupIndex: number) => {
  const updated = /* toggle logic */;
  localStorage.setItem('orchestration-expanded', JSON.stringify(updated));
  setExpandedGroups(updated);
};
```

---

## Support & Documentation

- **Full Implementation Guide**: `PHASE6_INSPECTOR_UI_IMPLEMENTATION.md`
- **Phase 5 Backend Guide**: `PHASE5_INSPECTOR_INTEGRATION_COMPLETE.md`
- **Orchestration Quick Reference**: `ORCHESTRATION_TRACE_QUICK_REFERENCE.md`
- **Utility Functions**: Inline documentation in `orchestrationTraceUtils.ts`

---

## Next Steps

1. ✅ Install reactflow
2. ✅ Update inspector/page.tsx
3. ✅ Test with real traces
4. ✅ Customize colors/layout as needed
5. 📋 Phase 7: Advanced features (conditional execution, loops, etc.)

---

**Integration Status**: Ready to Deploy

**Estimated Integration Time**: 5-10 minutes

**Complexity**: Low (3 files, minimal changes)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
