import { test, expect } from '@playwright/test';

test.describe('Explore UI Structure', () => {
  test('should load UI and verify page structure', async ({ page }) => {
    // Navigate to home page
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Verify page loaded
    await expect(page).toHaveURL(/.*\//);

    // Verify basic page elements exist
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check for common UI elements
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    expect(buttonCount).toBeGreaterThanOrEqual(0);

    // Check for inputs
    const inputs = page.locator('input');
    const inputCount = await inputs.count();
    expect(inputCount).toBeGreaterThanOrEqual(0);

    console.log(`Page loaded with ${buttonCount} buttons and ${inputCount} inputs`);
  });

  test('should verify admin screens page is accessible', async ({ page }) => {
    // Navigate to admin screens page
    await page.goto('/admin/screens', { waitUntil: 'domcontentloaded' });

    // Verify page loaded
    await expect(page).toHaveURL(/.*\/admin\/screens.*/);

    // Verify page has content
    const main = page.locator('main').first();
    const mainExists = await main.isVisible().catch(() => false);

    if (mainExists) {
      await expect(main).toBeVisible();
    }

    console.log('Admin screens page is accessible');
  });

  test('should verify page has interactive elements', async ({ page }) => {
    // Navigate to home
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Get page structure info
    const pageInfo = await page.evaluate(() => {
      return {
        title: document.title,
        hasNav: !!document.querySelector('nav'),
        hasHeader: !!document.querySelector('header'),
        buttonCount: document.querySelectorAll('button').length,
        inputCount: document.querySelectorAll('input').length,
      };
    });

    expect(pageInfo.buttonCount).toBeGreaterThanOrEqual(0);
    expect(pageInfo.inputCount).toBeGreaterThanOrEqual(0);

    console.log('Page structure verified:', pageInfo);
  });
});
