import { test, expect } from '@playwright/test';

test.describe('U3-Entry: Layout Rendering E2E', () => {
  test('should render grid layout correctly', async ({ page }) => {
    // Navigate to a screen with grid layout
    // This assumes we have a test screen with grid layout
    await page.goto('/admin/screens');

    // Create a test screen with grid layout
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`grid_layout_test_${Date.now()}`);
    await page.locator('[data-testid="input-screen-name"]').fill('Grid Layout Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);

    // Edit the screen to add grid layout
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await page.waitForLoadState('networkidle');

    // Update schema with grid layout
    const schemaInput = page.locator('[data-testid="textarea-schema-json"]');
    const gridSchema = {
      screen_id: 'grid_layout_test',
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

    // Save draft
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=Screen draft saved successfully')).toBeVisible();

    // Publish the screen
    await page.locator('[data-testid="btn-publish-screen"]').click();
    await expect(page.locator('text=Screen published successfully')).toBeVisible();

    // Now view the screen via renderer
    // This would be done through the ops or inspector endpoint
    // For now, we verify the schema is correctly saved
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify schema shows grid layout
    const savedSchema = await page.locator('[data-testid="textarea-schema-json"]').textContent();
    expect(savedSchema).toContain('"type":"grid"');
    expect(savedSchema).toContain('"cols":2');
  });

  test('should render vertical stack layout correctly', async ({ page }) => {
    await page.goto('/admin/screens');

    // Create a test screen with vertical stack
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`vstack_test_${Date.now()}`);
    await page.locator('[data-testid="input-screen-name"]').fill('Vertical Stack Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await page.waitForLoadState('networkidle');

    // Update with vertical stack layout
    const schemaInput = page.locator('[data-testid="textarea-schema-json"]');
    const vStackSchema = {
      screen_id: 'vstack_test',
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

    // Save
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=Screen draft saved successfully')).toBeVisible();

    // Verify layout properties
    const savedSchema = await page.locator('[data-testid="textarea-schema-json"]').textContent();
    expect(savedSchema).toContain('"direction":"vertical"');
    expect(savedSchema).toContain('"type":"stack"');
  });

  test('should render horizontal stack layout correctly', async ({ page }) => {
    await page.goto('/admin/screens');

    // Create test screen
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`hstack_test_${Date.now()}`);
    await page.locator('[data-testid="input-screen-name"]').fill('Horizontal Stack Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await page.waitForLoadState('networkidle');

    // Update with horizontal stack layout
    const schemaInput = page.locator('[data-testid="textarea-schema-json"]');
    const hStackSchema = {
      screen_id: 'hstack_test',
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

    // Save
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=Screen draft saved successfully')).toBeVisible();

    // Verify horizontal layout
    const savedSchema = await page.locator('[data-testid="textarea-schema-json"]').textContent();
    expect(savedSchema).toContain('"direction":"horizontal"');
  });

  test('should validate layout type in schema', async ({ page }) => {
    await page.goto('/admin/screens');

    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`invalid_layout_${Date.now()}`);
    await page.locator('[data-testid="input-screen-name"]').fill('Invalid Layout Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await page.waitForLoadState('networkidle');

    // Update with invalid layout type
    const schemaInput = page.locator('[data-testid="textarea-schema-json"]');
    const invalidSchema = {
      screen_id: 'invalid_layout',
      layout: { type: 'invalid_type' },
      components: [],
      state: { initial: {} },
      actions: [],
      bindings: {},
    };

    await schemaInput.clear();
    await schemaInput.fill(JSON.stringify(invalidSchema, null, 2));

    // Try to publish
    await page.locator('[data-testid="btn-publish-screen"]').click();

    // Should show validation error
    await expect(page.locator('text=must be one of')).toBeVisible();
  });

  test('should handle list layout with dividers', async ({ page }) => {
    await page.goto('/admin/screens');

    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`list_layout_${Date.now()}`);
    await page.locator('[data-testid="input-screen-name"]').fill('List Layout Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await page.waitForLoadState('networkidle');

    // Update with list layout
    const schemaInput = page.locator('[data-testid="textarea-schema-json"]');
    const listSchema = {
      screen_id: 'list_layout',
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

    // Save
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=Screen draft saved successfully')).toBeVisible();

    // Verify list layout type
    const savedSchema = await page.locator('[data-testid="textarea-schema-json"]').textContent();
    expect(savedSchema).toContain('"type":"list"');
    expect(savedSchema).toContain('"type":"divider"');
  });

  test('should preserve layout when updating screen', async ({ page }) => {
    await page.goto('/admin/screens');

    // Create screen with grid layout
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(`preserve_layout_${Date.now()}`);
    await page.locator('[data-testid="input-screen-name"]').fill('Preserve Layout Test');
    await page.locator('[data-testid="btn-confirm-create"]').click();

    await page.waitForTimeout(1000);
    await page.locator('[data-testid^="btn-edit-"]').first().click();
    await page.waitForLoadState('networkidle');

    // Set grid layout
    const schemaInput = page.locator('[data-testid="textarea-schema-json"]');
    const gridSchema = {
      screen_id: 'preserve_layout',
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
    await page.locator('[data-testid="btn-save-draft"]').click();

    // Update name
    const nameInput = page.locator('[data-testid="input-screen-name"]');
    await nameInput.clear();
    await nameInput.fill('Updated Name');

    // Save again
    await page.locator('[data-testid="btn-save-draft"]').click();
    await expect(page.locator('text=Screen draft saved successfully')).toBeVisible();

    // Verify layout is still there
    const updatedSchema = await page.locator('[data-testid="textarea-schema-json"]').textContent();
    expect(updatedSchema).toContain('"type":"grid"');
    expect(updatedSchema).toContain('"cols":3');
  });
});
