import { test, expect } from '@playwright/test';

test.describe('Admin Assets - Filter Persistence', () => {
  test.beforeEach(async ({ page }) => {
    // Admin Assets 페이지로 바로 이동
    await page.goto('/admin/assets', { waitUntil: 'domcontentloaded' });
  });

  test('should preserve filters when navigating to detail page and back', async ({ page }) => {
    // 1. Asset 페이지로 이동 확인 및 로딩 대기
    await expect(page).toHaveURL('/admin/assets');
    
    // Asset이 로드될 때까지 대기 (AG Grid 테이블이 표시될 때까지)
    await page.waitForSelector('.ag-body-container', { timeout: 10000 });
    
    // 2. Asset Type 필터 설정 (예: "prompt")
    // 첫 번째 select는 Asset Type 필터
    const typeSelect = page.locator('select').first();
    await expect(typeSelect).toBeVisible();
    await typeSelect.selectOption('prompt');
    
    // URL 업데이트 대기
    await page.waitForURL(/type=prompt/, { timeout: 5000 });
    
    // 3. Lifecycle 필터 설정 (예: "published")
    // 두 번째 select는 Lifecycle 필터
    const statusSelect = page.locator('select').nth(1);
    await expect(statusSelect).toBeVisible();
    await statusSelect.selectOption('published');
    
    // URL 업데이트 대기
    await page.waitForURL(/type=prompt.*status=published/, { timeout: 5000 });
    
    // 4. 목록에서 첫 번째 자산 클릭하여 상세 페이지로 이동
    const firstAssetName = page.locator('.ag-body-container .ag-row:first-child a').first();
    await expect(firstAssetName).toBeVisible({ timeout: 10000 });
    
    await firstAssetName.click();
    
    // 5. 상세 페이지 URL 확인 (쿼리 파라미터가 포함되어 있는지)
    await page.waitForURL(/\/admin\/assets\//);
    await expect(page).toHaveURL(/type=prompt.*status=published/);
    
    // 6. "Back to Asset List" 버튼 클릭
    const backButton = page.locator('a[href*="/admin/assets"]').first();
    await backButton.click();
    
    // 7. 필터가 유지되었는지 확인
    await page.waitForURL(/type=prompt.*status=published/, { timeout: 5000 });
    
    // 8. 필터 선택값이 여전히 올바른지 확인 (페이지가 다시 로드된 후)
    await page.waitForSelector('select', { timeout: 5000 });
    const typeSelectAfter = page.locator('select').first();
    const statusSelectAfter = page.locator('select').nth(1);
    await expect(typeSelectAfter).toHaveValue('prompt');
    await expect(statusSelectAfter).toHaveValue('published');
    
    console.log('✓ Filter persistence test passed - filters preserved after navigation');
  });

  test('should preserve only type filter when navigating', async ({ page }) => {
    // 1. 페이지 로딩 대기
    await page.waitForSelector('.ag-body-container', { timeout: 10000 });
    
    // 2. Asset Type 필터만 설정
    const typeSelect = page.locator('select').first();
    await typeSelect.selectOption('query');
    await page.waitForURL(/type=query/, { timeout: 5000 });
    
    // 3. 자산 클릭하여 상세 페이지로 이동
    const firstAssetName = page.locator('.ag-body-container .ag-row:first-child a').first();
    await firstAssetName.click();
    
    // 4. 상세 페이지에서 type 파라미터 확인
    await page.waitForURL(/type=query/);
    
    // 5. 뒤로가기
    const backButton = page.locator('a[href*="/admin/assets"]').first();
    await backButton.click();
    
    // 6. 필터 유지 확인
    await page.waitForURL(/type=query/, { timeout: 5000 });
    await page.waitForSelector('select', { timeout: 5000 });
    const typeSelectAfter = page.locator('select').first();
    await expect(typeSelectAfter).toHaveValue('query');
    
    console.log('✓ Type-only filter persistence test passed');
  });

  test('should preserve only status filter when navigating', async ({ page }) => {
    // 1. 페이지 로딩 대기
    await page.waitForSelector('.ag-body-container', { timeout: 10000 });
    
    // 2. Lifecycle 필터만 설정
    const statusSelect = page.locator('select').nth(1);
    await statusSelect.selectOption('draft');
    await page.waitForURL(/status=draft/, { timeout: 5000 });
    
    // 3. 자산 클릭하여 상세 페이지로 이동
    const firstAssetName = page.locator('.ag-body-container .ag-row:first-child a').first();
    await firstAssetName.click();
    
    // 4. 상세 페이지에서 status 파라미터 확인
    await page.waitForURL(/status=draft/);
    
    // 5. 뒤로가기
    const backButton = page.locator('a[href*="/admin/assets"]').first();
    await backButton.click();
    
    // 6. 필터 유지 확인
    await page.waitForURL(/status=draft/, { timeout: 5000 });
    await page.waitForSelector('select', { timeout: 5000 });
    const statusSelectAfter = page.locator('select').nth(1);
    await expect(statusSelectAfter).toHaveValue('draft');
    
    console.log('✓ Status-only filter persistence test passed');
  });
});