import { test, expect, type Page } from '@playwright/test';

async function openJsonEditor(page: Page) {
  await page.waitForSelector('[data-testid="screen-editor"]', { timeout: 20000 });
  await page.click('[data-testid="tab-json"]');
  await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 10000 });
}

test.describe('U3-Entry: Screen Asset Lifecycle E2E', () => {
  const testScreenId = `test_screen_${Date.now()}`;
  // createdAssetId tracking - to be implemented in future tests

  test.beforeEach(async ({ page }) => {
    // Navigate to screens admin page
    await page.goto('/admin/screens');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display screen asset list', async ({ page }) => {
    // Verify page title and elements are present
    await expect(page.locator('text=Screen Asset Management')).toBeVisible();
    await expect(page.locator('[data-testid="btn-create-screen"]')).toBeVisible();
    await expect(page.locator('[data-testid="input-search-screens"]')).toBeVisible();
    await expect(page.locator('[data-testid="select-filter-status"]')).toBeVisible();
  });

  test('should create a new screen draft', async ({ page }) => {
    // Click create button
    await page.locator('[data-testid="btn-create-screen"]').click();

    // Verify modal is shown
    const modal = page.locator('[data-testid="modal-create-screen"]');
    await expect(modal).toBeVisible();

    // Fill in create form
    await page.locator('[data-testid="input-screen-id"]').fill(testScreenId);
    await page.locator('[data-testid="input-screen-name"]').fill('Test Screen');
    await page.locator('[data-testid="input-screen-description"]').fill('This is a test screen');

    // Confirm creation
    await page.locator('[data-testid="btn-confirm-create"]').click();

    // Wait for success message
    await expect(page.locator('text=Screen created successfully')).toBeVisible();

    // Extract asset ID from the rendered screen card
    const screenCard = page.locator(`[data-testid="screen-asset-"]`).first();
    await expect(screenCard).toBeVisible();
  });

  test('should edit screen draft', async ({ page }) => {
    // Create a screen first
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`${testScreenId}_edit`);
    await page.locator('[data-testid="input-screen-name"]').fill('Edit Test Screen');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    // Wait for screen to be created
    await page.waitForTimeout(1000);

    // Click edit button on the newly created screen
    const editBtn = page.locator('[data-testid^="btn-edit-"]').first();
    await editBtn.click();

    // Verify editor page
    await openJsonEditor(page);
    await expect(page.locator('[data-testid="json-textarea"]')).toBeVisible();

    // Edit screen name via JSON
    const nameInput = page.locator('[data-testid="json-textarea"]');
    const currentJson = await nameInput.inputValue();
    const parsed = JSON.parse(currentJson);
    parsed.name = 'Updated Screen Name';
    await nameInput.clear();
    await nameInput.fill(JSON.stringify(parsed, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Save draft
    await page.locator('[data-testid="btn-save-draft"]').click();

    // Wait for save confirmation
    await expect(page.locator('text=/Draft saved successfully|Screen draft saved successfully/')).toBeVisible();

    // Verify name was updated
    const updatedJson = await nameInput.inputValue();
    expect(updatedJson).toContain('"Updated Screen Name"');
  });

  test('should validate schema on save', async ({ page }) => {
    // Create and navigate to edit
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`${testScreenId}_validate`);
    await page.locator('[data-testid="input-screen-name"]').fill('Validation Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await openJsonEditor(page);

    // Break the schema JSON
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    await schemaInput.clear();
    await schemaInput.fill('{ invalid json }');

    // Try to save
    await page.locator('[data-testid="btn-save-draft"]').click();

    // Verify error is shown
    await expect(page.locator('text=/Invalid JSON|Parse error/')).toBeVisible();
  });

  test('should publish screen', async ({ page }) => {
    // Create a screen
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`${testScreenId}_publish`);
    await page.locator('[data-testid="input-screen-name"]').fill('Publish Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);

    // Navigate to edit
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await openJsonEditor(page);

    // Publish the screen
    await page.locator('[data-testid="btn-publish-screen"]').click();

    // Verify success message
    await expect(page.locator('text=Screen published successfully')).toBeVisible();

    // Verify status changed to published
    await page.goto('/admin/screens');
    await page.waitForLoadState('domcontentloaded');

    // Look for published status badge
    const publishedBadges = page.locator('text=published');
    const publishedCount = await publishedBadges.count();
    expect(publishedCount).toBeGreaterThan(0);
  });

  test('should not allow editing published screen', async ({ page }) => {
    // Create and publish a screen
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`${testScreenId}_readonly`);
    await page.locator('[data-testid="input-screen-name"]').fill('Read Only Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await openJsonEditor(page);
    await page.locator('[data-testid="btn-publish-screen"]').click();

    // Refresh page to see updated state
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Verify editor shows read-only state
    await expect(page.locator('text=Published screens are read-only')).toBeVisible();
    await expect(page.locator('[data-testid="btn-save-draft"]')).toHaveCount(0);
  });

  test('should rollback published screen to draft', async ({ page }) => {
    // Create and publish a screen
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`${testScreenId}_rollback`);
    await page.locator('[data-testid="input-screen-name"]').fill('Rollback Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await openJsonEditor(page);
    await page.locator('[data-testid="btn-publish-screen"]').click();

    // Reload and rollback
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Click rollback button
    const rollbackBtn = page.locator('[data-testid="btn-rollback-screen"]');
    await expect(rollbackBtn).toBeVisible();
    await rollbackBtn.click();

    // Confirm dialog
    await page.on('dialog', dialog => dialog.accept());

    // Verify rollback success
    await expect(page.locator('text=Screen rolled back to draft')).toBeVisible();

    // Verify editor is back to draft mode
    await expect(page.locator('[data-testid="btn-save-draft"]')).toBeVisible();
  });

  test('should search screens by ID', async ({ page }) => {
    // Create a few test screens
    for (let i = 0; i < 2; i++) {
      await page.locator('[data-testid="btn-create-screen"]').click();
      await page.locator('[data-testid="input-screen-id"]').fill(`search_test_${i}_${Date.now()}`);
      await page.locator('[data-testid="input-screen-name"]').fill(`Search Test ${i}`);
      await page.locator('[data-testid="btn-confirm-create"]').click();
      await page.waitForTimeout(500);
    }

    // Search for one of them
    const searchInput = page.locator('[data-testid="input-search-screens"]');
    await searchInput.fill('search_test_0');

    // Verify results are filtered
    await page.waitForTimeout(500);
    const screens = page.locator('[data-testid^="screen-asset-"]');
    const count = await screens.count();
    expect(count).toBeLessThanOrEqual(1);
  });

  test('should filter screens by status', async ({ page }) => {
    // Filter by draft
    const statusSelect = page.locator('[data-testid="select-filter-status"]');
    await statusSelect.selectOption('draft');

    // Wait for filtering
    await page.waitForTimeout(500);

    // Verify only draft screens are shown (if any exist)
    // screenCards locator - awaiting use in assertions
    const draftBadges = page.locator('[data-testid^="status-badge-"]');

    for (let i = 0; i < await draftBadges.count(); i++) {
      const badge = draftBadges.nth(i);
      await expect(badge).toContainText('draft');
    }
  });
});
