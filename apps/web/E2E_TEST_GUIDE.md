# Inspector E2E Tests Guide

## Overview

This guide documents the Playwright E2E tests for the Inspector UI components and workflows. The tests verify the complete flow from querying to inspecting results and performing root cause analysis (RCA).

## Test Files

- **`tests-e2e/ops_e2e.spec.ts`** - Main E2E tests (5 cases + network validation)
- **`tests-e2e/inspector_e2e.spec.ts`** - Additional Inspector-specific tests

## Test Cases

### Case 1: Open in Inspector from /ops/query
**File:** `ops_e2e.spec.ts` → Case1
**Description:** Verifies navigation from query page to inspector with trace_id
**Steps:**
1. Navigate to `/ops/query`
2. Click "Open in Inspector" button (if visible)
3. Verify URL change to `/admin/inspector?trace_id=...`
4. Verify inspector drawer loads

**Selectors Used:**
- `[data-testid="ops-open-in-inspector"]` - Open button
- `[data-testid="inspector-drawer"]` - Inspector container

---

### Case 2: Inspector Drawer - Flow Section & Empty-State
**File:** `ops_e2e.spec.ts` → Case2
**Description:** Verifies Flow section visibility and empty-state handling when no flow_spans
**Steps:**
1. Navigate to `/admin/inspector?trace_id=<test-id>`
2. Verify Flow section is visible
3. Check for empty-state message
4. Verify toggle buttons (if applicable)

**Selectors Used:**
- `[data-testid="inspector-drawer"]` - Inspector container
- `[data-testid="flow-section"]` - Flow section
- `[data-testid="flow-empty-state"]` - Empty state message
- `[data-testid="flow-toggle-timeline"]` - Timeline toggle (if visible)
- `[data-testid="flow-toggle-graph"]` - Graph toggle (if visible)

**Expected Behavior:**
- Flow section always visible
- Empty-state shows message when no flow_spans
- Toggles may be disabled or hidden in empty state

---

### Case 3: Run RCA (Single Mode) - API Call & Routing
**File:** `ops_e2e.spec.ts` → Case3
**Description:** Verifies RCA button triggers POST /ops/rca (single mode) and redirects
**Steps:**
1. Navigate to inspector
2. Click "Run RCA" button
3. Intercept POST /ops/rca request
4. Verify request body structure:
   ```json
   {
     "mode": "single",
     "trace_id": "<current-trace>",
     "options": {}
   }
   ```
5. Mock response with new trace_id
6. Verify URL changes to new trace

**Selectors Used:**
- `[data-testid="drawer-run-rca"]` - Run RCA button

**Network Interception:**
- Endpoint: `POST **/ops/rca`
- Expected request body properties: `mode`, `trace_id`, `options`
- Expected response: `{ trace_id: string }`

---

### Case 3B: Run RCA Error Handling
**File:** `inspector_e2e.spec.ts` → Case3B
**Description:** Verifies error handling when RCA fails
**Steps:**
1. Navigate to inspector
2. Mock RCA endpoint to return 500
3. Click "Run RCA" button
4. Verify error is handled (alert/console/silent)

---

### Case 4: Compare → Diff Overlay → Run RCA (Diff Mode)
**File:** `ops_e2e.spec.ts` → Case4
**Description:** Verifies complete diff comparison and diff-mode RCA
**Steps:**
1. Navigate to `/admin/inspector?trace_id=<baseline>`
2. Click "Compare" button
3. Fill baseline trace input
4. Click "Confirm"
5. Wait for Diff overlay to appear
6. Click "Run RCA" in diff overlay
7. Intercept POST /ops/rca request
8. Verify request body:
   ```json
   {
     "mode": "diff",
     "baseline_trace_id": "<baseline>",
     "candidate_trace_id": "<candidate>"
   }
   ```
9. Verify URL changes to result trace

**Selectors Used:**
- `[data-testid="compare-button"]` - Compare button
- `[data-testid="compare-trace-id-input"]` - Baseline trace input
- `[data-testid="compare-confirm"]` - Confirm button
- `[data-testid="diff-overlay"]` - Diff overlay container
- `[data-testid="diff-run-rca"]` - Diff RCA button

**Network Interception:**
- Endpoint: `POST **/ops/rca`
- Mode: `"diff"` with `baseline_trace_id` and `candidate_trace_id`

---

### Case 5: /admin/regression Page Rendering
**File:** `ops_e2e.spec.ts` → Case5
**Description:** Verifies regression panel loads and renders
**Steps:**
1. Navigate to `/admin/regression`
2. Verify page URL
3. Verify regression panel is visible
4. Check for interactive controls (buttons, inputs)
5. Log panel content

