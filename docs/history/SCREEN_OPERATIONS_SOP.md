# Screen Operations Standard Operating Procedure (SOP)

## Overview

This SOP provides operational guidelines for managing UI Creator Screens as production assets through their complete lifecycle: **Draft → Preview → Diff → Publish Gate → Regression → Rollback**.

**Document Version**: 1.0 (U3-2 Production)
**Last Updated**: 2026-01-19
**Audience**: Operations Engineers, Screen Operators, DevOps Teams

---

## 1. Screen Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SCREEN LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. CREATION              2. EDITING              3. VALIDATION          │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Create Screen│  │ Visual Editor    │  │ JSON Validation         │   │
│  │ (3 templates)│→ │ JSON Editor      │→ │ Preview Tab             │   │
│  │ or Blank     │  │ Component ops    │  │ (live rendering)        │   │
│  └──────────────┘  └──────────────────┘  └──────────────────────────┘   │
│                           ↓                                              │
│  6. ROLLBACK           4. DIFF REVIEW           5. PUBLISH GATE         │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Revert to    │  │ Draft vs         │  │ 4-Step Validation:      │   │
│  │ Previous     │← │ Published Diff   │← │ 1. Schema Validation    │   │
│  │ Version      │  │ Component-level  │  │ 2. Binding Validation   │   │
│  │ (+ Regress)  │  │ Action-level     │  │ 3. Action Validation    │   │
│  └──────────────┘  │ State-level      │  │ 4. Dry-Run Test         │   │
│                    │ Binding-level    │  │ → Publish (if pass)     │   │
│                    └──────────────────┘  └──────────────────────────┘   │
│                           ↑                           ↓                  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  7. REGRESSION TESTING (Post-Publish)                              │ │
│  │  └─ Run automated golden queries                                   │ │
│  │  └─ View execution traces in Inspector                            │ │
│  │  └─ Verify screen behavior matches expectations                   │ │
│  │  └─ If issues found: Proceed to Step 6 (Rollback)                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Operational Procedures

### Phase 1: Screen Creation

#### Purpose
Create a new screen asset, optionally starting from a pre-built template to accelerate development.

#### Procedure

1. **Navigate to Screens Panel**
   - URL: `/admin/screens`
   - Click **"+ Create Screen"** button

2. **Choose Template** (Optional)
   - **Blank**: Start with empty screen
   - **Read-only Detail**: Device/entity information display (state fields auto-bound)
   - **List + Filter**: Searchable data grid with filtering
   - **List + Modal CRUD**: Full CRUD with create/edit modal and actions

3. **Fill Screen Metadata**
   - **Screen ID** (required): Unique identifier (e.g., `device_dashboard`, `user_list_v2`)
     - Format: `snake_case`, no spaces
     - Used for asset registry and filtering
   - **Screen Name** (required): Human-readable title (e.g., "Device Dashboard")
   - **Description** (optional): Brief purpose (e.g., "Main dashboard for device monitoring")

4. **Create**
   - Click **"Create"** button
   - Screen is created in **DRAFT** status
   - Automatically navigates to Screen Editor

#### Best Practices

✅ **DO**:
- Use descriptive screen IDs (e.g., `device_detail_v2` instead of `screen_1`)
- Start with templates for common patterns (saves 80% dev time)
- Name screens after their primary use case

❌ **DON'T**:
- Use generic IDs without context
- Create screens without clear purpose
- Reuse screen IDs (use version suffix instead)

---

### Phase 2: Visual & JSON Editing

#### Purpose
Build screen components, define state schema, create bindings and actions.

#### Tabs Available

| Tab | Purpose | When to Use |
|-----|---------|------------|
| **Visual Editor** | Drag-drop component building | Initial screen building |
| **JSON** | Direct schema editing | Advanced configurations, debugging |
| **Preview** | Live rendering | Before publish, test interactions |
| **Diff** | Change comparison (NEW) | Review vs published version |

#### Visual Editor Workflow

1. **Add Components**
   - Click **"Add Component"**
   - Select type: Text, Input, Button, DataGrid, Modal, etc.
   - Component appears in canvas

