import { test, expect } from '@playwright/test';

test('homepage has correct title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Intelligent Ops Studio/);
});

test('homepage has correct header', async ({ page }) => {
    await page.goto('/');
    const header = page.getByRole('heading', { name: 'Intelligent Ops Studio' });
    await expect(header).toBeVisible();
});
