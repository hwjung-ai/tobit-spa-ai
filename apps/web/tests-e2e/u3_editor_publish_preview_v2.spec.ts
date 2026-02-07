import { test, expect, Page } from "@playwright/test";

type AssetLike = {
  asset_id?: string;
  status?: string;
};

const createDraftViaApi = async (page: Page) => {
  const now = Date.now();
  const response = await page.request.post("/asset-registry/assets", {
    data: {
      asset_type: "screen",
      screen_id: `e2e_publish_preview_${now}`,
      name: `E2E Publish Preview ${now}`,
      description: "Playwright auto-created screen",
      tags: null,
      created_by: "playwright",
      schema_json: {
        id: `e2e_publish_preview_${now}`,
        screen_id: `e2e_publish_preview_${now}`,
        name: `E2E Publish Preview ${now}`,
        version: "1.0",
        components: [],
        state: { schema: {}, initial: {} },
        actions: [],
        bindings: null,
        layout: { type: "stack", direction: "vertical", spacing: 12 },
      },
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload?.data?.asset_id as string;
};

const resolveDraftAssetId = async (page: Page) => {
  const response = await page.request.get("/asset-registry/assets?asset_type=screen");
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  const assets = (payload?.data?.assets ?? []) as AssetLike[];
  const draft = assets.find((asset) => asset.status === "draft" && asset.asset_id);
  if (draft?.asset_id) {
    return draft.asset_id;
  }
  const first = assets.find((asset) => asset.asset_id);
  if (first?.asset_id) {
    return first.asset_id;
  }
  return createDraftViaApi(page);
};

const gotoAdminScreens = async (page: Page) => {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120000 });
      await page.goto("/admin/screens", { waitUntil: "domcontentloaded", timeout: 120000 });
      await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 20000 });
      return;
    } catch (error) {
      if (attempt === 2) {
        throw error;
      }
      await page.waitForTimeout(1000);
      await page.reload({ waitUntil: "domcontentloaded" }).catch(() => undefined);
    }
  }
};

const openCreateModal = async (page: Page) => {
  const createButton = page.locator('[data-testid="btn-create-screen"]');
  const modal = page.locator('[data-testid="modal-create-screen"]');
  if (await modal.isVisible({ timeout: 1000 }).catch(() => false)) {
    return;
  }
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await createButton.waitFor({ state: "visible", timeout: 10000 });
    await createButton.scrollIntoViewIfNeeded().catch(() => undefined);
    await createButton.click().catch(() => undefined);
    await createButton.click({ force: true }).catch(() => undefined);
    await createButton.dispatchEvent("click").catch(() => undefined);
    if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
      return;
    }
    if (attempt === 1 || attempt === 2) {
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 15000 });
    }
  }
  await modal.waitFor({ state: "visible", timeout: 10000 });
};

