import { test, expect, Page } from '@playwright/test';

/**
 * Live Save Draft Test - Direct reproduction of user issue
 * Captures exact error from browser console
 */

test.describe('Save Draft - Live Issue Reproduction', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Capture all console messages
    const consoleLogs: { type: string; text: string }[] = [];
    page.on('console', msg => {
      consoleLogs.push({ type: msg.type(), text: msg.text() });
      console.log(`[CONSOLE:${msg.type()}] ${msg.text().substring(0, 200)}`);
    });

    // Capture all network requests
    const networkLog: Array<{ method: string; url: string; status?: number }> = [];
    await page.route('**/*', route => {
      networkLog.push({ method: route.request().method(), url: route.request().url() });
      route.continue();
    });

    // Login
    console.log('[TEST] === LOGIN ===');
    await page.goto('http://localhost:3000/login');
    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for redirect
    await new Promise(r => setTimeout(r, 3000));

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log(`[TEST] Token: ${!!token}`);
    expect(token).toBeTruthy();
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Reproduce exact user flow and capture error', async () => {
    console.log('\n[TEST] === STARTING REPRODUCTION ===\n');

    // Step 1: Navigate to Admin menu > Screens
    console.log('[TEST] Step 1: Navigate to Admin > Screens');
    await page.goto('http://localhost:3000/admin/screens');
    await new Promise(r => setTimeout(r, 2000));

    // Step 2: Get list of screens
    const screenLinks = await page.locator('a[href*="/admin/screens/"]').count();
    console.log(`[TEST] Found ${screenLinks} screen links`);
    expect(screenLinks).toBeGreaterThan(0);

    // Step 3: Click on first screen
    console.log('[TEST] Step 2: Click on first screen in list');
    const firstScreen = page.locator('a[href*="/admin/screens/"]').first();
    const screenId = await firstScreen.getAttribute('href');
    console.log(`[TEST] Screen ID: ${screenId}`);

    await firstScreen.click();
    await new Promise(r => setTimeout(r, 3000));

    // Step 4: Select left panel text component
    console.log('[TEST] Step 3: Select text component on left panel');

    // Try to find components in the left panel
    const components = await page.locator('[class*="component"], [role*="button"]').count();
    console.log(`[TEST] Found ${components} potential components in editor`);

    // Click on a component to select it
    if (components > 0) {
      const firstComponent = page.locator('button, [role="button"]').first();
      await firstComponent.click();
      await new Promise(r => setTimeout(r, 500));
      console.log('[TEST] Clicked first component');
    }

    // Step 5: Look for properties panel on right side
    console.log('[TEST] Step 4: Check properties panel on right');
    const propertiesPanel = await page.locator('[class*="properties"], [class*="panel"]').isVisible().catch(() => false);
    console.log(`[TEST] Properties panel visible: ${propertiesPanel}`);

    // Find name input in properties
    const nameInputs = await page.locator('input[placeholder*="name" i], input[placeholder*="Name" i]').count();
    console.log(`[TEST] Found ${nameInputs} name input fields`);

    // Step 6: Modify component name
    console.log('[TEST] Step 5: Modify component name');
    if (nameInputs > 0) {
      const nameInput = page.locator('input[placeholder*="name" i], input[placeholder*="Name" i]').first();
      const currentValue = await nameInput.inputValue();
      console.log(`[TEST] Current name: "${currentValue}"`);

      await nameInput.triple_click();
      const newName = `Test_${Date.now()}`;
      await nameInput.type(newName);
      await new Promise(r => setTimeout(r, 500));
      console.log(`[TEST] Changed name to: "${newName}"`);
    }

    // Step 7: Click Save Draft button
    console.log('[TEST] Step 6: Click Save Draft button');

    // Capture network requests during save
    const saveRequests: Array<{ method: string; url: string; status?: number }> = [];
    const saveErrors: string[] = [];

    page.on('response', res => {
      if (res.url().includes('asset') || res.url().includes('draft')) {
        saveRequests.push({
          method: res.request().method(),
          url: res.url(),
          status: res.status(),
        });

        if (!res.ok() && (res.url().includes('asset') || res.url().includes('draft'))) {
          saveErrors.push(`${res.request().method()} ${res.url()} -> ${res.status()}`);
        }
      }
    });

    const saveDraftButton = page.locator('button:has-text("Save Draft")');
    const isEnabled = await saveDraftButton.isEnabled();
    console.log(`[TEST] Save Draft button enabled: ${isEnabled}`);

    if (isEnabled) {
      // Collect console errors before save
      const consoleBefore = await page.evaluate(() => {
        const logs: string[] = [];
        return logs;
      });

      // Capture all console messages after clicking
      const errorMessages: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error' && msg.text().includes('[API]')) {
          errorMessages.push(msg.text());
        }
      });

      console.log('[TEST] Clicking Save Draft...');
      await saveDraftButton.click();

      // Wait for response
      await new Promise(r => setTimeout(r, 2000));

      // Log all captured data
      console.log('\n[TEST] === SAVE DRAFT RESULTS ===');
      console.log(`[TEST] Network requests made: ${saveRequests.length}`);
      saveRequests.forEach((req, idx) => {
        console.log(`[${idx + 1}] ${req.method} ${req.url} -> ${req.status || '?'}`);
      });

      console.log(`\n[TEST] Network errors: ${saveErrors.length}`);
      saveErrors.forEach(err => console.log(`  - ${err}`));

      console.log(`\n[TEST] Console error messages: ${errorMessages.length}`);
      errorMessages.forEach(err => console.log(`  - ${err.substring(0, 200)}`));

      // Check for specific error patterns
      const hasApiError = errorMessages.some(m => m.includes('Request failed'));
      const hasFetchError = errorMessages.some(m => m.includes('fetchApi'));

      console.log(`\n[TEST] Has API error: ${hasApiError}`);
      console.log(`[TEST] Has fetch error: ${hasFetchError}`);

      // Log full error details if any
      if (errorMessages.length > 0) {
        console.log('\n[TEST] === FULL ERROR MESSAGE ===');
        console.log(errorMessages[0]);
      }
    } else {
      console.log('[WARN] Save Draft button is disabled - modifications may not have been detected');
    }
  });
});