2. **Configure Component**
   - Click component in canvas
   - **Properties Panel** (right side) appears:
     - **Label**: Display name in editor
     - **Props**: Component-specific properties
     - **Bindings**: Bind props to {{state.field}}
     - **Actions**: Attach handlers (http_request, set_state, etc.)
     - **Visibility**: Conditional display ({{state.modal_open}})

3. **Add Bindings**
   - Click **"Bindings"** tab in Properties Panel
   - For each property (text, value, open, etc.):
     - Choose **"Binding"** mode (vs Static)
     - Use **Path Picker** dropdown to select:
       - `state.*` fields from schema
       - `context.*` inputs
       - `inputs.*` parameters
       - `trace_id` (special)
     - Example: Text component `text` property → `{{state.device_name}}`

4. **Add Actions**
   - Click component (usually Button)
   - Click **"Actions"** tab in Properties Panel
   - Click **"Add Action"**
   - ActionEditorModal opens:
     - **Action ID**: Unique name (auto-generated)
     - **Handler**: Type of action (http_request, set_state, run_workflow)
     - **Payload Template**: Key-value pairs (can use bindings)
     - **Test Action**: Execute action in draft mode (shows result in Inspector)

5. **Define State Schema**
   - Screen level: Click **"State"** section
   - Define fields:
     - `device_id: string`
     - `device_name: string`
     - `items: array`
     - `modal_open: boolean`
   - Set initial values for preview

#### Example: Device Detail Screen

```json
Screen Structure:
├─ Title (Text) → text: "{{state.device_name}}"
├─ ID Field (Text) → text: "{{state.device_id}}"
├─ Status Button (Button) → onClick: set_state {status: "active"}
│  └─ Visibility: {{state.admin_mode}}
└─ Edit Modal (Modal) → open: "{{state.modal_open}}"
   ├─ Name Input → value: "{{state.form_name}}"
   ├─ Save Button → onClick: http_request POST /devices
   └─ Cancel Button → onClick: set_state {modal_open: false}

State Schema:
{
  device_id: "string",
  device_name: "string",
  status: "string",
  admin_mode: "boolean",
  modal_open: "boolean",
  form_name: "string"
}
```

#### Best Practices

✅ **DO**:
- Use consistent state field naming (`snake_case`)
- Keep components organized (group related items)
- Test bindings early with Preview tab
- Use Path Picker (no manual {{}} typing)

❌ **DON'T**:
- Create typos in binding paths ({{state.deviceid}} vs {{state.device_id}})
- Leave state schema incomplete
- Use dynamic component IDs

---

### Phase 3: Preview & Testing

#### Purpose
Verify screen rendering and interactions before publishing.

#### Procedure

1. **Navigate to Preview Tab**
   - Click **"Preview"** tab in Screen Editor

2. **Verify Rendering**
   - All components display correctly
   - Layout matches design intent
   - Text bindings show actual state values

3. **Test Interactions**
   - Click buttons → Verify actions trigger
   - Fill inputs → Verify state updates
   - Open modals → Verify visibility conditions work

4. **Check State Changes**
   - Perform action (e.g., set_state)
   - Verify state displays updated values
   - Open Inspector link from toast if needed

5. **Test Edge Cases**
   - Empty state (no items in list)
   - Error conditions (invalid actions)
   - Conditional visibility (hide/show based on state)

#### Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Binding not rendering (shows {{state.x}}) | Path typo or missing state field | Check state schema, fix binding path |
| Action doesn't execute | Handler not registered or invalid payload | Check handler name, test with dummy values |
| Component not visible | Visibility condition false | Check visibility rule, update condition |
| Modal stuck open | set_state action not updating state | Verify action payload updates modal_open to false |

---

### Phase 4: Diff Review (NEW)

#### Purpose
Compare draft changes against the last published version before committing.

#### Procedure

1. **Navigate to Diff Tab**
   - Click **"Diff"** tab in Screen Editor

2. **Review Summary**
   - Top banner shows counts: `+5 added, -2 removed, ~3 modified, 10 unchanged`
   - Assess scope of changes

