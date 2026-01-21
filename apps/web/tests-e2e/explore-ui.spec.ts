import { test } from '@playwright/test';

test('Explore UI structure', async ({ browser }) => {
  const page = await browser.newPage();

  // Login
  await page.goto('http://localhost:3000/login');
  await page.fill('input[id="email"]', 'admin@tobit.local');
  await page.fill('input[id="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 3000));

  // Go to screen
  await page.goto('http://localhost:3000/admin/screens/5b02c332-dd74-4294-bc3c-be9e46c2ed77');
  await new Promise(r => setTimeout(r, 3000));

  // Get full HTML structure
  const html = await page.evaluate(() => {
    return {
      bodyHTML: document.body.innerHTML.substring(0, 5000),
      hasScreenEditor: !!document.querySelector('[data-testid*="screen"]'),
      allButtons: Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent,
        testId: b.getAttribute('data-testid'),
        disabled: b.disabled,
        class: b.className,
      })),
      allInputs: Array.from(document.querySelectorAll('input')).map(i => ({
        placeholder: i.placeholder,
        type: i.type,
        value: i.value,
        class: i.className,
      })),
    };
  });

  console.log('=== BUTTONS ===');
  html.allButtons.forEach((btn, idx) => {
    console.log(`[${idx}] ${btn.text} | testId: ${btn.testId} | disabled: ${btn.disabled}`);
  });

  console.log('\n=== INPUTS ===');
  html.allInputs.slice(0, 10).forEach((input, idx) => {
    console.log(`[${idx}] placeholder: ${input.placeholder} | type: ${input.type} | value: ${input.value}`);
  });

  console.log('\n=== SCREEN STRUCTURE ===');
  console.log(html.bodyHTML.substring(0, 2000));

  await page.close();
});
