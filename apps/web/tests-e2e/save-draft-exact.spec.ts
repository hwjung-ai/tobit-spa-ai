import { test } from '@playwright/test';

test('Exact User Flow: List > First Screen > Add Text > Save Draft', async ({ browser }) => {
  const page = await browser.newPage();

  // Capture all console messages
  const allMessages: string[] = [];
  page.on('console', msg => {
    allMessages.push(`[${msg.type()}] ${msg.text()}`);
    if (msg.text().includes('[API]') || msg.text().includes('[EDITOR]') || msg.text().includes('error')) {
      console.log(`[CONSOLE] ${msg.text().substring(0, 300)}`);
    }
  });

  console.log('\n=== EXACT USER FLOW REPRODUCTION ===\n');

  // Step 1: Login
  console.log('[TEST] Step 1: LOGIN');
  await page.goto('http://localhost:3000/login');
  await page.fill('input[id="email"]', 'admin@tobit.local');
  await page.fill('input[id="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));

  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  console.log(`[TEST] Logged in: ${!!token}`);

  // Step 2: Go to Admin > Screens list
  console.log('[TEST] Step 2: GO TO SCREENS LIST');
  await page.goto('http://localhost:3000/admin/screens');
  await new Promise(r => setTimeout(r, 2000));

  // Get all screens
  const screenRows = await page.locator('a[href*="/admin/screens/"]').count();
  console.log(`[TEST] Found ${screenRows} screens in list`);

  // Step 3: Click on FIRST (맨 위에 있는 것) screen
  console.log('[TEST] Step 3: CLICK FIRST SCREEN IN LIST');
  const firstScreen = page.locator('a[href*="/admin/screens/"]').first();
  const screenHref = await firstScreen.getAttribute('href');
  const screenIdMatch = screenHref?.match(/screens\/([\w-]+)/);
  const screenId = screenIdMatch?.[1];
  console.log(`[TEST] First screen ID: ${screenId}`);
  console.log(`[TEST] Screen href: ${screenHref}`);

  await firstScreen.click();
  await new Promise(r => setTimeout(r, 3000));

  // Step 4: Add Text component from left panel (palette)
  console.log('[TEST] Step 4: ADD TEXT COMPONENT FROM PALETTE');
  const textComponentBtn = page.locator('[data-testid="palette-component-text"]');
  const textBtnVisible = await textComponentBtn.isVisible();
  console.log(`[TEST] Text component button visible: ${textBtnVisible}`);

  if (textBtnVisible) {
    await textComponentBtn.click();
    console.log('[TEST] Clicked Text component button');
    await new Promise(r => setTimeout(r, 1000));
  }

  // Step 5: Check if Save Draft is now enabled
  console.log('[TEST] Step 5: CHECK SAVE DRAFT BUTTON STATE');
  const saveDraftBtn = page.locator('[data-testid="btn-save-draft"]');
  const isDraftBtnEnabled = await saveDraftBtn.isEnabled();
  console.log(`[TEST] Save Draft button enabled: ${isDraftBtnEnabled}`);

  if (isDraftBtnEnabled) {
    // Step 6: Click Save Draft
    console.log('[TEST] Step 6: CLICK SAVE DRAFT');

    // Monitor network requests
    const requests: Array<{ method: string; url: string; status?: number; response?: string }> = [];

    page.on('response', res => {
      if (res.url().includes('asset') || res.url().includes('asset-registry')) {
        requests.push({
          method: res.request().method(),
          url: res.url(),
          status: res.status(),
        });
        console.log(`[NETWORK] ${res.request().method()} ${res.url()} -> ${res.status()}`);
      }
    });

    await saveDraftBtn.click();
    console.log('[TEST] Save Draft button clicked');
    await new Promise(r => setTimeout(r, 3000));

    // Log all network requests
    console.log('\n=== NETWORK REQUESTS ===');
    requests.forEach((req, idx) => {
      console.log(`[${idx + 1}] ${req.method} ${req.url} -> ${req.status}`);
    });

    // Check for PUT request
    const putRequests = requests.filter(r => r.method === 'PUT');
    console.log(`\nPUT requests: ${putRequests.length}`);
    if (putRequests.length > 0) {
      putRequests.forEach(r => console.log(`  - ${r.url}`));
    }

    // Get error messages
    const errorMessages = allMessages.filter(m => m.includes('error') || m.includes('failed'));
    console.log(`\n=== ERROR MESSAGES ===`);
    console.log(`Total errors: ${errorMessages.length}`);
    errorMessages.forEach(msg => console.log(msg));

    // Get editor logs
    const editorLogs = allMessages.filter(m => m.includes('[EDITOR]'));
    console.log(`\n=== EDITOR LOGS ===`);
    editorLogs.forEach(msg => console.log(msg));

    // Get API logs
    const apiLogs = allMessages.filter(m => m.includes('[API]'));
    console.log(`\n=== API LOGS ===`);
    apiLogs.forEach(msg => console.log(msg));

  } else {
    console.log('[ERROR] Save Draft button is disabled!');
    throw new Error('Save Draft button should be enabled after adding component');
  }

  await page.close();
});
