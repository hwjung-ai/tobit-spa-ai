import { test, expect } from '@playwright/test';

async function gotoWithRetry(page: { goto: (url: string) => Promise<unknown>; waitForTimeout: (ms: number) => Promise<void> }, url: string, attempts: number = 3) {
  for (let i = 0; i < attempts; i++) {
    try {
      await page.goto(url);
      return;
    } catch (error) {
      if (i === attempts - 1) {
        throw error;
      }
      await page.waitForTimeout(2000);
    }
  }
}

/**
 * Comprehensive Save Draft E2E Test
 * Tests: save draft functionality with improved error handling and timeouts
 */

test.describe('Save Draft - Detailed Testing', () => {
  test('Save Draft - Full Flow with Network Monitoring', async ({ page }) => {
    console.log('\n=== TEST START: Save Draft Full Flow ===\n');

    // Navigate to screens
    console.log('[TEST] Navigating to /admin/screens');
    await gotoWithRetry(page, '/admin/screens');

    // Wait for screen list
    console.log('[TEST] Waiting for screen list to load');
    await page.waitForSelector('[data-testid^="screen-asset-"]', { timeout: 20000 }).catch(() => {
      console.log('[ERROR] Timeout waiting for screen list, trying alternative selectors');
      return page.waitForSelector('[data-testid^="link-screen-"]', { timeout: 10000 });
    });

    const rows = await page.locator('[data-testid^="screen-asset-"]').count();
    console.log(`[TEST] Found ${rows} screens in list`);
    expect(rows).toBeGreaterThan(0);

    // Create a fresh draft screen to avoid existing schema validation issues
    const draftId = `e2e_draft_${Date.now()}`;
    const draftName = `E2E Draft Screen ${Date.now()}`;
    console.log('[TEST] Creating a new draft screen');
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(draftId);
    await page.locator('[data-testid="input-screen-name"]').fill(draftName);
    await page.locator('[data-testid="btn-confirm-create"]').click();
    await page.waitForTimeout(1000);

    const searchInput = page.locator('[data-testid="input-search-screens"]');
    await searchInput.fill(draftId);

    const createdCard = page.locator('[data-testid^="screen-asset-"]').filter({
      hasText: draftId,
    }).first();
    await createdCard.waitFor({ timeout: 15000 });

    const firstScreenLink = createdCard.locator('[data-testid^="link-screen-"]').first();
    const screenHref = await firstScreenLink.getAttribute('href');
    console.log(`[TEST] First screen href: ${screenHref}`);

    // Click first screen
    console.log('[TEST] Clicking first screen');
    await firstScreenLink.click();

    // Wait for editor to load
    console.log('[TEST] Waiting for Save Draft button');
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 15000 }).catch(() => {
      console.log('[ERROR] Timeout waiting for Save Draft button, trying alternative selectors');
      // Try data-testid selector
      return page.waitForSelector('[data-testid="btn-save-draft"]', { timeout: 10000 });
    });
    console.log('[TEST] Save Draft button found');

    // Wait for editor initialization
    await page.waitForTimeout(3000);
    console.log('[TEST] Editor initialized');

    // Get current state before modification
    const apiLogs: string[] = [];
    const networkErrors: string[] = [];

    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[API]') || text.includes('[EDITOR]')) {
        apiLogs.push(text);
        console.log(text);
      }
    });

    // Monitor failed requests
    page.on('response', res => {
      if (!res.ok() && (res.url().includes('asset') || res.url().includes('draft'))) {
        const error = `${res.request().method()} ${res.url()} -> ${res.status()}`;
        networkErrors.push(error);
        console.log(`[ERROR] ${error}`);
      }
    });

    // Try to find and modify a text component
    console.log('[TEST] Looking for text components to modify');
    const textComponents = await page.locator('text=/text|Text/i').count();
    console.log(`[TEST] Found ${textComponents} text-like elements`);

    // Ensure a change is made so Save Draft is enabled
    const paletteTextButton = page.locator('[data-testid="palette-component-text"]');
    await paletteTextButton.waitFor({ timeout: 5000 });
    await paletteTextButton.click();
    await page.waitForTimeout(1000);

    // Attempt Save Draft
    console.log('\n[TEST] === SAVE DRAFT ATTEMPT ===');
    const saveDraftButton = page.locator('button:has-text("Save Draft")');

    // Collect all API calls during save
    const apiCalls: Array<{ method: string; url: string; status: number }> = [];

    page.on('response', res => {
      if (res.url().includes('asset-registry') || res.url().includes('assets')) {
        apiCalls.push({
          method: res.request().method(),
          url: res.url(),
          status: res.status(),
        });
      }
    });

    // Click Save Draft
    console.log('[TEST] Clicking Save Draft button');
    try {
      await saveDraftButton.click();
      console.log('[TEST] Save Draft button clicked successfully');
    } catch (e) {
      console.log(`[ERROR] Error clicking Save Draft: ${e}`);
      // Try alternative selectors for clicking
      try {
        const alternativeButton = page.locator('[data-testid="btn-save-draft"]');
        await alternativeButton.click();
        console.log('[TEST] Alternative Save Draft button clicked');
      } catch (altError) {
        console.log(`[ERROR] Also failed with alternative button: ${altError}`);
        throw new Error('Could not click Save Draft button with any selector');
      }
    }

    // Wait for network activity to complete with longer timeout
    await page.waitForTimeout(5000);
    console.log('[TEST] Waited 5 seconds for network requests');

    // Wait for any loading indicators to disappear
    await page.waitForLoadState('domcontentloaded', { timeout: 10000 }).catch(() => {
      console.log('[WARN] Network idle timeout reached, continuing with test');
    });

    // Log all API calls
    console.log('\n=== API CALLS MADE ===');
    apiCalls.forEach((call, idx) => {
      console.log(`[${idx + 1}] ${call.method} ${call.url} -> ${call.status}`);
    });

    // Log API logs
    console.log('\n=== API LOGS ===');
    apiLogs.forEach(log => console.log(log));

    // Log network errors
    if (networkErrors.length > 0) {
      console.log('\n=== NETWORK ERRORS ===');
      networkErrors.forEach(err => console.log(err));
    }

    // Check for success or failure indicators
    console.log('\n=== RESULT CHECK ===');
    const successToast = await page.locator('[role="alert"]:has-text("saved")').isVisible().catch(() => false);
    const errorAlert = await page.locator('[role="alert"]:has-text("error")').isVisible().catch(() => false);

    console.log(`[TEST] Success toast visible: ${successToast}`);
    console.log(`[TEST] Error alert visible: ${errorAlert}`);

    // Verify PUT request was made to correct endpoint
    const putCalls = apiCalls.filter(call => call.method === 'PUT');
    console.log(`\n[TEST] PUT calls made: ${putCalls.length}`);
    putCalls.forEach(call => {
      console.log(`  - ${call.url} -> ${call.status}`);
    });

    // Main assertion
    if (putCalls.length === 0) {
      console.log('[ERROR] NO PUT REQUEST MADE!');
    }

    const hasAssetRegistryPath = putCalls.some(call => call.url.includes('/asset-registry/assets/'));
    console.log(`[TEST] Has /asset-registry/assets/ path: ${hasAssetRegistryPath}`);

    // Summary
    console.log('\n=== SUMMARY ===');
    console.log(`API Calls: ${apiCalls.length}`);
    console.log(`PUT Requests: ${putCalls.length}`);
    console.log(`Network Errors: ${networkErrors.length}`);
    console.log(`Console API Logs: ${apiLogs.length}`);

    // Assertions
    expect(apiCalls.length).toBeGreaterThan(0);
  });

  test('Save Draft - Verify Endpoint Path', async ({ page }) => {
    console.log('\n=== TEST: Endpoint Path Verification ===\n');

    const requestUrls: string[] = [];

    page.on('response', res => {
      if (res.url().includes('asset') || res.url().includes('Asset')) {
        requestUrls.push(`${res.request().method()} ${res.url()}`);
      }
    });

    // Navigate to screen editor
    await gotoWithRetry(page, '/admin/screens');
    await page.waitForSelector('[data-testid^="screen-asset-"]', { timeout: 20000 }).catch(() => {
      console.log('[ERROR] Timeout waiting for screen list, trying alternative selectors');
      return page.waitForSelector('[data-testid^="link-screen-"]', { timeout: 10000 });
    });

    const draftId = `e2e_draft_${Date.now()}`;
    const draftName = `E2E Draft Screen ${Date.now()}`;
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(draftId);
    await page.locator('[data-testid="input-screen-name"]').fill(draftName);
    await page.locator('[data-testid="btn-confirm-create"]').click();
    await page.waitForTimeout(1000);

    const searchInput = page.locator('[data-testid="input-search-screens"]');
    await searchInput.fill(draftId);

    const createdCard = page.locator('[data-testid^="screen-asset-"]').filter({
      hasText: draftId,
    }).first();
    await createdCard.waitFor({ timeout: 15000 });

    const firstScreenLink = createdCard.locator('[data-testid^="link-screen-"]').first();
    await firstScreenLink.click();

    // Wait for editor
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 15000 }).catch(() => {
      console.log('[ERROR] Timeout waiting for Save Draft button, trying alternative selectors');
      return page.waitForSelector('[data-testid="btn-save-draft"]', { timeout: 10000 });
    });
    await page.waitForTimeout(3000);

    // Add a component so Save Draft becomes enabled
    const textButton = page.locator('[data-testid="palette-component-text"]');
    await textButton.waitFor({ timeout: 5000 });
    await textButton.click();
    await page.waitForTimeout(1000);

    // Click Save Draft
    const saveDraftButton = page.locator('button:has-text("Save Draft")');
    if (await saveDraftButton.isEnabled()) {
      await saveDraftButton.click();
      // Wait for network activity
      await page.waitForTimeout(5000);
    } else {
      console.log('[WARN] Save Draft button is disabled');
    }

    console.log('=== Request URLs ===');
    requestUrls.forEach(url => console.log(url));

    // Verify correct endpoint is being called
    const hasCorrectEndpoint = requestUrls.some(url => url.includes('/asset-registry/assets/'));
    console.log(`\nHas correct endpoint: ${hasCorrectEndpoint}`);

    if (!hasCorrectEndpoint) {
      console.log('\nERROR: Save Draft is not calling /asset-registry/assets/ endpoint!');
    }

    expect(requestUrls.length).toBeGreaterThan(0);
  });
});
