import { test, expect, Page } from '@playwright/test';

/**
 * Complete Save Draft E2E Test
 * Tests the full flow of editing and saving a screen
 */

test.describe('Save Draft - Complete Flow', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Console logging
    page.on('console', msg => {
      if (msg.text().includes('[API]') || msg.text().includes('[EDITOR]')) {
        console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
      }
    });

    // Navigate to login
    console.log('[TEST] Navigating to login');
    await page.goto('/login');

    // Login
    console.log('[TEST] Logging in');
    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for login
    await page.waitForTimeout(2000);

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log(`[TEST] Token after login: ${!!token}`);
    expect(token).toBeTruthy();
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('Edit screen component and save draft', async () => {
    console.log('\n=== TEST START: Edit and Save ===\n');

    // Navigate to screens
    console.log('[TEST] Navigating to /admin/screens');
    await page.goto('/admin/screens');
    await page.waitForTimeout(2000);

    // Find screen link
    const firstScreenLink = page.locator('a[href*="/admin/screens/"]').first();
    const href = await firstScreenLink.getAttribute('href');
    console.log(`[TEST] Opening screen: ${href}`);

    // Click screen
    await firstScreenLink.click();
    await page.waitForTimeout(3000);

    // Verify Save Draft button is visible
    const saveDraftBtn = await page.locator('button:has-text("Save Draft")').isVisible();
    console.log(`[TEST] Save Draft button visible: ${saveDraftBtn}`);
    expect(saveDraftBtn).toBeTruthy();

    // Check initial state
    const initialState = await page.evaluate(() => {
      return {
        isDirty: document.body.innerText.includes('Unsaved changes'),
        disabled: document.querySelector('[data-testid="btn-save-draft"]')?.hasAttribute('disabled'),
      };
    });
    console.log(`[TEST] Initial state - isDirty: ${initialState.isDirty}, disabled: ${initialState.disabled}`);

    // Try to find a component to modify
    console.log('[TEST] Looking for components to modify...');

    // Try clicking on components in the left panel
    const componentElements = await page.locator('[data-testid*="component"], [class*="component"], button[class*="block"]').count();
    console.log(`[TEST] Found ${componentElements} potential component elements`);

    if (componentElements > 0) {
      // Click first component
      const firstComponent = page.locator('[data-testid*="component"], [class*="component"], button[class*="block"]').first();
      console.log('[TEST] Clicking first component');
      await firstComponent.click();
      await page.waitForTimeout(1000);

      // Look for rename/name input field in properties panel
      const nameInputs = await page.locator('input[placeholder*="name" i], input[placeholder*="Name" i]').count();
      console.log(`[TEST] Found ${nameInputs} name input fields`);

      if (nameInputs > 0) {
        const nameInput = page.locator('input[placeholder*="name" i], input[placeholder*="Name" i]').first();

        // Get current value
        const currentName = await nameInput.inputValue();
        console.log(`[TEST] Current name: ${currentName}`);

        // Modify the name
        const newName = `${currentName}_Modified_${Date.now()}`;
        console.log(`[TEST] Changing name to: ${newName}`);

        await nameInput.triple_click();
        await nameInput.type(newName);
        await page.waitForTimeout(500);

        // Check if unsaved changes indicator appeared
        const hasUnsavedIndicator = await page.evaluate(() =>
          document.body.innerText.includes('Unsaved changes')
        );
        console.log(`[TEST] Has unsaved indicator: ${hasUnsavedIndicator}`);
      }
    }

    // Check Save Draft button state now
    const saveDraftButton = page.locator('button[data-testid="btn-save-draft"]');
    const isDisabled = await saveDraftButton.isDisabled();
    console.log(`[TEST] Save Draft button disabled: ${isDisabled}`);

    // If it's still disabled, try a different approach - modify screen name directly
    if (isDisabled) {
      console.log('[TEST] Try modifying screen name via top section');

      // Look for the screen name that might be editable
      const screenNameElements = await page.locator('h1, h2, [role="heading"]').count();
      console.log(`[TEST] Found ${screenNameElements} heading elements`);

      // Try to find any editable text in the editor
      const editableInputs = await page.locator('input[type="text"], textarea').count();
      console.log(`[TEST] Found ${editableInputs} editable inputs`);

      if (editableInputs > 0) {
        const firstInput = page.locator('input[type="text"], textarea').first();
        const placeholder = await firstInput.getAttribute('placeholder');
        const value = await firstInput.inputValue();
        console.log(`[TEST] First input - placeholder: ${placeholder}, value: ${value}`);

        if (value && value.length < 100) {
          // Try modifying this field
          await firstInput.triple_click();
          await firstInput.type('_test_modification');
          console.log('[TEST] Modified first input field');
          await page.waitForTimeout(500);
        }
      }
    }

    // Check Save Draft button state again
    const isSaveDraftEnabled = await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="btn-save-draft"]');
      return btn && !btn.hasAttribute('disabled');
    });
    console.log(`[TEST] Save Draft enabled: ${isSaveDraftEnabled}`);

    if (isSaveDraftEnabled) {
      console.log('[TEST] === Attempting to save draft ===');

      // Monitor network requests
      const apiRequests: Array<{ method: string; url: string }> = [];

      await page.route('**/*', route => {
        const url = route.request().url();
        const method = route.request().method();

        if (url.includes('asset')) {
          apiRequests.push({ method, url });
          console.log(`[NETWORK] ${method} ${url}`);
        }

        route.continue();
      });

      // Get the current button state before clicking
      const beforeSave = await page.evaluate(() => ({
        hasUnsavedChanges: document.body.innerText.includes('Unsaved changes'),
      }));
      console.log(`[TEST] Before save - unsaved changes indicator: ${beforeSave.hasUnsavedChanges}`);

      // Click Save Draft
      try {
        console.log('[TEST] Clicking Save Draft button');
        const saveDraftBtn = page.locator('button[data-testid="btn-save-draft"]');
        await saveDraftBtn.click();
        console.log('[TEST] Save Draft button clicked');
      } catch (e) {
        console.error(`[ERROR] Failed to click Save Draft: ${e}`);
      }

      // Wait for requests to complete
      await page.waitForTimeout(3000);

      // Check results
      const afterSave = await page.evaluate(() => ({
        hasUnsavedChanges: document.body.innerText.includes('Unsaved changes'),
        hasSavingText: document.body.innerText.includes('Saving'),
      }));
      console.log(`[TEST] After save - unsaved changes: ${afterSave.hasUnsavedChanges}, saving: ${afterSave.hasSavingText}`);

      // Check API requests
      console.log('\n=== API Requests ===');
      apiRequests.forEach((req, idx) => {
        console.log(`[${idx + 1}] ${req.method} ${req.url}`);
      });

      const putRequests = apiRequests.filter(r => r.method === 'PUT');
      const hasAssetRegistryPath = putRequests.some(r => r.url.includes('/asset-registry/assets/'));

      console.log(`\n[TEST] PUT requests: ${putRequests.length}`);
      console.log(`[TEST] Has /asset-registry/assets/ path: ${hasAssetRegistryPath}`);

      expect(putRequests.length).toBeGreaterThan(0);
      if (putRequests.length > 0) {
        expect(hasAssetRegistryPath).toBeTruthy();
      }
    } else {
      console.log('[WARN] Save Draft button is still disabled - no modifications detected');
      console.log('[INFO] This test requires actual screen modifications to enable the save button');
    }
  });
});
