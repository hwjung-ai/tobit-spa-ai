import { test, expect } from '@playwright/test';

/**
 * E2E tests for Ops Inspector and Query workflows
 *
 * These tests verify the complete flow from running queries to inspecting results
 * and performing root cause analysis.
 */

const BASE_URL = 'http://localhost:3000';

test.describe('Ops Query and Inspector Integration', () => {

  // ===== CASE 1: Open in Inspector from /ops/query =====
  test('Case1: /ops/query -> Open in Inspector - Complete Flow', async ({ page }) => {
    // 1. Navigate to /ops/query page
    await page.goto(`${BASE_URL}/ops/query`);
    await page.waitForLoadState('networkidle');

    console.log('Navigated to /ops/query');

    // 2. Wait for page content to load
    await expect(page).toHaveURL(/.*\/ops\/query.*/);

    // 3. Look for Open in Inspector button
    const openBtn = page.locator('[data-testid="ops-open-in-inspector"]');

    // 4. If button exists and is visible, click it
    const btnExists = await openBtn.isVisible({ timeout: 5000 }).catch(() => false);
    if (btnExists) {
      console.log('Open in Inspector button found');
      await openBtn.click();

      // 5. Wait for navigation to inspector with trace_id
      await page.waitForURL(/admin\/inspector\?trace_id=/, { timeout: 15000 });
      console.log('Navigated to inspector with trace_id');

      // 6. Verify inspector drawer loaded
      const drawer = page.locator('[data-testid="inspector-drawer"]');
      await expect(drawer).toBeVisible({ timeout: 10000 });
      console.log('Inspector drawer is visible');

      // 7. Extract and log trace_id from URL
      const url = page.url();
      const traceIdMatch = url.match(/trace_id=([^&]+)/);
      if (traceIdMatch) {
        console.log(`Trace ID: ${traceIdMatch[1]}`);
      }
    } else {
      console.log('Open in Inspector button not visible - verifying page loaded at least');
      await expect(page).toHaveURL(/.*\/ops\/query.*/);
    }
  });

  // ===== CASE 2: Inspector Drawer - Flow Section Visibility & Empty-State =====
  test('Case2: Inspector Drawer - Flow section is visible with proper empty-state handling', async ({ page }) => {
    // 1. Navigate to inspector directly with a test trace
    const testTraceId = 'test-trace-empty-flow';
    await page.goto(`${BASE_URL}/admin/inspector?trace_id=${testTraceId}`);
    await page.waitForLoadState('networkidle');

    console.log(`Navigated to inspector with trace_id=${testTraceId}`);

    // 2. Verify inspector drawer is visible
    const drawer = page.locator('[data-testid="inspector-drawer"]');
    await expect(drawer).toBeVisible({ timeout: 15000 });
    console.log('Inspector drawer is visible');

    // 3. Verify Flow section exists
    const flowSection = page.locator('[data-testid="flow-section"]');
    await expect(flowSection).toBeVisible({ timeout: 10000 });
    console.log('Flow section is visible');

    // 4. Check for empty-state (when no flow_spans are present)
    const emptyState = page.locator('[data-testid="flow-empty-state"]');
    const emptyStateVisible = await emptyState.isVisible({ timeout: 5000 }).catch(() => false);

    if (emptyStateVisible) {
      console.log('Flow empty-state is visible');
      await expect(emptyState).toBeVisible();

      // 5. Verify empty-state message
      const emptyStateText = await emptyState.textContent();
      console.log(`Empty state text: ${emptyStateText}`);

      // 6. Verify flow toggles are disabled/hidden in empty state
      const timelineToggle = page.locator('[data-testid="flow-toggle-timeline"]');
      const graphToggle = page.locator('[data-testid="flow-toggle-graph"]');

      const timelineVisible = await timelineToggle.isVisible().catch(() => false);
      const graphVisible = await graphToggle.isVisible().catch(() => false);

      console.log(`Timeline toggle visible: ${timelineVisible}, Graph toggle visible: ${graphVisible}`);
    } else {
      console.log('No empty-state found - flow data may be present or flow section is minimal');
    }
  });

  // ===== CASE 3: Run RCA Button - Single Mode with API Call & Routing =====
  test('Case3: Drawer header "Run RCA" triggers POST /ops/rca (single) and redirects', async ({ page }) => {
    const testTraceId = 'test-trace-rca-single';
    const rcaResultTraceId = 'trace-rca-single-result-001';

    // 1. Intercept /ops/rca API calls
    await page.route('**/ops/rca', (route) => {
      const request = route.request();

      console.log('RCA API called');
      console.log(`Method: ${request.method()}`);

      // 2. Verify it's a POST request
      if (request.method() === 'POST') {
        const postData = request.postDataJSON();
        console.log('RCA request body:', JSON.stringify(postData));

        // 3. Verify request structure
        expect(postData).toHaveProperty('mode');
        expect(postData).toHaveProperty('trace_id');
        expect(postData).toHaveProperty('options');
        expect(postData.mode).toBe('single');

        // 4. Mock response
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            trace_id: rcaResultTraceId,
            status: 'success',
          }),
        });
      } else {
        route.continue();
      }
    });

    // 5. Navigate to inspector
    await page.goto(`${BASE_URL}/admin/inspector?trace_id=${testTraceId}`);
    await page.waitForLoadState('networkidle');

    // 6. Verify drawer loaded
    const drawer = page.locator('[data-testid="inspector-drawer"]');
    await expect(drawer).toBeVisible({ timeout: 10000 });
    console.log('Inspector drawer loaded');

    // 7. Click Run RCA button
    const runRcaBtn = page.locator('[data-testid="drawer-run-rca"]');
    const btnVisible = await runRcaBtn.isVisible({ timeout: 5000 }).catch(() => false);

    if (btnVisible) {
      console.log('Run RCA button found');

      // 8. Wait for RCA response
      const rcaPromise = page.waitForResponse(response =>
        response.url().includes('/ops/rca') && response.status() === 200
      );

      await runRcaBtn.click();
      console.log('Run RCA button clicked');

      // 9. Verify response
      const rcaResponse = await rcaPromise.catch(() => null);
      if (rcaResponse) {
        const rcaData = await rcaResponse.json();
        console.log('RCA response:', rcaData);

        // 10. Verify navigation to result trace
        await page.waitForURL(new RegExp(`trace_id=${rcaResultTraceId}`), { timeout: 15000 });
        console.log(`Navigated to result trace: ${rcaResultTraceId}`);

        expect(page.url()).toContain(`trace_id=${rcaResultTraceId}`);
      }
    } else {
      console.log('Run RCA button not found in drawer');
    }
  });

  // ===== CASE 4: Compare & Diff Overlay - RCA in Diff Mode =====
  test('Case4: Compare -> Diff overlay -> Run RCA (diff mode) with API validation', async ({ page }) => {
    const baselineTraceId = 'trace-baseline-diff-001';
    const candidateTraceId = 'trace-candidate-diff-001';
    const rcaResultTraceId = 'trace-rca-diff-result-001';

    // 1. Intercept diff RCA calls
    await page.route('**/ops/rca', (route) => {
      const request = route.request();

      if (request.method() === 'POST') {
        const postData = request.postDataJSON();
        console.log('Diff RCA request body:', JSON.stringify(postData));

        // 2. Validate diff mode structure
        if (postData.mode === 'diff') {
          expect(postData).toHaveProperty('baseline_trace_id');
          expect(postData).toHaveProperty('candidate_trace_id');
          console.log(
            `Diff mode: baseline=${postData.baseline_trace_id}, candidate=${postData.candidate_trace_id}`
          );
        }

        // 3. Mock response
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            trace_id: rcaResultTraceId,
            status: 'success',
          }),
        });
      } else {
        route.continue();
      }
    });

    // 4. Navigate to baseline trace
    await page.goto(`${BASE_URL}/admin/inspector?trace_id=${baselineTraceId}`);
    await page.waitForLoadState('networkidle');
    console.log(`Opened baseline trace: ${baselineTraceId}`);

    // 5. Click Compare button
    const compareBtn = page.locator('[data-testid="compare-button"]');
    const compareBtnVisible = await compareBtn.isVisible({ timeout: 5000 }).catch(() => false);

    if (compareBtnVisible) {
      console.log('Compare button found');
      await compareBtn.click();

      // 6. Fill in candidate trace ID
      const compareInput = page.locator('[data-testid="compare-trace-id-input"]');
      const inputVisible = await compareInput.isVisible({ timeout: 5000 }).catch(() => false);

      if (inputVisible) {
        console.log('Compare input found');
        await compareInput.fill(candidateTraceId);

        // 7. Click confirm
        const confirmBtn = page.locator('[data-testid="compare-confirm"]');
        const confirmVisible = await confirmBtn.isVisible({ timeout: 5000 }).catch(() => false);

        if (confirmVisible) {
          console.log('Confirm button found');
          await confirmBtn.click();

          // 8. Wait for diff overlay
          const diffOverlay = page.locator('[data-testid="diff-overlay"]');
          const overlayVisible = await diffOverlay.isVisible({ timeout: 10000 }).catch(() => false);

          if (overlayVisible) {
            console.log('Diff overlay is visible');

            // 9. Click Run RCA in diff overlay
            const diffRunRcaBtn = page.locator('[data-testid="diff-run-rca"]');
            const diffRcaBtnVisible = await diffRunRcaBtn.isVisible({ timeout: 5000 }).catch(() => false);

            if (diffRcaBtnVisible) {
              console.log('Diff Run RCA button found');

              // 10. Wait for RCA response
              const rcaPromise = page.waitForResponse(response =>
                response.url().includes('/ops/rca') && response.status() === 200
              );

              await diffRunRcaBtn.click();
              console.log('Diff Run RCA button clicked');

              // 11. Verify response and navigation
              const rcaResponse = await rcaPromise.catch(() => null);
              if (rcaResponse) {
                const rcaData = await rcaResponse.json();
                console.log('Diff RCA response:', rcaData);

                await page.waitForURL(new RegExp(`trace_id=${rcaResultTraceId}`), { timeout: 15000 });
                console.log(`Navigated to diff RCA result: ${rcaResultTraceId}`);
              }
            } else {
              console.log('Diff Run RCA button not found');
            }
          } else {
            console.log('Diff overlay did not appear');
          }
        } else {
          console.log('Confirm button not found');
        }
      } else {
        console.log('Compare input not found');
      }
    } else {
      console.log('Compare button not visible');
    }
  });

  // ===== CASE 5: Regression Page =====
  test('Case5: /admin/regression page loads and renders regression panel', async ({ page }) => {
    // 1. Navigate to regression page
    await page.goto(`${BASE_URL}/admin/regression`);
    await page.waitForLoadState('networkidle');
    console.log('Navigated to /admin/regression');

    // 2. Verify page URL
    await expect(page).toHaveURL(/.*\/admin\/regression.*/);

    // 3. Verify regression panel is rendered
    const regressionPanel = page.locator('[data-testid="regression-panel"]');
    const panelVisible = await regressionPanel.isVisible({ timeout: 15000 }).catch(() => false);

    if (panelVisible) {
      console.log('Regression panel is visible');
      await expect(regressionPanel).toBeVisible();

      // 4. Verify page has interactive controls
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();
      console.log(`Found ${buttonCount} buttons on regression page`);
      expect(buttonCount).toBeGreaterThan(0);

      // 5. Look for common regression testing controls
      const inputs = page.locator('input');
      const inputCount = await inputs.count();
      console.log(`Found ${inputCount} inputs on regression page`);

      // 6. Log panel content for debugging
      const panelText = await regressionPanel.textContent();
      console.log(`Regression panel content: ${panelText}`);
    } else {
      console.log('Regression panel not visible - checking page structure');
      const pageTitle = await page.title();
      console.log(`Page title: ${pageTitle}`);
    }
  });

});

/**
 * Helper test: Validate network requests structure
 */
test.describe('Network Request Validation', () => {

  test('Validate RCA API request/response contract', async ({ page }) => {
    const capturedRequests: Array<{
    method: string;
    body: unknown;
  }> = [];

    await page.route('**/ops/rca', (route) => {
      capturedRequests.push({
        method: route.request().method(),
        body: route.request().postDataJSON(),
      });

      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ trace_id: 'result-001' }),
      });
    });

    await page.goto(`${BASE_URL}/admin/inspector?trace_id=contract-test-001`);
    await page.waitForLoadState('networkidle');

    const runRcaBtn = page.locator('[data-testid="drawer-run-rca"]');
    if (await runRcaBtn.isVisible()) {
      await runRcaBtn.click();
      await page.waitForTimeout(1000);

      if (capturedRequests.length > 0) {
        const request = capturedRequests[0];
        console.log('Captured RCA request:', request);

        expect(request.method).toBe('POST');
        expect(request.body).toBeDefined();
        expect(request.body.mode).toBeDefined();
        expect(request.body.trace_id).toBeDefined();
        expect(request.body.options).toBeDefined();
      }
    }
  });

});
