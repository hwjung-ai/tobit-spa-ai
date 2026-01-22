import { test, expect } from '@playwright/test';

test('homepage has correct title', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveTitle(/Intelligent Ops Studio/);
}, { timeout: 30000 });

test('homepage has correct header', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('heading', { name: 'Intelligent Ops Studio' })).toBeVisible();
}, { timeout: 30000 });
