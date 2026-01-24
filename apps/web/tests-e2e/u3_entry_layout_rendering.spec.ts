import { test, expect, type Page } from '@playwright/test';

async function openDraftScreen(page: Page) {
  await page.goto('/admin/screens', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid^="screen-asset-"]', { timeout: 60000 });

  const draftCard = page.locator('[data-testid^="screen-asset-"]').filter({
    has: page.locator('[data-testid^="status-badge-"]', { hasText: 'draft' }),
  }).first();

  if (!(await draftCard.isVisible())) {
    const draftId = `e2e_draft_${Date.now()}`;
    await page.locator('[data-testid="btn-create-screen"]').click();
    const modal = page.locator('[data-testid="modal-create-screen"]');
    await expect(modal).toBeVisible({ timeout: 10000 });
    await modal.locator('[data-testid="input-screen-id"]').fill(draftId);
    await modal.locator('[data-testid="input-screen-name"]').fill('E2E Draft Screen');
    await modal.locator('[data-testid="btn-confirm-create"]').click();
    await expect(modal).toBeHidden({ timeout: 10000 });
  }

  const draftLink = page
    .locator('[data-testid^="screen-asset-"]')
    .filter({ has: page.locator('[data-testid^="status-badge-"]', { hasText: 'draft' }) })
    .first()
    .locator('[data-testid^="link-screen-"]')
    .first();
  await draftLink.waitFor({ timeout: 60000 });
  const href = await draftLink.getAttribute('href');
  if (!href) {
    throw new Error('Draft screen link is missing href.');
  }
  await page.goto(href, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="screen-editor"]', { timeout: 60000 });
}

async function openJsonEditor(page: Page) {
  await page.waitForSelector('[data-testid="screen-editor"]', { timeout: 60000 });
  await page.click('[data-testid="tab-json"]');
  await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 10000 });
}

test.describe('U3-Entry: Layout Rendering E2E', () => {
  test('should render grid layout correctly', async ({ page }) => {
    // Navigate to a screen with grid layout
    // This assumes we have a test screen with grid layout
    const screenId = `grid_layout_test_${Date.now()}`;
    await openDraftScreen(page);
    await openJsonEditor(page);

    // Update schema with grid layout
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    const gridSchema = {
      screen_id: screenId,
      layout: { type: 'grid', cols: 2, gap: 4 },
      components: [
        { id: 'comp1', type: 'text', label: 'Item 1' },
        { id: 'comp2', type: 'text', label: 'Item 2' },
        { id: 'comp3', type: 'text', label: 'Item 3' },
      ],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(gridSchema, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Save draft
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=/Draft saved successfully|Screen draft saved successfully/')).toBeVisible();

    // Verify schema is correctly saved after reload
    await page.reload();
    await openJsonEditor(page);

    // Verify schema shows grid layout
    const savedSchema = JSON.parse(await page.locator('[data-testid="json-textarea"]').inputValue());
    expect(savedSchema.layout.type).toBe('grid');
    expect(savedSchema.layout.cols).toBe(2);
  });

  test('should render vertical stack layout correctly', async ({ page }) => {
    const screenId = `vstack_test_${Date.now()}`;
    await openDraftScreen(page);
    await openJsonEditor(page);

    // Update with vertical stack layout
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    const vStackSchema = {
      screen_id: screenId,
      layout: { type: 'stack', direction: 'vertical', gap: 2 },
      components: [
        { id: 'title', type: 'text', label: 'Title' },
        { id: 'content', type: 'markdown', label: 'Content' },
        { id: 'action', type: 'button', label: 'Submit' },
      ],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(vStackSchema, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Save
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=/Draft saved successfully|Screen draft saved successfully/')).toBeVisible();

    // Verify layout properties
    const savedSchema = JSON.parse(await page.locator('[data-testid="json-textarea"]').inputValue());
    expect(savedSchema.layout.type).toBe('stack');
    expect(savedSchema.layout.direction).toBe('vertical');
  });

  test('should render horizontal stack layout correctly', async ({ page }) => {
    const screenId = `hstack_test_${Date.now()}`;
    await openDraftScreen(page);
    await openJsonEditor(page);

    // Update with horizontal stack layout
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    const hStackSchema = {
      screen_id: screenId,
      layout: { type: 'stack', direction: 'horizontal', gap: 2 },
      components: [
        { id: 'btn1', type: 'button', label: 'Button 1' },
        { id: 'btn2', type: 'button', label: 'Button 2' },
        { id: 'btn3', type: 'button', label: 'Button 3' },
      ],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(hStackSchema, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Save
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=/Draft saved successfully|Screen draft saved successfully/')).toBeVisible();

    // Verify horizontal layout
    const savedSchema = JSON.parse(await page.locator('[data-testid="json-textarea"]').inputValue());
    expect(savedSchema.layout.direction).toBe('horizontal');
  });

  test('should validate layout type in schema', async ({ page }) => {
    const screenId = `invalid_layout_${Date.now()}`;
    await openDraftScreen(page);
    await openJsonEditor(page);

    // Update with invalid layout type
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    const invalidSchema = {
      screen_id: screenId,
      layout: { type: 'invalid_type' },
      components: [],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(invalidSchema, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Should show validation error
    await expect(page.locator('[data-testid="editor-errors"]')).toContainText('must be one of');
  });

  test('should handle list layout with dividers', async ({ page }) => {
    const screenId = `list_layout_${Date.now()}`;
    await openDraftScreen(page);
    await openJsonEditor(page);

    // Update with list layout
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    const listSchema = {
      screen_id: screenId,
      layout: { type: 'list', gap: 2 },
      components: [
        { id: 'item1', type: 'text', label: 'List Item 1' },
        { id: 'divider1', type: 'divider' },
        { id: 'item2', type: 'text', label: 'List Item 2' },
        { id: 'divider2', type: 'divider' },
        { id: 'item3', type: 'text', label: 'List Item 3' },
      ],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(listSchema, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Save
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=/Draft saved successfully|Screen draft saved successfully/')).toBeVisible();

    // Verify list layout type
    const savedSchema = JSON.parse(await page.locator('[data-testid="json-textarea"]').inputValue());
    expect(savedSchema.layout.type).toBe('list');
    expect(savedSchema.components.some((component: { type: string }) => component.type === 'divider')).toBe(true);
  });

  test('should preserve layout when updating screen', async ({ page }) => {
    const screenId = `preserve_layout_${Date.now()}`;
    await openDraftScreen(page);
    await openJsonEditor(page);

    // Set grid layout
    const schemaInput = page.locator('[data-testid="json-textarea"]');
    const gridSchema = {
      screen_id: screenId,
      layout: { type: 'grid', cols: 3, gap: 2 },
      components: [
        { id: 'comp1', type: 'text', label: 'Item 1' },
      ],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(gridSchema, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();
    await page.locator('[data-testid="btn-save-draft"]').click();

    // Update name in JSON
    const updatedSchemaPayload = { ...gridSchema, name: 'Updated Name' };
    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(updatedSchemaPayload, null, 2));
    await page.locator('[data-testid="btn-apply-json"]').click();

    // Save again
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=/Draft saved successfully|Screen draft saved successfully/')).toBeVisible();

    // Verify layout is still there
    const updatedSchema = JSON.parse(await page.locator('[data-testid="json-textarea"]').inputValue());
    expect(updatedSchema.layout.type).toBe('grid');
    expect(updatedSchema.layout.cols).toBe(3);
  });
});
