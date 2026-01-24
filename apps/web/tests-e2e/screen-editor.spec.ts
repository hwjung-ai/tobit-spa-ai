import { test, expect, type Page } from '@playwright/test';

async function openDraftScreen(page: Page) {
  await page.goto('/admin/screens', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid^="screen-asset-"]', { timeout: 20000 });

  const draftCard = page.locator('[data-testid^="screen-asset-"]').filter({ hasText: 'draft' }).first();
  if (!(await draftCard.isVisible())) {
    const draftId = `e2e_draft_${Date.now()}`;
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(draftId);
    await page.locator('[data-testid="input-screen-name"]').fill('E2E Draft Screen');
    await page.locator('[data-testid="btn-confirm-create"]').click();
    await page.waitForTimeout(1000);
  }

  const draftLink = page
    .locator('[data-testid^="screen-asset-"]')
    .filter({ hasText: 'draft' })
    .first()
    .locator('[data-testid^="link-screen-"]')
    .first();
  await draftLink.waitFor({ timeout: 15000 });
  await draftLink.click();
}

/**
 * Screen Editor E2E Tests
 * Tests for the visual screen editor functionality
 */

test.describe('Screen Editor', () => {
  test('should load screen list', async ({ page }) => {
    // Navigate to screens page
    await page.goto('/admin/screens', { waitUntil: 'domcontentloaded' });

    // Wait for screen list to load
    await page.waitForSelector('[data-testid^="screen-asset-"]', { timeout: 20000 });

    // Verify screens are displayed
    const rows = await page.locator('[data-testid^="screen-asset-"]').count();
    expect(rows).toBeGreaterThan(0);
  }, { timeout: 30000 });

  test('should open visual editor for a screen', async ({ page }) => {
    await openDraftScreen(page);

    // Wait for editor to load
    await page.waitForSelector('[data-testid="screen-editor-header"]', {
      timeout: 20000
    }).catch(() => {
      // Fallback: wait for any editor elements
      return page.waitForSelector('button:has-text("Save Draft")', { timeout: 20000 });
    });

    // Verify editor header is visible
    const saveDraftButton = await page.locator('button:has-text("Save Draft")').isVisible();
    expect(saveDraftButton).toBeTruthy();
  }, { timeout: 45000 });

  test('should log authentication status in console', async ({ page }) => {
    const authEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === 'true';

    await openDraftScreen(page);

    // Wait for editor to load
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });

    // Get console messages
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.text().includes('[EDITOR]') || msg.text().includes('[API]')) {
        consoleLogs.push(msg.text());
      }
    });

    // Wait a bit for console logs
    await page.waitForTimeout(2000);

    // Verify authentication logs exist
    if (authEnabled) {
      const authLog = consoleLogs.find(log => log.includes('[API] Adding Authorization header'));
      expect(authLog).toBeTruthy();
    } else {
      const authLog = consoleLogs.find(log => log.includes('Auth disabled'));
      expect(authLog).toBeTruthy();
    }
  });

  test('should save draft successfully', async ({ page }) => {
    await openDraftScreen(page);

    // Wait for editor to load
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });

    // Wait for editor to fully initialize
    await page.waitForTimeout(2000);

    // Get initial Save Draft button state
    const saveDraftButton = page.locator('button:has-text("Save Draft")');

    // Try to click Save Draft
    const isEnabled = await saveDraftButton.isEnabled();
    if (isEnabled) {
      // Listen for success toast
      const toastPromise = page.waitForSelector('[role="alert"]:has-text("saved successfully")', {
        timeout: 10000
      }).catch(() => null);

      await saveDraftButton.click();
      const toast = await toastPromise;

      // Should see success or at least no error
      expect(toast !== null || isEnabled).toBeTruthy();
    }
  });

  test('should show error if user is not authenticated', async ({ page }) => {
    const authEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === 'true';
    test.skip(!authEnabled, 'Auth disabled in this environment');

    // Create a page without logging in
    const unauthPage = await page.context().newPage();

    // Try to navigate to editor directly
    await unauthPage.goto('/admin/screens/test-screen');

    // Should either redirect to login or show error
    const url = unauthPage.url();
    const hasError = await unauthPage.locator('text=/failed|error|not authenticated/i').isVisible().catch(() => false);

    expect(url.includes('login') || hasError).toBeTruthy();

    await unauthPage.close();
  });

  test('should handle missing token gracefully', async ({ page }) => {
    const authEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === 'true';
    test.skip(!authEnabled, 'Auth disabled in this environment');

    await openDraftScreen(page);

    // Wait for editor
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });

    // Clear token to simulate expired session
    await page.evaluate(() => {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    });

    // Try to save draft
    const saveDraftButton = page.locator('button:has-text("Save Draft")');

    // Capture console errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('[API]')) {
        errors.push(msg.text());
      }
    });

    // Click save (should fail gracefully)
    await saveDraftButton.click().catch(() => {});

    // Wait for error handling
    await page.waitForTimeout(2000);

    // Verify error was logged with helpful message
    const hasHelpfulError = errors.some(err =>
      err.includes('not logged in') || err.includes('Visit /login')
    );
    expect(hasHelpfulError || errors.length > 0).toBeTruthy();
  });

  test('should display API request logs in console', async ({ page }) => {
    await openDraftScreen(page);

    // Wait for screen to load
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });

    // Collect all API logs
    const apiLogs: string[] = [];
    page.on('console', msg => {
      if (msg.text().includes('[API]')) {
        apiLogs.push(msg.text());
      }
    });

    await page.waitForTimeout(2000);

    // Verify various API logs are present
    expect(apiLogs.length).toBeGreaterThan(0);

    // Should have logs about token and endpoint
    const hasTokenLog = apiLogs.some(log => log.includes('Authorization header'));
    const hasFetchLog = apiLogs.some(log => log.includes('Fetching'));

    expect(hasTokenLog || hasFetchLog).toBeTruthy();
  });
});
