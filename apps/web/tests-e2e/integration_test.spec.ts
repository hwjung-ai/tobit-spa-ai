import { test, expect } from '@playwright/test';

test('integration test: homepage loads and has navigation', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveTitle(/Intelligent Ops Studio/);

  // Check if navigation elements are present
  const nav = page.locator('nav').first();
  await expect(nav).toBeVisible();

  // Test a simple interaction if possible
  const header = page.getByRole('heading', { name: 'Intelligent Ops Studio' });
  await expect(header).toBeVisible();
}, { timeout: 30000 });
