import { test, expect } from '@playwright/test';

test.describe('Admin Assets - Filter Persistence', () => {
  test.beforeEach(async ({ page }) => {
    // 로그인 처리 (필요한 경우)
    await page.goto('/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/admin/assets');
  });

  test('should preserve filters when navigating to detail page and back', async ({ page }) => {
    // 1. Asset 페이지로 이동 확인
    await expect(page).toHaveURL('/admin/assets');
    
    // 2. Asset Type 필터 설정 (예: "prompt")
    const typeSelect = page.locator('select').filter({ hasText: 'All Categories' });
    await typeSelect.selectOption('prompt');
    await page.waitForTimeout(500);
    
    // URL에 쿼리 파라미터가 추가되었는지 확인
    await expect(page).toHaveURL(/type=prompt/);
    
    // 3. Lifecycle 필터 설정 (예: "published")
    const statusSelect = page.locator('select').filter({ hasText: 'Any Status' });
    await statusSelect.selectOption('published');
    await page.waitForTimeout(500);
    
    // URL에 두 쿼리 파라미터가 모두 있는지 확인
    await expect(page).toHaveURL(/type=prompt.*status=published/);
    
    // 4. 목록에서 첫 번째 자산 클릭하여 상세 페이지로 이동
    // AG Grid 테이블의 첫 번째 행 클릭
    const firstAssetName = page.locator('.ag-body-container .ag-row:first-child a').first();
    await expect(firstAssetName).toBeVisible({ timeout: 10000 });
    const assetNameText = await firstAssetName.textContent();
    
    await firstAssetName.click();
    await page.waitForTimeout(1000);
    
    // 5. 상세 페이지 URL 확인 (쿼리 파라미터가 포함되어 있는지)
    await expect(page).toHaveURL(/\/admin\/assets\//);
    await expect(page).toHaveURL(/type=prompt.*status=published/);
    
    // 6. "Back to Asset List" 버튼 클릭
    const backButton = page.locator('a[href*="/admin/assets"]').first();
    await backButton.click();
    await page.waitForTimeout(1000);
    
    // 7. 필터가 유지되었는지 확인
    await expect(page).toHaveURL(/type=prompt.*status=published/);
    
    // 8. 필터 선택값이 여전히 올바른지 확인
    await expect(typeSelect).toHaveValue('prompt');
    await expect(statusSelect).toHaveValue('published');
    
    console.log('✓ Filter persistence test passed - filters preserved after navigation');
  });

  test('should preserve only type filter when navigating', async ({ page }) => {
    // 1. Asset Type 필터만 설정
    const typeSelect = page.locator('select').filter({ hasText: 'All Categories' });
    await typeSelect.selectOption('query');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveURL(/type=query/);
    
    // 2. 자산 클릭하여 상세 페이지로 이동
    const firstAssetName = page.locator('.ag-body-container .ag-row:first-child a').first();
    await expect(firstAssetName).toBeVisible({ timeout: 10000 });
    await firstAssetName.click();
    await page.waitForTimeout(1000);
    
    // 3. 상세 페이지에서 type 파라미터 확인
    await expect(page).toHaveURL(/type=query/);
    
    // 4. 뒤로가기
    const backButton = page.locator('a[href*="/admin/assets"]').first();
    await backButton.click();
    await page.waitForTimeout(1000);
    
    // 5. 필터 유지 확인
    await expect(page).toHaveURL(/type=query/);
    await expect(typeSelect).toHaveValue('query');
    
    console.log('✓ Type-only filter persistence test passed');
  });

  test('should preserve only status filter when navigating', async ({ page }) => {
    // 1. Lifecycle 필터만 설정
    const statusSelect = page.locator('select').filter({ hasText: 'Any Status' });
    await statusSelect.selectOption('draft');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveURL(/status=draft/);
    
    // 2. 자산 클릭하여 상세 페이지로 이동
    const firstAssetName = page.locator('.ag-body-container .ag-row:first-child a').first();
    await expect(firstAssetName).toBeVisible({ timeout: 10000 });
    await firstAssetName.click();
    await page.waitForTimeout(1000);
    
    // 3. 상세 페이지에서 status 파라미터 확인
    await expect(page).toHaveURL(/status=draft/);
    
    // 4. 뒤로가기
    const backButton = page.locator('a[href*="/admin/assets"]').first();
    await backButton.click();
    await page.waitForTimeout(1000);
    
    // 5. 필터 유지 확인
    await expect(page).toHaveURL(/status=draft/);
    await expect(statusSelect).toHaveValue('draft');
    
    console.log('✓ Status-only filter persistence test passed');
  });
});