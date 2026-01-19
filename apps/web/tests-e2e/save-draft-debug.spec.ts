import { test, expect, Page } from '@playwright/test';

/**
 * Save Draft Debug Test
 * Focuses on debugging the exact issue
 */

test.describe('Save Draft - Debug', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();

    // Intercept and log all API calls
    await page.route('**/*', route => {
      const url = route.request().url();
      const method = route.request().method();

      if (url.includes('asset') || url.includes('Asset') || url.includes('screen')) {
        console.log(`[INTERCEPT] ${method} ${url}`);
      }
      route.continue();
    });

    // Console logging
    page.on('console', msg => {
      if (msg.text().includes('[API]') || msg.text().includes('[EDITOR]')) {
        console.log(`[CONSOLE] ${msg.text()}`);
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

  test('Navigate to screen and attempt save draft', async () => {
    console.log('\n=== TEST START ===\n');

    // Check if we can access admin panel
    console.log('[TEST] Navigating to /admin');
    await page.goto('/admin');
    await page.waitForTimeout(2000);

    // Check page content
    const pageContent = await page.evaluate(() => document.body.innerText.substring(0, 200));
    console.log(`[TEST] Page content: ${pageContent}`);

    // Try /admin/screens
    console.log('[TEST] Navigating to /admin/screens');
    await page.goto('/admin/screens');
    await page.waitForTimeout(3000);

    // Check if there's an error or permission issue
    const errorText = await page.evaluate(() => document.body.innerText);
    console.log(`[TEST] Page length: ${errorText.length}`);

    if (errorText.includes('error') || errorText.includes('Error') || errorText.includes('permission')) {
      console.log('[ERROR] Page contains error or permission message');
      console.log(errorText.substring(0, 500));
    }

    // Try to find table
    const tableExists = await page.locator('table').isVisible().catch(() => false);
    console.log(`[TEST] Table visible: ${tableExists}`);

    // Try to find any screen links
    const links = await page.locator('a[href*="/admin/screens/"]').count();
    console.log(`[TEST] Screen links found: ${links}`);

    // If we can find a screen, try to open it
    if (links > 0) {
      console.log('[TEST] Found screen links, clicking first one');
      const firstLink = page.locator('a[href*="/admin/screens/"]').first();
      const href = await firstLink.getAttribute('href');
      console.log(`[TEST] First screen href: ${href}`);

      await firstLink.click();
      await page.waitForTimeout(3000);

      // Check for save draft button
      const saveDraftBtn = await page.locator('button:has-text("Save Draft")').isVisible().catch(() => false);
      console.log(`[TEST] Save Draft button visible: ${saveDraftBtn}`);

      if (saveDraftBtn) {
        console.log('[TEST] Clicking Save Draft button');
        const saveDraftButton = page.locator('button:has-text("Save Draft")');

        // Listen for all network requests during save
        const requests: Array<{ method: string; url: string; status?: number }> = [];

        await page.route('**/*', route => {
          const url = route.request().url();
          const method = route.request().method();
          requests.push({ method, url });

          if (url.includes('asset') || url.includes('screen')) {
            console.log(`[REQUEST] ${method} ${url}`);
          }

          route.continue().then(() => {
            // Can't easily get response status in route, but log it
          }).catch(err => {
            console.log(`[REQUEST_ERROR] ${method} ${url}: ${err}`);
          });
        });

        // Click save draft
        try {
          await saveDraftButton.click();
          console.log('[TEST] Save Draft clicked');
        } catch (e) {
          console.log(`[ERROR] Failed to click Save Draft: ${e}`);
        }

        // Wait for requests to complete
        await page.waitForTimeout(3000);

        // Log all requests
        console.log('\n=== ALL REQUESTS ===');
        requests.forEach((req, idx) => {
          console.log(`[${idx + 1}] ${req.method} ${req.url}`);
        });

        // Filter asset requests
        const assetRequests = requests.filter(r => r.url.includes('asset'));
        console.log(`\n=== ASSET REQUESTS (${assetRequests.length}) ===`);
        assetRequests.forEach(req => {
          console.log(`${req.method} ${req.url}`);
        });

        // Check for PUT to /asset-registry/assets/
        const putRequests = assetRequests.filter(r => r.method === 'PUT');
        console.log(`\n=== PUT REQUESTS (${putRequests.length}) ===`);
        putRequests.forEach(req => {
          console.log(`${req.url}`);
        });

        const hasCorrectEndpoint = putRequests.some(r => r.url.includes('/asset-registry/assets/'));
        console.log(`\n[TEST] Has /asset-registry/assets/ endpoint: ${hasCorrectEndpoint}`);

        expect(requests.length).toBeGreaterThan(0);
      } else {
        console.log('[WARN] Save Draft button not found');
      }
    } else {
      console.log('[WARN] No screen links found');
    }
  });
});
