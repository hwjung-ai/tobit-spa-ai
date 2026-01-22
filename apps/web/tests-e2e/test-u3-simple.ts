import { test as baseTest, Page, expect } from '@playwright/test';

/**
 * Custom test fixture with authentication helpers
 */
// eslint-disable-next-line react-hooks/rules-of-hooks, @typescript-eslint/no-explicit-any
const test = baseTest.extend<{
  authenticatedPage: Page;
}>({
  authenticatedPage: async ({ page }, use) => {
    // Check if authentication is disabled
    const isAuthDisabled = await page.evaluate(() => {
      return typeof window !== 'undefined' &&
        (window as any).NEXT_PUBLIC_ENABLE_AUTH === 'false';
    });

    if (isAuthDisabled) {
      console.log('Authentication is disabled, using page as-is');
      await use(page);
      return;
    }

    // Step 1: Navigate to login page
    await page.goto('/login');

    // Step 2: Login with demo credentials
    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for login to complete
    try {
      await page.waitForLoadState('networkidle', { timeout: 15000 });
    } catch {
      console.warn('Network idle not reached, continuing anyway');
    }

    // Verify login was successful
    let token = await page.evaluate(() => localStorage.getItem('access_token'));
    if (!token) {
      // Try alternative selectors for login form
      console.log('Retrying login with alternative selectors');
      await page.fill('input[type="email"]', 'admin@tobit.local');
      await page.fill('input[type="password"]', 'admin123');
      await page.click('button[type="submit"]');

      // Wait again with longer timeout
      await page.waitForTimeout(3000);
      await page.waitForLoadState('networkidle').catch(() => console.warn('Network idle not reached after retry'));

      // Check for token again
      token = await page.evaluate(() => localStorage.getItem('access_token'));
      if (!token) {
        console.warn('Login may have failed, but continuing with test');
      }
    }

    // Verify we're on the home page or a protected page
    try {
      await page.waitForURL(/^http:\/\/localhost:3000\/?$/, { timeout: 5000 });
    } catch {
      // If not redirected to home, check if we're on any protected page
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        console.warn('Still on login page, login may have failed');
      }
    }

    await use(page);
  },
});

test.describe("U3 Visual Editor - Publish & Preview", () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    // Give the authenticated page time to be ready
    await page.waitForTimeout(2000);

    // Navigate to editor
    await page.goto("/admin/screens/test-screen-1", { waitUntil: 'networkidle' });

    // Wait for editor to load with multiple fallbacks
    try {
      await page.waitForSelector('[data-testid="screen-editor"]', { timeout: 10000 });
    } catch {
      try {
        await page.waitForSelector('button:has-text("Save Draft")', { timeout: 10000 });
      } catch {
        await page.waitForSelector('[role="button"]', { timeout: 5000 });
      }
    }
  });

  test("should show save draft button for draft state", async ({ authenticatedPage: page }) => {
    // Add a component to make changes
    try {
      await page.click('[data-testid="palette-component-button"]', { timeout: 5000 });
    } catch {
      await page.click('[data-testid="palette-btn"]', { timeout: 5000 });
    }

    // Wait for buttons to be available
    await page.waitForSelector('button:has-text("Save Draft")', { timeout: 5000 });

    // Verify "Save Draft" button is visible
    await expect(page.locator('button:has-text("Save Draft")')).toBeVisible();

    // Verify "Publish" button is visible
    await expect(page.locator('button:has-text("Publish")')).toBeVisible();
  }, { timeout: 15000 });
});
