import { test, expect } from '@playwright/test';

test('UI Creator - Runtime Preview for First_UI', async ({ page, context }) => {
  const errors = {
    console: [] as string[],
    network: [] as string[],
  };

  page.on('console', (msg) => {
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
    if (msg.type() === 'error') {
      errors.console.push(msg.text());
    }
  });

  page.on('response', (response) => {
    if (!response.ok()) {
      const errorMsg = `${response.status()} ${response.url()}`;
      errors.network.push(errorMsg);
      console.log(`[NETWORK ERROR] ${errorMsg}`);
    }
  });

  console.log('📖 Navigating to UI Creator...');
  await page.goto('http://localhost:3000/ui-creator', { waitUntil: 'load' });
  await page.waitForTimeout(2000);

  console.log('🖱️  Clicking First_UI button...');
  const firstUiBtn = page.locator('button').filter({ hasText: /GRID.*First_UI/ }).first();
  await firstUiBtn.click();
  await page.waitForTimeout(2000);

  console.log('🎬 Clicking RUNTIME PREVIEW button...');
  const runtimeBtn = page.locator('button').filter({ hasText: /Runtime Preview/i }).first();
  await runtimeBtn.click();

  await page.waitForTimeout(3000);

  console.log('\n=== 📊 TEST RESULTS ===\n');

  // 성공 여부 확인
  const durationText = await page.locator('text=/Duration.*ms/').isVisible().catch(() => false);
  const errorDisplay = await page.locator('text=/Preview failed|Runtime API not found|Failed to fetch/').isVisible().catch(() => false);

  if (durationText) {
    console.log('✅ RUNTIME PREVIEW: SUCCESS');
    const meta = await page.locator('[class*="text-slate-400"]').filter({ hasText: /Duration/ }).textContent();
    console.log(`   ${meta}`);
  } else if (errorDisplay) {
    console.log('❌ RUNTIME PREVIEW: FAILED');
    const errorMsg = await page.locator('text=/Preview failed|Runtime API not found|Failed to fetch/').first().textContent();
    console.log(`   Error: ${errorMsg}`);
  } else {
    console.log('⏳ RUNTIME PREVIEW: LOADING or NO CLEAR STATE');
  }

  // 네트워크 에러 출력
  if (errors.network.length > 0) {
    console.log('\n🌐 Network Errors:');
    errors.network.forEach(e => console.log(`   - ${e}`));
  }

  // 콘솔 에러 출력
  if (errors.console.length > 0) {
    console.log('\n💻 Console Errors:');
    errors.console.forEach(e => console.log(`   - ${e}`));
  }

  // 페이지 상태 스크린샷
  await page.screenshot({ path: '/tmp/ui-creator-runtime-preview.png' });
  console.log('\n📸 Screenshot: /tmp/ui-creator-runtime-preview.png');

  console.log('\n📝 Check backend logs:');
  console.log('   tail -100 /home/spa/tobit-spa-ai/apps/api/logs/api.log');
});
