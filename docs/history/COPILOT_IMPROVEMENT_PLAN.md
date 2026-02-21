# Copilot Improvement Plan - All 4 Modules

## Overview

This document outlines a comprehensive plan to improve AI Copilot functionality across all 4 modules:
- CEP Builder
- API Manager
- SIM (Simulation)
- Screen Editor

## Current State Analysis

### CEP Builder (apps/web/src/app/cep-builder/page.tsx)
- **Frontend Copilot**: ChatExperience with SSE streaming
- **Context Passed**: Only `rule_id`, `rule_name`, `trigger_type` (metadata only)
- **Missing**: `trigger_spec`, `action_spec`, `conditions`, `actions`, `windowing`, `aggregation`
- **Backend**: No dedicated CEP copilot service

### API Manager (apps/web/src/app/api-manager/page.tsx)
- **Frontend Copilot**: ChatExperience with SSE streaming
- **Context Passed**: Only `api_id`, `api_name`, `method`, `endpoint`, `logic_type`
- **Missing**: `logic_body`, `param_schema`, `runtime_policy`, `logic_spec`
- **Backend**: `/ai/api-copilot` exists but NOT utilized by frontend

### SIM (apps/web/src/app/sim/page.tsx)
- **Frontend Copilot**: ChatExperience with SSE streaming
- **Context Passed**: `question`, `scenario_type`, `strategy`, `horizon`, `service`, `assumptions`, `latest_summary`, `latest_kpis`
- **Status**: Best context passing among 4 modules
- **Missing**: Backend copilot service, analysis mode (only JSON generation)

### Screen Editor (apps/web/src/components/admin/screen-editor/ScreenEditor.tsx)
- **Frontend Copilot**: ChatExperience (limited context)
- **Context Passed**: Only `screen_id`, `name`, `layout_type`, `component_count`
- **Backend**: `/ai/screen-copilot` with FULL schema passing (in separate CopilotPanel.tsx)
- **Issue**: Two copilot paths not integrated

---

## P0: Full Context Passing (Critical)

### P0.1 CEP Builder - Pass Full Rule Context

**File**: `apps/web/src/app/cep-builder/page.tsx`

**Current** (Line ~1307-1324):
```typescript
copilotBuilderContext = {
  selected_rule: { rule_id, rule_name, trigger_type },
  draft_status,
  active_tab,
  current_form: { rule_name, trigger_type }
}
```

**Target**:
```typescript
copilotBuilderContext = {
  selected_rule: selectedRule ? {
    rule_id: selectedRule.rule_id,
    rule_name: selectedRule.rule_name,
    trigger_type: selectedRule.trigger_type,
    trigger_spec: selectedRule.trigger_spec,
    action_spec: selectedRule.action_spec,
    is_active: selectedRule.is_active
  } : null,
  draft_status,
  active_tab,
  current_form: {
    rule_name: ruleName,
    trigger_type: triggerType,
    trigger_spec: triggerSpec,
    conditions: conditions,
    windowing: windowing,
    aggregation: aggregation,
    actions: actions
  },
  selected_condition_id: selectedConditionId,
  selected_action_id: selectedActionId
}
```

### P0.2 API Manager - Pass Full API Context

**File**: `apps/web/src/app/api-manager/page.tsx`

**Current** (Line ~2513-2542):
```typescript
copilotBuilderContext = {
  selected_api: { api_id, api_name, method, endpoint, logic_type },
  draft_status,
  active_tab,
  form_snapshot: { api_name, method, endpoint, logic_type }
}
```

**Target**:
```typescript
copilotBuilderContext = {
  selected_api: selectedApi ? {
    api_id: selectedApi.api_id,
    api_name: selectedApi.api_name,
    method: selectedApi.method,
    endpoint: selectedApi.endpoint,
    logic_type: selectedApi.logic_type,
    logic_body: selectedApi.logic_body,
    param_schema: selectedApi.param_schema,
    runtime_policy: selectedApi.runtime_policy,
    description: selectedApi.description,
    tags: selectedApi.tags
  } : null,
  draft_status,
  active_tab,
  form_snapshot: {
    api_name: definitionDraft.api_name,
    method: definitionDraft.method,
    endpoint: definitionDraft.endpoint,
    logic_type: logicType,
    logic_body: logicType === 'sql' ? sqlQuery : httpSpec,
    param_schema: paramSchema,
    runtime_policy: runtimePolicy
  }
}
```

### P0.3 SIM - Add Analysis Mode

**File**: `apps/web/src/app/sim/page.tsx`

**Current Prompt** (Line ~159-167):
```
Output must be a single JSON object: {"type":"sim_draft","draft":{...}}.
```

**Target Prompt**:
```
You are Tobit SIM Workspace AI Copilot with two modes:

1. DRAFT MODE: When user wants to create/modify simulation parameters
   Output: {"type":"sim_draft","draft":{question,scenario_type,strategy,horizon,service,assumptions}}

2. ANALYSIS MODE: When user asks about results, wants explanation, or insights
   Output: {"type":"sim_analysis","analysis":{summary,key_findings,recommendations,anomalies,comparison_with_baseline}}

Current simulation results (if any):
- latest_summary: ...
- latest_kpis: ...

Always respond in the same language as the user.
```

### P0.4 Screen Editor - Integrate Backend Copilot

**File**: `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx`