3. **Review Detailed Changes**
   - **Components Section**: Click to expand
     - 🟢 Green (added): New components
     - 🔴 Red (removed): Deleted components
     - 🟡 Yellow (modified): Changed properties
   - **Bindings Section**: Click to expand
     - Shows all {{}} expressions that changed
     - Highlights new/removed/modified bindings
   - **Actions Section**: Handlers and payloads
   - **State Schema**: Field additions/removals

4. **Assess Risk**
   - ✅ Low risk: Adding new components (no impact on existing)
   - ⚠️ Medium risk: Modifying existing bindings (verify correctness)
   - ⛔ High risk: Removing actions (test regression before publish)

5. **Proceed or Revise**
   - Diff looks good → **Proceed to Publish Gate**
   - Unexpected changes → **Revise in Visual Editor**

#### Example Diff Output

```
Components [4 items]
├─ + comp_new_button (added)
│  └─ type: Button, text: "Click Me"
├─ ~ comp_title (modified)
│  └─ text: "Old Title" → "New Title"
├─ - comp_old_input (removed)
│  └─ type: Input (no longer present)
└─ ○ comp_list (unchanged)
   └─ type: DataGrid

Bindings [6 items]
├─ + comp_new_button visibility.rule: {{state.admin}}
├─ ~ comp_title props.text: "static" → "{{state.title}}"
├─ - comp_old_input props.value: "{{state.old_field}}"
└─ ○ comp_list props.data: "{{state.items}}" (unchanged)

Actions [2 items]
├─ + action_save_device (added)
│  └─ handler: http_request, POST /api/devices
└─ ○ action_toggle_modal (unchanged)

State Schema [3 items]
├─ + admin: boolean (added)
├─ ~ items: array (unchanged)
└─ ○ device_id: string (unchanged)
```

#### Best Practices

✅ **DO**:
- Review Diff before publish (always)
- Pay attention to removed actions (verify no workflows broken)
- Check new bindings for typos
- Document rationale for large changes

❌ **DON'T**:
- Publish without reviewing Diff
- Make unintentional large changes
- Ignore warnings about removed bindings

---

### Phase 5: Publish with Validation Gate (NEW)

#### Purpose
Validate screen integrity before publishing; prevent invalid screens from reaching production.

#### Procedure

1. **Click "Publish" Button**
   - Top-right corner of editor
   - **PublishGateModal** opens
   - Message: "All checks must pass before publishing"

2. **Wait for Validation Checks**
   - Modal runs 4 checks automatically:
     1. **Schema Validation** (🟢 pass or 🔴 fail)
        - Validates ScreenSchemaV1 structure
        - Checks required fields present
     2. **Binding Validation** (🟢 pass or 🔴 fail)
        - Verifies all {{state.x}} paths exist in schema
        - Checks context.* and inputs.* availability
     3. **Action Validation** (🟢 pass or 🟡 warn)
        - Verifies handler names follow convention
        - Checks payload structure
     4. **Dry-Run Test** (🟢 pass or 🟡 warn)
        - Executes sample actions with test payload
        - Reports execution errors

3. **Fix Errors if Needed**
   - Status = 🔴 **FAIL**: Blocks publish
     - Example error: "Binding {{state.nonexistent}} not found"
     - Action: Return to Editor, fix the issue, retry
   - Status = 🟡 **WARN**: Allows publish with caution
     - Example warning: "Action handler follows non-standard naming"
     - Action: Review, then click "Publish" to proceed

4. **Publish**
   - Once all checks pass (or warnings only), **"Publish"** button is enabled
   - Click **"Publish"**
   - Screen transitions to **PUBLISHED** status
   - **Success Toast**: "Screen published successfully"

5. **See Regression Banner**
   - Blue banner appears: "Screen published. Run regression tests to verify?"
   - Two buttons:
     - **"View Traces"**: Opens Inspector (view execution history)
     - **"Run Regression (Recommended)"**: Navigates to regression page

#### Validation Detail: Common Errors

