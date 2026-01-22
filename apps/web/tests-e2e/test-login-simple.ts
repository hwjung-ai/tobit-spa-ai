import { test, expect } from '@playwright/test';

test.describe('Login Test', () => {
  test('should login successfully', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');

    // Fill in credentials
    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // Wait for navigation
    await page.waitForLoadState('networkidle');

    // Check if we have access token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
  });
});