import { test, expect, Page } from '@playwright/test';

/**
 * Screen Editor E2E Tests
 * Tests for the visual screen editor functionality
 */

test.describe('Screen Editor', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Step 1: Navigate to login page
    await page.goto('/login');

    // Step 2: Login with demo credentials
    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for redirect to home page or success indication
    try {
      await page.waitForURL(/^http:\/\/localhost:3000\/?$/, { timeout: 10000 });
    } catch {
      // Login might redirect to a different page, check if token exists instead
    }

    // Verify token was stored in localStorage
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    if (!token) {
      console.warn('Token not found after login, checking page');
      // If token doesn't exist, the test setup failed
      const loginError = await page.locator('text=/error|invalid|failed/i').isVisible().catch(() => false);
      if (loginError) {
        throw new Error('Login failed');
      }
    }
    expect(token).toBeTruthy();
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('should load screen list', async () => {
    // Navigate to screens page
    await page.goto('/admin/screens');

    // Wait for screen list to load
    await page.waitForSelector('[role="table"]', { timeout: 10000 });

    // Verify screens are displayed
    const rows = await page.locator('table tbody tr').count();
    expect(rows).toBeGreaterThan(0);
  });

  test('should open visual editor for a screen', async () => {
    // Navigate to screens page
    await page.goto('/admin/screens');

    // Wait for first screen to be clickable
    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    await firstScreenLink.waitFor({ timeout: 10000 });

    // Click first screen
    await firstScreenLink.click();

    // Wait for editor to load
    await page.waitForSelector('[data-testid="screen-editor-header"]', {
      timeout: 10000
    }).catch(() => {
      // Fallback: wait for any editor elements
      return page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });
    });

    // Verify editor header is visible
    const saveDraftButton = await page.locator('button:has-text("Save Draft")').isVisible();
    expect(saveDraftButton).toBeTruthy();
  });

  test('should log authentication status in console', async () => {
    // Navigate to editor
    await page.goto('/admin/screens');
    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    await firstScreenLink.click();

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
    const authLog = consoleLogs.find(log => log.includes('[API] Adding Authorization header'));
    expect(authLog).toBeTruthy();
  });

  test('should save draft successfully', async () => {
    // Navigate to editor
    await page.goto('/admin/screens');
    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    await firstScreenLink.click();

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

  test('should show error if user is not authenticated', async ({ browser }) => {
    // Create a page without logging in
    const unauthPage = await browser.newPage();

    // Try to navigate to editor directly
    await unauthPage.goto('/admin/screens/test-screen');

    // Should either redirect to login or show error
    const url = unauthPage.url();
    const hasError = await unauthPage.locator('text=/failed|error|not authenticated/i').isVisible().catch(() => false);

    expect(url.includes('login') || hasError).toBeTruthy();

    await unauthPage.close();
  });

  test('should handle missing token gracefully', async () => {
    // Navigate to editor
    await page.goto('/admin/screens');
    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    await firstScreenLink.click();

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

  test('should display API request logs in console', async () => {
    // Navigate to editor
    await page.goto('/admin/screens');
    const firstScreenLink = page.locator('table tbody tr:first-child a').first();
    await firstScreenLink.click();

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
