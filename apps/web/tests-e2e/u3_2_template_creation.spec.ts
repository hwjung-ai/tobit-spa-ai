import { test, expect, type Page } from "@playwright/test";

const openCreateModal = async (page: Page) => {
  const modal = page.locator('[data-testid="modal-create-screen"]');
  if (await modal.isVisible({ timeout: 1000 }).catch(() => false)) {
    return;
  }
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 10000 });
    await page.click('[data-testid="btn-create-screen"]');
    if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
      return;
    }
    if (attempt === 1) {
      await page.reload({ waitUntil: "domcontentloaded" });
    }
  }
  await modal.waitFor({ state: "visible", timeout: 10000 });
};

const ACTIVE_TEMPLATE_CLASS = /bg-sky-500\/10/;

const createScreenFromModal = async (
  page: Page,
  options: { screenId?: string; screenName: string; templateId?: string | null }
) => {
  await openCreateModal(page);
  if (options.templateId) {
    await page.click(`[data-testid="template-${options.templateId}"]`);
  } else {
    await page.click('[data-testid="template-blank"]');
  }
  if (options.screenId !== undefined) {
    await page.fill('[data-testid="input-screen-id"]', options.screenId);
  }
  await page.fill('[data-testid="input-screen-name"]', options.screenName);

  const createResponsePromise = page.waitForResponse(
    response =>
      response.request().method() === "POST" &&
      response.url().includes("/asset-registry/assets"),
    { timeout: 30000 }
  );
  await page.click('[data-testid="btn-confirm-create"]');
  const createResponse = await createResponsePromise;

  let body: any = null;
  let payload: any = null;
  try {
    body = await createResponse.json();
  } catch {
    body = null;
  }
  try {
    payload = JSON.parse(createResponse.request().postData() || "{}");
  } catch {
    payload = null;
  }
  expect(createResponse.ok(), JSON.stringify(body ?? {})).toBeTruthy();
  return {
    assetId: body?.data?.asset?.asset_id as string | undefined,
    payload,
  };
};

const waitForScreenCreated = async (page: Page, screenName: string) => {
  const targetLink = page.locator(`[data-testid^="link-screen-"]`, { hasText: screenName }).first();
  await targetLink.waitFor({ state: "visible", timeout: 30000 });
};

const openCreatedScreenEditor = async (page: Page, screenName: string) => {
  const targetLink = page.locator(`[data-testid^="link-screen-"]`, { hasText: screenName }).first();
  await targetLink.waitFor({ state: "visible", timeout: 15000 });
  await targetLink.click();
  await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 15000 });
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
    await expect(blankButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    await createScreenFromModal(page, {
      screenId,
      screenName,
      templateId: null,
    });

    // Verify create completion
    await waitForScreenCreated(page, screenName);

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
    await expect(templateButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    const { assetId } = await createScreenFromModal(page, {
      screenId,
      screenName,
      templateId: "readonly_detail",
    });

    if (assetId) {
      await page.goto(`/admin/screens/${assetId}`, { waitUntil: "domcontentloaded" });
      await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 20000 });
    } else {
      await waitForScreenCreated(page, screenName);
      await openCreatedScreenEditor(page, screenName);
    }

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
    await expect(templateButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    const { assetId } = await createScreenFromModal(page, {
      screenId,
      screenName,
      templateId: "list_filter",
    });

    if (assetId) {
      await page.goto(`/admin/screens/${assetId}`, { waitUntil: "domcontentloaded" });
      await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 20000 });
    } else {
      await waitForScreenCreated(page, screenName);
      await openCreatedScreenEditor(page, screenName);
    }

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
    await expect(templateButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    const { assetId } = await createScreenFromModal(page, {
      screenId,
      screenName,
      templateId: "list_modal_crud",
    });

    if (assetId) {
      await page.goto(`/admin/screens/${assetId}`, { waitUntil: "domcontentloaded" });
      await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 20000 });
    } else {
      await waitForScreenCreated(page, screenName);
      await openCreatedScreenEditor(page, screenName);
    }

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
    await expect(blankButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    // Switch to Read-only Detail
    await page.click('[data-testid="template-readonly_detail"]');
    const readonlyButton = page.locator('[data-testid="template-readonly_detail"]');
    await expect(readonlyButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    // Verify blank is no longer selected
    await expect(blankButton).not.toHaveClass(ACTIVE_TEMPLATE_CLASS);

    // Switch to List + Filter
    await page.click('[data-testid="template-list_filter"]');
    const listButton = page.locator('[data-testid="template-list_filter"]');
    await expect(listButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);

    // Verify previous is no longer selected
    await expect(readonlyButton).not.toHaveClass(ACTIVE_TEMPLATE_CLASS);

    // Switch back to Blank
    await page.click('[data-testid="template-blank"]');
    await expect(blankButton).toHaveClass(ACTIVE_TEMPLATE_CLASS);
  });

  test("should create from template without explicit screen id", async ({ page }) => {
    const suffix = Date.now();
    const screenName = `Auto ID Screen ${suffix}`;

    const { payload } = await createScreenFromModal(page, {
      screenName,
      templateId: "readonly_detail",
    });

    expect(typeof payload?.screen_id).toBe("string");
    expect(payload?.screen_id?.length).toBeGreaterThan(0);
    await waitForScreenCreated(page, screenName);
  });
});