**Current**: Uses `BuilderCopilotPanel` → `ChatExperience` (limited context)

**Target**: Create new `ScreenEditorCopilotPanel` that calls `/ai/screen-copilot`

Or modify `BuilderCopilotPanel` to optionally use backend API.

---

## P1: Backend Services & Incremental Modification

### P1.1 CEP Backend Copilot Service

**New File**: `apps/api/app/modules/ai/cep_copilot_service.py`

**Endpoints**:
- `POST /ai/cep-copilot` - Generate/improve CEP rules
- `POST /ai/cep-copilot/validate` - Validate CEP rule

**Service**:
```python
class CepCopilotService:
    async def generate_rule(
        self,
        request: CepCopilotRequest
    ) -> CepCopilotResponse:
        # Full rule context passed
        # Returns: rule_draft, explanation, confidence, suggestions
```

### P1.2 SIM Backend Copilot Service

**New File**: `apps/api/app/modules/ai/sim_copilot_service.py`

**Endpoints**:
- `POST /ai/sim-copilot` - Generate simulation parameters
- `POST /ai/sim-copilot/analyze` - Analyze simulation results

### P1.3 Incremental Modification (Patch Mode)

**CEP & SIM**: Add `mode: "patch"` support similar to API Manager

**Contract**:
```json
{
  "type": "cep_draft",
  "mode": "patch",
  "patch": [
    {"op": "replace", "path": "/trigger_spec/threshold", "value": 90}
  ],
  "notes": "Increased threshold to 90%"
}
```

### P1.4 API Manager - Connect to Backend

**File**: `apps/web/src/app/api-manager/page.tsx`

Add option to use `/ai/api-copilot` backend instead of frontend ChatExperience.

---

## P2: UI Consistency & Onboarding

### P2.1 Unified Copilot Response Display

**New Component**: `apps/web/src/components/copilot/CopilotResponseDisplay.tsx`

```typescript
interface CopilotResponseDisplayProps {
  explanation?: string;
  confidence?: number;
  suggestions?: string[];
  warnings?: string[];
  errors?: string[];
}
```

### P2.2 Example Prompts UI

**CEP**: Add clickable example prompts from `CEP_COPILOT_EXAMPLE_PROMPTS`
**API Manager**: Add example prompts for SQL/HTTP/Python generation
**Screen Editor**: Add quick action buttons (already exists in CopilotPanel.tsx)

### P2.3 Onboarding Tours

**New Files**:
- `apps/web/src/components/cep-builder/OnboardingTour.tsx`
- `apps/web/src/components/api-manager/OnboardingTour.tsx`

---

## P3: Multi-turn Conversation Context

### P3.1 Conversation History in Context

**All Modules**: Pass last N messages to LLM for context

```typescript
copilotBuilderContext = {
  // ... existing context
  conversation_summary: lastFewMessages.map(m => ({
    role: m.role,
    content_summary: m.content.substring(0, 200)
  }))
}
```

### P3.2 Draft History Tracking

**CEP & SIM**: Track draft versions within session for "go back" functionality

---

## Implementation Order

### Phase 1 (P0) - Parallel Implementation
1. CEP: Full context passing
2. API Manager: Full context passing
3. SIM: Analysis mode prompt
4. Screen Editor: Backend integration

### Phase 2 (P1) - Sequential Implementation
1. CEP Backend Copilot Service
2. SIM Backend Copilot Service
3. API Manager backend connection
4. Patch mode support

### Phase 3 (P2) - Shared Components
1. CopilotResponseDisplay component
2. Example prompts UI
3. Onboarding tours

### Phase 4 (P3) - Conversation Enhancement
1. Multi-turn context
2. Draft history

---

## Testing Plan

### Unit Tests
- Context passing functions
- Contract validation
- Patch application

### Integration Tests
- Frontend → Backend copilot flow
- Draft → Apply → Save flow
- Error handling

### End-to-End Tests
- Each module: Create → Modify with Copilot → Apply → Save
- Cross-module: Verify no regressions

---

## Files to Modify/Create

### P0 Files
1. `apps/web/src/app/cep-builder/page.tsx` - Context passing
2. `apps/web/src/app/api-manager/page.tsx` - Context passing
3. `apps/web/src/app/sim/page.tsx` - Analysis mode prompt
4. `apps/web/src/components/admin/screen-editor/ScreenEditor.tsx` - Backend integration

### P1 Files
1. `apps/api/app/modules/ai/cep_copilot_service.py` (NEW)
2. `apps/api/app/modules/ai/cep_copilot_schemas.py` (NEW)
3. `apps/api/app/modules/ai/cep_copilot_prompts.py` (NEW)
4. `apps/api/app/modules/ai/sim_copilot_service.py` (NEW)
5. `apps/api/app/modules/ai/sim_copilot_schemas.py` (NEW)
6. `apps/api/app/modules/ai/sim_copilot_prompts.py` (NEW)
7. `apps/api/app/modules/ai/router.py` - Add new endpoints

### P2 Files
1. `apps/web/src/components/copilot/CopilotResponseDisplay.tsx` (NEW)
2. `apps/web/src/components/cep-builder/ExamplePrompts.tsx` (NEW)
3. `apps/web/src/components/api-manager/ExamplePrompts.tsx` (NEW)

### P3 Files
1. `apps/web/src/lib/copilot/conversation-context.ts` (NEW)
