import { test, expect } from "@playwright/test";

test.describe("U3-2-4: Template-based Screen Creation", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to screens page
    await page.goto("/admin/screens");
    // Wait for screens panel to load
    await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 10000 });
  });

  test("should create blank screen when no template is selected", async ({ page }) => {
    // Click create screen button
    await page.click('[data-testid="btn-create-screen"]');

    // Wait for create modal
    await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 5000 });

    // Verify blank template is selected by default
    const blankButton = page.locator('[data-testid="template-blank"]');
    await expect(blankButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', "test_blank_screen");
    await page.fill('[data-testid="input-screen-name"]', "Test Blank Screen");

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success toast
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Verify screen appears in list
    await expect(page.locator('text=Test Blank Screen')).toBeVisible();
  });

  test("should create screen from Read-only Detail template", async ({ page }) => {
    // Click create screen button
    await page.click('[data-testid="btn-create-screen"]');

    // Wait for create modal
    await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 5000 });

    // Select Read-only Detail template
    await page.click('[data-testid="template-readonly_detail"]');

    // Verify template is selected (highlighted)
    const templateButton = page.locator('[data-testid="template-readonly_detail"]');
    await expect(templateButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', "test_readonly_detail");
    await page.fill('[data-testid="input-screen-name"]', "Device Details");

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Open the created screen in editor
    await page.click('text=Device Details');
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });

    // Navigate to JSON tab to verify template content
    await page.click('[data-testid="tab-json"]');
    const jsonContent = await page.locator('[data-testid="json-editor-content"]').textContent();

    // Verify template components are present
    expect(jsonContent).toContain("device_id");
    expect(jsonContent).toContain("device_name");
    expect(jsonContent).toContain("state");
  });

  test("should create screen from List + Filter template", async ({ page }) => {
    // Click create screen button
    await page.click('[data-testid="btn-create-screen"]');

    // Wait for create modal
    await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 5000 });

    // Select List + Filter template
    await page.click('[data-testid="template-list_filter"]');

    // Verify template is selected
    const templateButton = page.locator('[data-testid="template-list_filter"]');
    await expect(templateButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', "test_list_filter");
    await page.fill('[data-testid="input-screen-name"]', "Device List");

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Open the created screen
    await page.click('text=Device List');
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });

    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    const jsonContent = await page.locator('[data-testid="json-editor-content"]').textContent();

    // Verify DataGrid component is present
    expect(jsonContent).toContain("DataGrid");
    expect(jsonContent).toContain("search_term");
    expect(jsonContent).toContain("items");
  });

  test("should create screen from List + Modal CRUD template", async ({ page }) => {
    // Click create screen button
    await page.click('[data-testid="btn-create-screen"]');

    // Wait for create modal
    await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 5000 });

    // Select List + Modal CRUD template
    await page.click('[data-testid="template-list_modal_crud"]');

    // Verify template is selected
    const templateButton = page.locator('[data-testid="template-list_modal_crud"]');
    await expect(templateButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', "test_crud_modal");
    await page.fill('[data-testid="input-screen-name"]', "Device Management");

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Open the created screen
    await page.click('text=Device Management');
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });

    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    const jsonContent = await page.locator('[data-testid="json-editor-content"]').textContent();

    // Verify CRUD components are present
    expect(jsonContent).toContain("Modal");
    expect(jsonContent).toContain("Create New");
    expect(jsonContent).toContain("modal_open");
    expect(jsonContent).toContain("form_name");
  });

  test("should switch between templates in create modal", async ({ page }) => {
    // Click create screen button
    await page.click('[data-testid="btn-create-screen"]');

    // Wait for create modal
    await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 5000 });

    // Start with Blank
    const blankButton = page.locator('[data-testid="template-blank"]');
    await expect(blankButton).toHaveClass(/bg-sky-900/);

    // Switch to Read-only Detail
    await page.click('[data-testid="template-readonly_detail"]');
    const readonlyButton = page.locator('[data-testid="template-readonly_detail"]');
    await expect(readonlyButton).toHaveClass(/bg-sky-900/);

    // Verify blank is no longer selected
    await expect(blankButton).not.toHaveClass(/bg-sky-900/);

    // Switch to List + Filter
    await page.click('[data-testid="template-list_filter"]');
    const listButton = page.locator('[data-testid="template-list_filter"]');
    await expect(listButton).toHaveClass(/bg-sky-900/);

    // Verify previous is no longer selected
    await expect(readonlyButton).not.toHaveClass(/bg-sky-900/);

    // Switch back to Blank
    await page.click('[data-testid="template-blank"]');
    await expect(blankButton).toHaveClass(/bg-sky-900/);
  });
});
