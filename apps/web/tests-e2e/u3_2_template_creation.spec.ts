import { test, expect, type Page } from "@playwright/test";

const openCreateModal = async (page: Page) => {
  await page.click('[data-testid="btn-create-screen"]');
  const modal = page.locator('[data-testid="modal-create-screen"]');
  if (!(await modal.isVisible({ timeout: 10000 }).catch(() => false))) {
    await page.click('[data-testid="btn-create-screen"]');
  }
  await modal.waitFor({ state: "visible", timeout: 10000 });
};

test.describe("U3-2-4: Template-based Screen Creation", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to screens page
    await page.goto("/admin/screens");
    // Wait for screens panel to load
    await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 10000 });
  });

  test("should create blank screen when no template is selected", async ({ page }) => {
    const suffix = Date.now();
    const screenId = `test_blank_screen_${suffix}`;
    const screenName = `Test Blank Screen ${suffix}`;

    // Click create screen button
    await openCreateModal(page);

    // Verify blank template is selected by default
    const blankButton = page.locator('[data-testid="template-blank"]');
    await expect(blankButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', screenId);
    await page.fill('[data-testid="input-screen-name"]', screenName);

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success toast
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Verify screen appears in list
    await expect(page.locator(`[data-testid^="link-screen-"]`, { hasText: screenName }).first()).toBeVisible();
  });

  test("should create screen from Read-only Detail template", async ({ page }) => {
    const suffix = Date.now();
    const screenId = `test_readonly_detail_${suffix}`;
    const screenName = `Device Details ${suffix}`;

    // Click create screen button
    await openCreateModal(page);

    // Select Read-only Detail template
    await page.click('[data-testid="template-readonly_detail"]');

    // Verify template is selected (highlighted)
    const templateButton = page.locator('[data-testid="template-readonly_detail"]');
    await expect(templateButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', screenId);
    await page.fill('[data-testid="input-screen-name"]', screenName);

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Open the created screen in editor
    await page.click(`text=${screenName}`);
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
    const suffix = Date.now();
    const screenId = `test_list_filter_${suffix}`;
    const screenName = `Device List ${suffix}`;

    // Click create screen button
    await openCreateModal(page);

    // Select List + Filter template
    await page.click('[data-testid="template-list_filter"]');

    // Verify template is selected
    const templateButton = page.locator('[data-testid="template-list_filter"]');
    await expect(templateButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', screenId);
    await page.fill('[data-testid="input-screen-name"]', screenName);

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Open the created screen
    await page.click(`text=${screenName}`);
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });

    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    const jsonContent = await page.locator('[data-testid="json-editor-content"]').textContent();

    // Verify table component is present
    expect(jsonContent).toContain('"type": "table"');
    expect(jsonContent).toContain("Data Grid");
    expect(jsonContent).toContain("search_term");
    expect(jsonContent).toContain("items");
  });

  test("should create screen from List + Modal CRUD template", async ({ page }) => {
    const suffix = Date.now();
    const screenId = `test_crud_modal_${suffix}`;
    const screenName = `Device Management ${suffix}`;

    // Click create screen button
    await openCreateModal(page);

    // Select List + Modal CRUD template
    await page.click('[data-testid="template-list_modal_crud"]');

    // Verify template is selected
    const templateButton = page.locator('[data-testid="template-list_modal_crud"]');
    await expect(templateButton).toHaveClass(/bg-sky-900/);

    // Fill in form
    await page.fill('[data-testid="input-screen-id"]', screenId);
    await page.fill('[data-testid="input-screen-name"]', screenName);

    // Create screen
    await page.click('[data-testid="btn-confirm-create"]');

    // Verify success
    await page.waitForSelector('text=Screen created successfully', { timeout: 10000 });

    // Open the created screen
    await page.click(`text=${screenName}`);
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
    await openCreateModal(page);

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
