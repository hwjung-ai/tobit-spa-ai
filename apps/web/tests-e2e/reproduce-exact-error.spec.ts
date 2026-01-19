import { test, expect, Page } from '@playwright/test';

/**
 * Exact Reproduction Test
 * Step-by-step reproduction of the exact error the user is experiencing
 */

test('Exact Error Reproduction: Login → Navigate → Add Text → Save Draft', async ({ browser }) => {
  const page = await browser.newPage();

  // Set up logging
  const consoleLogs: Array<{ type: string; msg: string }> = [];
  page.on('console', msg => {
    consoleLogs.push({ type: msg.type(), msg: msg.text() });
  });

  const networkLogs: Array<{ method: string; url: string; status: number }> = [];
  page.on('response', res => {
    if (res.url().includes('asset') || res.url().includes('asset-registry')) {
      networkLogs.push({
        method: res.request().method(),
        url: res.url(),
        status: res.status(),
      });
    }
  });

  try {
    // STEP 1: LOGIN
    console.log('\n========== STEP 1: LOGIN ==========');
    await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    await page.fill('input[id="email"]', 'admin@tobit.local');
    await page.fill('input[id="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log(`✅ Login successful: ${!!token}`);

    // STEP 2: NAVIGATE TO SCREENS
    console.log('\n========== STEP 2: NAVIGATE TO SCREENS ==========');
    await page.goto('http://localhost:3000/admin/screens', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    const screenCount = await page.locator('a[href*="/admin/screens/"]').count();
    console.log(`✅ Found ${screenCount} screens`);

    // STEP 3: CLICK FIRST (맨 위) SCREEN
    console.log('\n========== STEP 3: CLICK FIRST SCREEN ==========');
    const firstScreen = page.locator('a[href*="/admin/screens/"]').first();
    const screenHref = await firstScreen.getAttribute('href');
    console.log(`📍 First screen: ${screenHref}`);

    await firstScreen.click();
    await page.waitForTimeout(3000);
    console.log('✅ Navigated to first screen');

    // STEP 4: ADD TEXT COMPONENT
    console.log('\n========== STEP 4: ADD TEXT COMPONENT FROM PALETTE ==========');
    const textBtn = page.locator('[data-testid="palette-component-text"]');
    await textBtn.waitFor({ timeout: 5000 });
    console.log('📍 Text component button found');

    await textBtn.click();
    await page.waitForTimeout(1000);
    console.log('✅ Text component added');

    // STEP 5: CHECK SAVE DRAFT STATE
    console.log('\n========== STEP 5: CHECK SAVE DRAFT BUTTON ==========');
    const saveBtn = page.locator('[data-testid="btn-save-draft"]');
    const isEnabled = await saveBtn.isEnabled();
    console.log(`📍 Save Draft enabled: ${isEnabled}`);

    if (!isEnabled) {
      throw new Error('Save Draft button should be enabled after adding component');
    }

    // STEP 6: CLICK SAVE DRAFT
    console.log('\n========== STEP 6: CLICK SAVE DRAFT ==========');

    // Clear previous logs
    networkLogs.length = 0;
    consoleLogs.length = 0;

    await saveBtn.click();
    await page.waitForTimeout(3000);

    console.log('✅ Save Draft clicked');

    // STEP 7: ANALYZE RESULTS
    console.log('\n========== STEP 7: ANALYZE NETWORK & CONSOLE ==========');

    console.log('\n--- Network Requests ---');
    networkLogs.forEach((log, idx) => {
      console.log(`[${idx + 1}] ${log.method} ${log.url} → ${log.status}`);
    });

    console.log('\n--- Console Messages ([API] and [EDITOR]) ---');
    const relevantLogs = consoleLogs.filter(
      l => l.msg.includes('[API]') || l.msg.includes('[EDITOR]') || l.type === 'error'
    );
    relevantLogs.forEach(log => {
      console.log(`[${log.type.toUpperCase()}] ${log.msg.substring(0, 200)}`);
    });

    // STEP 8: CHECK FOR ERROR
    console.log('\n========== STEP 8: FINAL RESULT ==========');
    const hasError = consoleLogs.some(l => l.msg.includes('[API] Request failed'));
    const putRequests = networkLogs.filter(r => r.method === 'PUT');
    const postRequests = networkLogs.filter(r => r.method === 'POST');

    console.log(`\n📊 Summary:`);
    console.log(`  PUT requests: ${putRequests.length}`);
    console.log(`  POST requests: ${postRequests.length}`);
    console.log(`  Has API error: ${hasError}`);

    if (putRequests.length === 0) {
      throw new Error('No PUT request made!');
    }

    if (postRequests.length === 0) {
      console.log('\n⚠️  NO POST REQUEST MADE! This is the problem!');
      throw new Error('POST request was not made. Check if 404 is being detected correctly.');
    }

    const postStatus = postRequests[0].status;
    if (postStatus !== 200 && postStatus !== 201) {
      console.log(`\n❌ POST FAILED WITH STATUS ${postStatus}`);
      throw new Error(`POST request failed with status ${postStatus}`);
    }

    console.log('\n✅ SUCCESS: Save Draft completed without error');

  } catch (error) {
    console.log('\n❌ TEST FAILED');
    console.log(`Error: ${error}`);

    // Print all logs for debugging
    console.log('\n=== ALL CONSOLE LOGS ===');
    consoleLogs.forEach(log => {
      console.log(`[${log.type}] ${log.msg}`);
    });

    throw error;
  } finally {
    await page.close();
  }
});