| Error | Cause | Resolution |
|-------|-------|-----------|
| Schema Validation: Components array empty | Screen has no components | Add at least one component |
| Binding Validation: {{state.device_id}} not found | state schema missing field | Add `device_id` to state schema |
| Action Validation: handler format invalid | Handler name has spaces/caps | Rename to `valid_handler_name` |
| Dry-Run Test: POST /api/endpoint failed | Backend endpoint unreachable | Check endpoint URL, verify API online |

#### Best Practices

✅ **DO**:
- Always review validation messages (they're actionable)
- Fix all FAIL (red) checks before publishing
- Understand what each WARN (yellow) means
- Re-test in Preview after fixing errors

❌ **DON'T**:
- Ignore validation errors and force publish
- Publish with unresolved bindings
- Deploy invalid screens to production

---

### Phase 6: Post-Publish Regression Testing (NEW)

#### Purpose
Verify screen behavior after publishing using automated regression suite and manual testing.

#### Procedure

1. **See Regression Banner** (after successful publish)
   - Top of editor: Blue banner with regression prompt
   - Click **"Run Regression (Recommended)"**

2. **Navigate to Regression Page**
   - URL: `/admin/regression?screen_id={screenId}`
   - Lists available golden queries (pre-built test scenarios)
   - Each query tests specific screen functionality

3. **Select Regression Tests**
   - Choose which golden queries to run
   - Example queries:
     - `device_detail_page_load`: Verify screen renders with sample device
     - `device_detail_edit_modal`: Verify edit modal opens/closes
     - `device_detail_state_binding`: Verify state updates reflected in UI

4. **Run Tests**
   - Click **"Run"** for each query
   - System executes predefined action sequence
   - Reports: ✅ Pass or ❌ Fail

5. **Review Results**
   - ✅ All Pass → Screen is production-ready
   - ❌ Any Fail → Proceed to Phase 7 (Rollback)

6. **View Execution Traces**
   - Each test run creates Inspector trace
   - Click **"View Traces"** (or banner "View Traces" button)
   - URL: `/admin/inspector?screen_id={screenId}`
   - Shows:
     - Action execution order
     - State changes
     - API responses
     - Error messages (if any)

#### Manual Regression Checklist

For critical screens, supplement automated tests with manual verification:

- [ ] Screen loads without errors
- [ ] All text bindings display correct values
- [ ] Buttons/inputs respond to user interaction
- [ ] Modals open/close as expected
- [ ] State updates visible in Preview
- [ ] Actions execute without errors
- [ ] Conditional visibility works (show/hide based on state)
- [ ] DataGrid displays correct data structure
- [ ] No console errors (open DevTools)

#### Troubleshooting Regression Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| No data displayed | API endpoint down | Check endpoint health, verify credentials |
| Binding shows {{state.x}} | Recent binding path change | Check updated Diff, verify state schema |
| Action fails | Payload mismatch | Check expected vs actual payload structure |
| Modal stuck | set_state action not triggered | Verify action in editor, test dry-run |

#### Best Practices

✅ **DO**:
- Always run regression after publish
- Document passing regression tests
- Investigate all failures before marking complete
- Keep trace links for audit trail

❌ **DON'T**:
- Skip regression testing
- Deploy without verifying automated tests
- Ignore warnings from dry-run tests

---

### Phase 7: Rollback Procedure (If Needed)

#### Purpose
Quickly revert to previous published version if issues are discovered post-publication.

#### When to Rollback
- ❌ Regression tests fail
- ❌ Critical binding errors detected
- ❌ User reports screen not working
- ❌ Action payloads cause downstream errors

#### Rollback Procedure

1. **Identify Issue**
   - Monitor regression results
   - Review execution traces in Inspector
   - Confirm root cause is screen-related (not downstream system)

2. **Navigate to Screen Editor**
   - URL: `/admin/screens/{screenId}`
   - Current status shows **PUBLISHED**
   - Previous version available (Draft)

3. **Click "Rollback to Draft"**
   - Red button, top-right
   - Confirmation dialog: "Revert to previous draft version?"
   - Click **"Confirm"**

4. **Verify Rollback**
   - Status changes to **DRAFT**
   - Published version automatically becomes previous snapshot
   - Diff tab now shows published version (what we just reverted to)

5. **Investigate & Fix**
   - Review what was published (Diff tab)
   - Edit and fix the issue
   - Re-save draft
   - Re-publish with validation gate

6. **Re-run Regression**
   - After re-publish, run regression again
   - Verify issue is fixed
   - Document resolution

#### Rollback Timeline

```
Timeline:
T=0:   Publish version 2.1 → Regression shows failures
T+5min: Discover issue in execution traces
T+10min: Decide to rollback
T+15min: Rollback to version 2.0 (draft restored)
T+20min: Fix issue in editor
T+25min: Re-publish with validation gate
T+30min: Re-run regression → All pass ✅
```

#### Best Practices

✅ **DO**:
- Keep previous versions for comparison
- Document why rollback occurred
- Use rollback as learning opportunity
- Implement fix and re-publish same day

❌ **DON'T**:
- Panic and rollback without investigation
- Make cascading changes after rollback without testing
- Rollback without re-testing

---

## 3. Common Operational Scenarios

### Scenario 1: Add New Field to Device Screen

**Request**: Show device location on device detail screen

**Steps**:
1. ✏️ Edit screen: Visual Editor → Add Text component
2. 📝 Set label binding: `{{state.device_location}}`
3. 🔧 Update state schema: Add `device_location: string`
4. 👁️ Preview tab: Verify displays correctly
5. 📊 Diff tab: Review change (1 component added, 1 binding added)
6. 🚀 Publish: Validation gate passes → Publish
7. 🧪 Regression: Run regression tests → All pass

**Timeline**: 10-15 minutes

---

### Scenario 2: Fix Typo in Button Label

**Request**: Button says "Submi" instead of "Submit"

**Steps**:
1. ✏️ Edit screen: Visual Editor → Select Button
2. 🔧 Change props.text: "Submi" → "Submit"
3. 👁️ Preview tab: Verify correct text
4. 📊 Diff tab: Review minimal change
5. 🚀 Publish: Validation gate passes → Publish
6. 🧪 Regression: Spot-check button in Preview

**Timeline**: 5 minutes

---

### Scenario 3: Add Edit Modal to List

**Request**: Users should be able to edit items from list

**Steps**:
1. 🎯 Start from "List + Modal CRUD" template
2. ✏️ Configure for specific data model
3. 🔧 Add bindings for form fields
4. 🧪 Test in Preview: Click row → Modal opens, form pre-fills
5. 📊 Diff vs blank: Review all changes
6. 🚀 Publish with validation
7. 🧪 Run regression: Edit, Save, Verify in traces

**Timeline**: 20-30 minutes

---

### Scenario 4: Production Issue - Action Fails

**Incident**: Users report "Save" button not working

**Investigation**:
1. 🔍 View Inspector traces: `/admin/inspector?screen_id=...`
2. 📋 Check recent action execution: See 500 error from API
3. 🔎 Confirm root cause: API endpoint changed, payload format wrong
4. 🚨 **Immediate action**: Rollback screen
5. ✏️ Fix screen: Update action payload format
6. 🚀 Re-publish with validation gate
7. 🧪 Re-run regression: Verify fix

**Timeline**: 10-15 minutes

---

## 4. Operational Metrics & Monitoring

### Key Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Publish Success Rate | >95% | <90% |
| Regression Pass Rate | >98% | <95% |
| Time-to-Publish | <30 min | >60 min |
| Rollback Frequency | <5% of publishes | >10% |
| Validation Errors | Trending down | Increasing |

### Monitoring Points

1. **Publish Gate Validation**
   - Track which checks fail most often
   - If "Binding Validation" > 20% of failures → Review developer guidelines

2. **Regression Results**
   - Track which tests fail most often
   - If >5% failures → May indicate instability

3. **Rollback Analysis**
   - Root cause: Binding issues? Action failures? Schema problems?
   - Trend: Should decrease as operators become proficient

4. **Inspector Traces**
   - Monitor execution times (should be <5 seconds typically)
   - Track API error rates from screen actions
   - Identify slow endpoints impacting UX

---

## 5. Best Practices for Operators

### ✅ DO

1. **Always use templates when possible**
   - 80% faster than blank
   - Pre-validated patterns
   - Reduces errors

2. **Review Diff before publish**
   - Takes 2 minutes
   - Catches unintended changes
   - Required for production safety

3. **Test in Preview tab**
   - Verify before publishing
   - Catch binding issues early
   - No risk to production

4. **Use Path Picker dropdown**
   - Eliminates {{}} typos
   - Autocomplete reduces errors
   - Better DX

5. **Document significant changes**
   - Add description in asset metadata
   - Use clear commit messages
   - Helps with rollback decisions

6. **Monitor regression tests**
   - Always run after publish
   - Fix failures immediately
   - Track trends

### ❌ DON'T

1. **Don't edit JSON directly**
   - Visual Editor is safer
   - Easier to maintain
   - Less error-prone

2. **Don't publish without validation**
   - Validation gate is there for reason
   - Takes <30 seconds to run
   - Worth the safety trade-off

3. **Don't ignore Diff warnings**
   - Yellow = investigate
   - Unexpected changes = red flag
   - Always review

4. **Don't skip regression**
   - Testing catches 90% of issues
   - Minimal time investment
   - Prevents customer impact

5. **Don't make cascading changes**
   - One screen change per publish
   - Easier to rollback if needed
   - Simpler debugging

6. **Don't reuse screen IDs**
   - Use versioning: `device_list_v2`, `device_list_v3`
   - Maintains history
   - Avoids confusion

---

## 6. Approval & Sign-Off

### Publish Approval Checklist

Before publishing to production, confirm:

- [ ] Screen created from template or blank
- [ ] All components properly configured
- [ ] State schema complete and accurate
- [ ] All bindings validated (no typos)
- [ ] All actions tested in Preview
- [ ] Diff reviewed (no unexpected changes)
- [ ] Validation gate: All checks pass (or warnings only)
- [ ] Regression tests selected and ready
- [ ] Stakeholder informed (if applicable)
- [ ] Runbook prepared (if complex)

### Rollback Approval Checklist

Before rolling back production, confirm:

- [ ] Issue reproduced and verified
- [ ] Root cause identified as screen-related
- [ ] Stakeholders notified
- [ ] Previous version tested (pre-rollback)
- [ ] Rollback command executed
- [ ] Regression tests re-run post-rollback
- [ ] Status dashboard updated
- [ ] Post-mortem scheduled

---

## 7. Support & Troubleshooting

### Getting Help

| Issue | Resource | Escalation |
|-------|----------|-----------|
| Schema validation error | See U3-2 docs, validation-utils.ts | Dev team |
| Binding path not found | Check state schema naming | Dev team |
| Action test fails | Test payload in Editor | Backend team |
| Regression fails | Check API health, review traces | Ops / Dev team |
| Performance issues | Monitor execution times in traces | Infrastructure team |

### Support Contact

- **On-call**: [link to on-call rotation]
- **Slack**: #ui-creator-support
- **Email**: ui-creator-ops@company.com
- **Docs**: [link to wiki]

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-19 | Initial SOP for U3-2 production release |

---

## Appendix: Quick Reference

### Command Reference

```bash
# View screen in editor
URL: /admin/screens/{screenId}

# Run regression tests
URL: /admin/regression?screen_id={screenId}

# View execution traces
URL: /admin/inspector?screen_id={screenId}

# List all screens
URL: /admin/screens
```

### Keyboard Shortcuts (Editor)

- `Ctrl+S` / `Cmd+S`: Save draft
- `Ctrl+Shift+P` / `Cmd+Shift+P`: Open Publish modal
- `Tab`: Navigate between components
- `Delete`: Remove selected component

### State Fields Quick Reference

```typescript
Common state patterns:
- items: array          // For lists/grids
- search_term: string   // For filtering
- modal_open: boolean   // For modal visibility
- is_edit: boolean      // For form mode
- selected_id: string   // For current selection
- error: string         // For error messages
- loading: boolean      // For async operations
```

---

## Sign-Off

This SOP is effective immediately for all Screen operations.

- **Document Owner**: UI Creator Team
- **Last Reviewed**: 2026-01-19
- **Next Review**: 2026-04-19 (quarterly)

**Approval**: ✅ Ready for production deployment
