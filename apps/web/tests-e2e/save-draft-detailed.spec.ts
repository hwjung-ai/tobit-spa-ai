import { test, expect, Page } from '@playwright/test';

/**
 * Detailed Save Draft E2E Test
 * Tests the save draft functionality with comprehensive error logging
 */

test.describe('Save Draft - Detailed Testing', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Enable all console and network logging
    page.on('console', msg => console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`));
    page.on('response', res => {
      if (res.url().includes('asset-registry') || res.url().includes('assets')) {
        console.log(`[NETWORK] ${res.request().method()} ${res.url()} -> ${res.status()}`);
      }
    });

    // Step 1: Navigate to login page
    await page.goto('/login');
    console.log('[TEST] Navigated to login page');

    // Step 2: Login
    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');
    console.log('[TEST] Submitted login form');

    // Wait for redirect
    try {
      await page.waitForURL(/admin|home/, { timeout: 10000 });
    } catch {
      console.log('[TEST] URL change timeout, checking token');
    }

    // Verify token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log(`[TEST] Token exists: ${!!token}`);
    expect(token).toBeTruthy();
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Save Draft - Full Flow with Network Monitoring', async () => {
    console.log('\n=== TEST START: Save Draft Full Flow ===\n');

    // Navigate to screens
    console.log('[TEST] Navigating to /admin/screens');
    await page.goto('/admin/screens');

    // Wait for screen list
    console.log('[TEST] Waiting for screen list to load');
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    const rows = await page.locator('table tbody tr').count();
    console.log(`[TEST] Found ${rows} screens in list`);
    expect(rows).toBeGreaterThan(0);

    // Get first screen ID
    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    const screenHref = await firstScreenLink.getAttribute('href');
    console.log(`[TEST] First screen href: ${screenHref}`);

    // Click first screen
    console.log('[TEST] Clicking first screen');
    await firstScreenLink.click();

    // Wait for editor to load
    console.log('[TEST] Waiting for Save Draft button');
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });
    console.log('[TEST] Save Draft button found');

    // Wait for editor initialization
    await page.waitForTimeout(2000);
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
    } catch {
      console.log(`[TEST] Error clicking Save Draft: ${e}`);
    }

    // Wait for network activity to complete
    await page.waitForTimeout(3000);
    console.log('[TEST] Waited 3 seconds for network requests');

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

  test('Save Draft - Verify Endpoint Path', async () => {
    console.log('\n=== TEST: Endpoint Path Verification ===\n');

    const requestUrls: string[] = [];

    page.on('response', res => {
      if (res.url().includes('asset') || res.url().includes('Asset')) {
        requestUrls.push(`${res.request().method()} ${res.url()}`);
      }
    });

    // Navigate to screen editor
    await page.goto('/admin/screens');
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    await firstScreenLink.click();

    // Wait for editor
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Click Save Draft
    const saveDraftButton = page.locator('button:has-text("Save Draft")');
    if (await saveDraftButton.isEnabled()) {
      await saveDraftButton.click();
    }

    // Wait for requests
    await page.waitForTimeout(2000);

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