**Selectors Used:**
- `[data-testid="regression-panel"]` - Regression panel

---

## Required Data-TestId Attributes

All UI components should include these `data-testid` attributes for test stability:

### Core Components
- `ops-open-in-inspector` - Button in query page
- `inspector-drawer` - Main inspector container
- `inspector-trace-row` - Trace list item
- `regression-panel` - Regression panel container

### Flow Section
- `flow-section` - Flow section container
- `flow-empty-state` - Empty state message
- `flow-toggle-timeline` - Timeline view toggle
- `flow-toggle-graph` - Graph view toggle

### RCA Controls
- `drawer-run-rca` - Single-mode RCA button
- `diff-run-rca` - Diff-mode RCA button

### Compare Controls
- `compare-button` - Compare trigger button
- `compare-trace-id-input` - Baseline trace input field
- `compare-confirm` - Confirm button
- `diff-overlay` - Diff overlay container

---

## Running Tests Locally

### Prerequisites
- Frontend (Next.js) running on `http://localhost:3000`
- Backend (FastAPI) running on `http://localhost:8000` (for API mocking)
- Playwright installed: `npm install -D @playwright/test`

### Run All Tests
```bash
cd apps/web
npm run test:e2e
# or
npx playwright test
```

### Run Specific Test File
```bash
npx playwright test tests-e2e/ops_e2e.spec.ts
```

### Run Specific Test Case
```bash
npx playwright test -g "Case1"
npx playwright test -g "Case3"
```

### Debug Mode
```bash
npx playwright test --debug
```

### View Test Report
```bash
npx playwright show-report
```

---

## Running Tests in CI

### Configuration
- CI environment variable: `CI=true`
- Workers: 1 (sequential execution)
- Retries: 2 on CI
- Browser: Chromium (headless)
- Base URL: `http://localhost:3000`

### CI Commands
```bash
npm run test:e2e:ci
# or
CI=true npx playwright test
```

### Test Report Artifacts
- HTML report: `playwright-report/index.html`
- Traces: `test-results/` (on failure)
- Screenshots: `test-results/` (on failure)
- Videos: `test-results/` (if enabled)

---

## Network Mocking Strategy

### RCA Endpoint Interception
Tests intercept `/ops/rca` requests using `page.route()`:

```typescript
await page.route('**/ops/rca', (route) => {
  const request = route.request();

  // Log and validate request
  console.log('Method:', request.method()); // POST
  const body = request.postDataJSON();
  console.log('Body:', body);

  // Mock response
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ trace_id: 'mock-result' }),
  });
});
```

### Request Validation
- `mode` must be `"single"` or `"diff"`
- `trace_id` or `baseline_trace_id`/`candidate_trace_id` required
- `options` object (can be empty)

---

## Debugging Failed Tests

### Check Console Logs
```bash
npx playwright test --reporter=list
```

### View Trace & Screenshots
```bash
# After test failure
npx playwright show-report
# Click on failed test to see trace, screenshot, video
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Element not found" | Check `data-testid` exists in component |
| "Timeout waiting for element" | Increase timeout or check element visibility conditions |
| "API not mocked" | Verify `page.route()` pattern matches endpoint |
| "Navigation timeout" | Check if URL actually changed after action |

---

## Test Statistics

### Coverage
- **5 main test cases** covering inspector workflows
- **1 network validation test** for API contracts
- **3 additional inspector-specific tests**

### Total Tests
- ops_e2e.spec.ts: 6 tests
- inspector_e2e.spec.ts: 8 tests
- **Total: 14 tests**

---

## Future Enhancements

- [ ] Add fixture data generation for tests
- [ ] Implement visual regression testing
- [ ] Add performance metrics collection
- [ ] Expand error scenario coverage
- [ ] Add accessibility testing

---

## Troubleshooting

### Tests Pass Locally but Fail in CI
- Check Node/Browser versions match
- Verify environment variables (CI flag)
- Check network/API mocking differences
- Review headless mode compatibility

### Element Visibility Issues
- Add explicit waits: `await page.waitForLoadState('networkidle')`
- Use `.catch(() => false)` for optional elements
- Check CSS/z-index issues with dev tools

### Flaky Tests
- Increase timeout values
- Add additional wait conditions
- Verify network mocking consistency
- Check for race conditions in element selection

---

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Test Best Practices](https://playwright.dev/docs/best-practices)
- [Network Interception](https://playwright.dev/docs/network)
- [Debugging Tests](https://playwright.dev/docs/debug)
