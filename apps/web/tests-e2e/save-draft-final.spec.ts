import { test, expect, Page } from '@playwright/test';

test('Save Draft - Full Detailed Test', async ({ browser }) => {
  const page = await browser.newPage();

  // Console monitoring
  const allConsoleMessages: string[] = [];
  page.on('console', msg => {
    allConsoleMessages.push(`[${msg.type()}] ${msg.text()}`);
  });

  // Network monitoring
  const networkRequests: Array<{ method: string; url: string; status?: number }> = [];
  page.on('response', res => {
    networkRequests.push({
      method: res.request().method(),
      url: res.url(),
      status: res.status(),
    });
  });

  console.log('[TEST] === LOGIN ===');
  await page.goto('http://localhost:3000/login');
  await page.fill('input[id="email"]', 'admin@tobit.local');
  await page.fill('input[id="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));

  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  console.log(`[TEST] Logged in: ${!!token}`);

  console.log('[TEST] === OPEN SCREEN ===');
  await page.goto('http://localhost:3000/admin/screens/5b02c332-dd74-4294-bc3c-be9e46c2ed77');
  await new Promise(r => setTimeout(r, 3000));

  // Step 1: Check initial state
  console.log('[TEST] === CHECK INITIAL STATE ===');
  let state = await page.evaluate(() => {
    const saveDraftBtn = document.querySelector('[data-testid="btn-save-draft"]') as HTMLButtonElement;
    return {
      saveDraftDisabled: saveDraftBtn?.disabled || false,
      saveDraftText: saveDraftBtn?.textContent || '',
      hasUnsavedIndicator: document.body.innerText.includes('Unsaved changes'),
    };
  });
  console.log(`[TEST] Initial state: `, state);

  // Step 2: Click on palette component to add it
  console.log('[TEST] === ADD TEXT COMPONENT ===');
  const textComponentButton = page.locator('[data-testid="palette-component-text"]');
  console.log('[TEST] Clicking "Text" button from palette');
  await textComponentButton.click();
  await new Promise(r => setTimeout(r, 1000));

  // Check state after adding component
  state = await page.evaluate(() => {
    const saveDraftBtn = document.querySelector('[data-testid="btn-save-draft"]') as HTMLButtonElement;
    return {
      saveDraftDisabled: saveDraftBtn?.disabled || false,
      saveDraftText: saveDraftBtn?.textContent || '',
      hasUnsavedIndicator: document.body.innerText.includes('Unsaved changes'),
      numButtons: document.querySelectorAll('button').length,
    };
  });
  console.log(`[TEST] After adding component: `, state);

  // Step 3: Check if Save Draft is now enabled
  if (!state.saveDraftDisabled) {
    console.log('[TEST] === ATTEMPTING SAVE DRAFT ===');

    // Capture network requests during save
    const saveStartTime = Date.now();
    const requestsBefore = networkRequests.length;

    // Get Save Draft button
    const saveDraftBtn = page.locator('[data-testid="btn-save-draft"]');

    // Monitor for API errors
    const apiErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('[API]')) {
        apiErrors.push(msg.text());
      }
    });

    // Click Save Draft
    console.log('[TEST] Clicking Save Draft...');
    await saveDraftBtn.click();
    await new Promise(r => setTimeout(r, 3000));

    const saveEndTime = Date.now();
    console.log(`[TEST] Save took ${saveEndTime - saveStartTime}ms`);

    // Check final state
    const finalState = await page.evaluate(() => {
      const saveDraftBtn = document.querySelector('[data-testid="btn-save-draft"]') as HTMLButtonElement;
      return {
        saveDraftDisabled: saveDraftBtn?.disabled || false,
        saveDraftText: saveDraftBtn?.textContent || '',
        hasUnsavedIndicator: document.body.innerText.includes('Unsaved changes'),
        hasSavingText: document.body.innerText.includes('Saving'),
      };
    });
    console.log(`[TEST] Final state: `, finalState);

    // Check network requests
    const newRequests = networkRequests.filter(r => {
      const url = r.url.toLowerCase();
      return url.includes('asset') || url.includes('draft');
    });

    console.log(`\n[TEST] === ASSET REQUESTS ===`);
    console.log(`Total requests made: ${networkRequests.length}`);
    console.log(`Asset-related requests: ${newRequests.length}`);
    newRequests.forEach((req, idx) => {
      console.log(`[${idx + 1}] ${req.method} ${req.url} -> ${req.status}`);
    });

    // Check for PUT request
    const putRequests = newRequests.filter(r => r.method === 'PUT');
    console.log(`\nPUT requests: ${putRequests.length}`);
    if (putRequests.length > 0) {
      putRequests.forEach(r => {
        console.log(`  ${r.url}`);
      });
    }

    // Check for errors
    console.log(`\n[TEST] === ERRORS ===`);
    console.log(`API errors from console: ${apiErrors.length}`);
    if (apiErrors.length > 0) {
      console.log('Error messages:');
      apiErrors.forEach(err => console.log(`  ${err}`));
    }

    // Print relevant console logs
    const relevantLogs = allConsoleMessages.filter(m =>
      m.includes('[API]') || m.includes('[EDITOR]') || m.includes('error')
    );
    console.log(`\n[TEST] === RELEVANT CONSOLE LOGS ===`);
    relevantLogs.forEach(log => console.log(log));

    // Assertion
    expect(putRequests.length).toBeGreaterThan(0);
  } else {
    console.log('[ERROR] Save Draft button is still disabled after adding component!');
    console.log('[ERROR] This indicates the isDirty state is not being updated');

    // Print all console messages to debug
    console.log('\n[TEST] === ALL CONSOLE MESSAGES ===');
    allConsoleMessages.forEach(msg => console.log(msg));

    throw new Error('Save Draft button should be enabled after adding component');
  }

  await page.close();
});