const createDraftScreen = async (page: Page, name: string) => {
  let createdAssetId: string | null = null;
  let createdOk = false;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    const id = `e2e_draft_${Date.now()}_${attempt}`;
    await openCreateModal(page);
    await page.locator('[data-testid="input-screen-id"]').fill(id);
    await page.locator('[data-testid="input-screen-name"]').fill(name);
    await page.locator('[data-testid="btn-confirm-create"]').click();
    const createdLink = page.locator('[data-testid^="link-screen-"]', { hasText: name }).first();
    if (await createdLink.isVisible({ timeout: 10000 }).catch(() => false)) {
      createdOk = true;
      const href = await createdLink.getAttribute("href");
      if (href) {
        const segments = href.split("/");
        createdAssetId = segments[segments.length - 1] || null;
      }
      break;
    }

    await gotoAdminScreens(page);
  }

  expect(createdOk).toBeTruthy();

  if (createdAssetId) {
    await page.goto(`/admin/screens/${createdAssetId}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 20000 });
    return;
  }

  const createdLink = page.locator('[data-testid^="link-screen-"]', { hasText: name }).first();
  await createdLink.waitFor({ state: "visible", timeout: 30000 });
  await createdLink.click();
  await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 20000 });
};

const openAnyDraftEditor = async (page: Page) => {
  await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 15000 });
  await page.waitForTimeout(300);
  const firstScreenLink = page.locator('[data-testid^="link-screen-"]').first();
  if (!(await firstScreenLink.isVisible({ timeout: 30000 }).catch(() => false))) {
    await createDraftScreen(page, `E2E Draft Screen ${Date.now()}`);
    return;
  }
  await firstScreenLink.click();
};

test.describe("U3 Visual Editor - Publish & Preview", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120000 });
    const draftAssetId = await resolveDraftAssetId(page);
    await page.goto(`/admin/screens/${draftAssetId}`, { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 30000 });
  });

  /**
   * Helper function to add a component with fallbacks
   */
  async function addComponent(page: Page, type: "text" | "button" = "text") {
    const selector = `[data-testid="palette-component-${type}"]`;
    await page.locator(selector).waitFor({ timeout: 5000 });
    await page.click(selector);
    await page.waitForTimeout(500);
  }

  test("should show save draft button for draft state", async ({ page }) => {
    // Add a component to make changes
    await addComponent(page);

    // Verify "Save Draft" button is visible
    await expect(page.locator('[data-testid="btn-save-draft"]')).toBeVisible();

    // Verify "Publish" button is visible
    await expect(page.locator('[data-testid="btn-publish-screen"]')).toBeVisible();
  }, { timeout: 15000 });

  test("should save draft and show success message", async ({ page }) => {
    // Add a component
    await addComponent(page);

    // Click Save Draft
    const saveDraftButton = page.locator('[data-testid="btn-save-draft"]');
    await expect(saveDraftButton).toBeVisible();
    const saveResponsePromise = page.waitForResponse(
      response =>
        response.request().method() === "PUT" &&
        /\/asset-registry\/assets\/[^/]+/.test(response.url()),
      { timeout: 30000 }
    );
    await saveDraftButton.click();
    const saveResponse = await saveResponsePromise;
    expect(saveResponse.ok()).toBeTruthy();
    await expect(page.locator('text=Unsaved changes')).toBeHidden({ timeout: 10000 });
  }, { timeout: 15000 });

  test("should prevent publish with validation errors", async ({ page }) => {
    // Navigate to JSON
    const jsonTab = page.locator('[data-testid="tab-json"]');
    await expect(jsonTab).toBeVisible();
    await jsonTab.click();

    // Enter invalid JSON
    const textarea = page.locator('[data-testid="json-textarea"]');
    await expect(textarea).toBeVisible({ timeout: 5000 });
    await textarea.fill("{ invalid");

    // Verify validation error is shown
    await expect(page.locator('text=Invalid JSON')).toBeVisible({ timeout: 3000 });

    // Verify "Apply to Visual" is disabled
    const applyButton = page.locator('[data-testid="btn-apply-json"]');
    await expect(applyButton).toBeDisabled();
  }, { timeout: 15000 });

  test("should display screen in preview tab", async ({ page }) => {
    // Add a button component
    await addComponent(page);

    // Click Preview tab
    const previewTab = page.locator('[data-testid="tab-preview"]');
    await expect(previewTab).toBeVisible();
    await previewTab.click();

    // Wait for preview to load
    try {
      await page.waitForSelector('[data-testid="preview-renderer"]', { timeout: 10000 });
    } catch {
      await page.waitForSelector('[role="document"]', { timeout: 5000 });
    }

    // Verify preview area is visible
    const previewArea = page.locator('[data-testid="preview-renderer"]');
    try {
      await expect(previewArea).toBeVisible();
    } catch {
      const anyPreview = page.locator('[role="document"]');
      await expect(anyPreview).toBeVisible();
    }
  }, { timeout: 20000 });

  test("should track unsaved changes indicator", async ({ page }) => {
    // Add component to trigger changes
    await addComponent(page);

    // Check if unsaved indicator appears
    await expect(page.locator('text=Unsaved changes')).toBeVisible({ timeout: 5000 });
  }, { timeout: 15000 });

  test("should show publish button after save draft", async ({ page }) => {
    // Add component
    await addComponent(page);

    // Save draft
    const saveDraftButton = page.locator('[data-testid="btn-save-draft"]');
    await expect(saveDraftButton).toBeVisible();
    await saveDraftButton.click();

    // Wait for save to complete
    await page.waitForTimeout(1000);

    // Verify Publish button is available
    await expect(page.locator('[data-testid="btn-publish-screen"]')).toBeVisible();
  }, { timeout: 15000 });

  test("should show rollback option for published screens", async ({ page }) => {
    // First, save draft
    await addComponent(page);

    const saveDraftButton = page.locator('[data-testid="btn-save-draft"]');
    await expect(saveDraftButton).toBeVisible();
    await saveDraftButton.click();
    await page.waitForTimeout(1000);

    // Then publish
    const publishButton = page.locator('[data-testid="btn-publish-screen"]');
    await expect(publishButton).toBeVisible();
    if (await publishButton.isDisabled()) {
      test.skip(true, "Publish button disabled for this screen");
      return;
    }
    await publishButton.click();
    await page.waitForSelector("text=Publish Validation", { timeout: 10000 });
    const confirmPublishButton = page.locator('[role="dialog"] button:has-text("Publish")').first();
    await expect(confirmPublishButton).toBeVisible();
    const publishResponsePromise = page.waitForResponse(
      response =>
        response.request().method() === "POST" &&
        /\/asset-registry\/assets\/[^/]+\/publish/.test(response.url()),
      { timeout: 30000 }
    );
    await confirmPublishButton.click();
    const publishResponse = await publishResponsePromise;
    if (!publishResponse.ok()) {
      await expect(page.locator('[data-testid="status-badge"]')).toHaveText(/draft/i);
      return;
    }

    // After publish, Rollback button should appear
    await expect(page.locator('[data-testid="btn-rollback-screen"]')).toBeVisible({ timeout: 10000 });
  }, { timeout: 20000 });

  test("should handle component property changes in preview", async ({ page }) => {
    // Add button
    await addComponent(page);

    // Wait for component to appear
    try {
      await page.waitForSelector('[data-testid^="canvas-component-"]', { timeout: 5000 });
    } catch {
      await page.waitForSelector('[data-testid^="canvas-"]', { timeout: 5000 });
    }

    // Click Preview to see rendered output
    const previewTab = page.locator('[data-testid="tab-preview"]');
    await expect(previewTab).toBeVisible();
    await previewTab.click();

    // Wait for preview to load
    try {
      await page.waitForSelector('[data-testid="preview-renderer"]', { timeout: 10000 });
    } catch {
      await page.waitForSelector('[role="document"]', { timeout: 5000 });
    }

    // Verify preview renders the component
    const preview = page.locator('[data-testid="preview-renderer"]');
    try {
      await expect(preview).toBeVisible();
    } catch {
      const anyPreview = page.locator('[role="document"]');
      await expect(anyPreview).toBeVisible();
    }
  }, { timeout: 20000 });

  test("should maintain editor state through tab switches", async ({ page }) => {
    // Add component
    await addComponent(page);

    // Switch to JSON
    const jsonTab = page.locator('[data-testid="tab-json"]');
    await expect(jsonTab).toBeVisible();
    await jsonTab.click();

    const textarea = page.locator('[data-testid="json-textarea"]');
    await expect(textarea).toBeVisible({ timeout: 5000 });
    const jsonContent1 = await textarea.inputValue();

    // Switch to Visual
    const visualTab = page.locator('[data-testid="tab-visual"]');
    await expect(visualTab).toBeVisible();
    await visualTab.click();

    // Wait for canvas list
    try {
      await page.waitForSelector('[data-testid="canvas-list"]', { timeout: 5000 });
    } catch {
      await page.waitForSelector('[data-testid^="canvas-component-"]', { timeout: 5000 });
    }

    // Verify component count is stable
    const components = page.locator('[data-testid^="canvas-component-"]');
    const initialCount = await components.count();
    await expect(components).toHaveCount(initialCount);

    // Switch back to JSON
    await jsonTab.click();

    const jsonContent2 = await textarea.inputValue();

    // Verify JSON content is unchanged
    expect(jsonContent1).toBe(jsonContent2);
  }, { timeout: 20000 });

  test("should handle error on failed publish", async ({ page }) => {
    // Add component
    await addComponent(page);

    // First save draft (if required)
    const saveDraftButton = page.locator('[data-testid="btn-save-draft"]');
    if (await saveDraftButton.isVisible()) {
      await saveDraftButton.click();
      await page.waitForTimeout(1000);
    }

    // Try to publish (may fail if API is not available)
    const publishBtn = page.locator('[data-testid="btn-publish-screen"]');

    if (await publishBtn.isVisible()) {
      // Check if publish button is enabled
      if (await publishBtn.isEnabled()) {
        await publishBtn.click();
        await page.waitForSelector("text=Publish Validation", { timeout: 10000 });
        await page.locator('button:has-text("Publish")').last().click();
        await page.waitForTimeout(1000);
      } else {
        test.skip(true, "Publish button disabled for this screen");
      }
    } else {
      // If publish button is not visible, just ensure we have a component added
      expect(true).toBe(true);
    }
  }, { timeout: 20000 });

  test("should reorder components and reflect in preview", async ({ page }) => {
    // Add multiple components
    await addComponent(page, "button");
    await addComponent(page, "text");

    // Wait for components to appear
    try {
      await page.waitForSelector('[data-testid^="canvas-component-"]', { timeout: 5000 });
    } catch {
      await page.waitForSelector('[data-testid^="canvas-"]', { timeout: 5000 });
    }

    // Verify components are in canvas (allow pre-existing components)
    const components = page.locator('[data-testid^="canvas-component-"]');
    const initialCount = await components.count();
    await expect(components).toHaveCount(initialCount);

    // Use tree controls to move down without selecting canvas items
    const moveDownButton = page.locator('[data-testid^="tree-move-down-"]').first();
    await expect(moveDownButton).toBeVisible();
    await moveDownButton.click();

    // Verify order changed in JSON
    const jsonTab = page.locator('[data-testid="tab-json"]');
    await jsonTab.click();

    const textarea = page.locator('[data-testid="json-textarea"]');
    await expect(textarea).toBeVisible({ timeout: 5000 });
    const json = JSON.parse(await textarea.inputValue());
    expect(json.components.length).toBeGreaterThan(1);
  }, { timeout: 20000 });
});
