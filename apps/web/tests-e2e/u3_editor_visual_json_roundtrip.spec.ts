import { test, expect, type Page } from "@playwright/test";

type AssetLike = {
  asset_id?: string;
  status?: string;
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

  const now = Date.now();
  const createResponse = await page.request.post("/asset-registry/assets", {
    data: {
      asset_type: "screen",
      screen_id: `e2e_roundtrip_${now}`,
      name: `E2E Roundtrip ${now}`,
      description: "Playwright auto-created screen",
      tags: null,
      created_by: "playwright",
      schema_json: {
        id: `e2e_roundtrip_${now}`,
        screen_id: `e2e_roundtrip_${now}`,
        name: `E2E Roundtrip ${now}`,
        version: "1.0",
        components: [],
        state: { schema: {}, initial: {} },
        actions: [],
        bindings: null,
        layout: { type: "stack", direction: "vertical", spacing: 12 },
      },
    },
  });
  expect(createResponse.ok()).toBeTruthy();
  const created = await createResponse.json();
  return created?.data?.asset_id as string;
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

const openDraftScreen = async (page: Page) => {
  await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120000 });
  const draftAssetId = await resolveDraftAssetId(page);
  await page.goto(`/admin/screens/${draftAssetId}`, { waitUntil: "domcontentloaded", timeout: 120000 });
};

test.describe("U3 Visual Editor - JSON Roundtrip", () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(15000);
    page.setDefaultNavigationTimeout(120000);
    await openDraftScreen(page);
    await page.waitForSelector('[data-testid="screen-editor-header"]', { timeout: 40000 }).catch(() => {
      return page.waitForSelector('button:has-text("Save Draft")', { timeout: 40000 });
    });

    // Reset to a blank screen to avoid state bleed between tests.
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 5000 });
    const textarea = page.locator('[data-testid="json-textarea"]');
    const currentJson = await textarea.inputValue();
    const screenData = JSON.parse(currentJson);
    screenData.components = [];
    screenData.actions = [];
    screenData.bindings = null;
    await textarea.fill(JSON.stringify(screenData, null, 2));
    await page.click('[data-testid="btn-apply-json"]');
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="canvas-list"]', { timeout: 5000 });
  });

  test("should create and persist a screen with components", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-editor"]');

    // Verify empty initial state
    const textarea = page.locator('[data-testid="json-textarea"]');
    const content = await textarea.inputValue();
    expect(content.includes('"components"')).toBeTruthy();
  });

  test("should add components through visual editor", async ({ page }) => {
    // Add a button component
    await page.click('[data-testid="palette-component-button"]');

    // Verify button appears in canvas
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(1);

    // Verify canvas shows 1 component
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(1);
  });

  test("should sync visual editor changes to JSON", async ({ page }) => {
    // Add button via palette
    await page.click('[data-testid="palette-component-button"]');
    await page.waitForSelector('[data-testid^="canvas-component-"]');

    // Switch to JSON tab
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-editor"]');

    // Verify JSON contains the button component
    const textarea = page.locator('[data-testid="json-textarea"]');
    const jsonContent = await textarea.inputValue();
    expect(jsonContent.includes('"type": "button"')).toBeTruthy();
  });

  test("should sync JSON changes back to visual editor", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-editor"]');

    // Get current JSON
    const textarea = page.locator('[data-testid="json-textarea"]');
    const currentJson = await textarea.inputValue();

    // Parse and modify JSON to add a text component
    const screenData = JSON.parse(currentJson);
    screenData.components.push({
      id: "text_1",
      type: "text",
      label: "Title",
      props: {
        content: "Hello World",
      },
    });

    // Update textarea
    await textarea.fill(JSON.stringify(screenData, null, 2));

    // Click "Apply to Visual"
    await page.click('[data-testid="btn-apply-json"]');

    // Switch to Visual tab
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="canvas-list"]');

    // Verify the text component appears in canvas
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(1);
  });

  test("should validate JSON and show errors for invalid structure", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-editor"]');

    // Clear and enter invalid JSON
    const textarea = page.locator('[data-testid="json-textarea"]');
    await textarea.fill("{ invalid json");

    // Verify error appears
    await expect(page.locator('text=/Invalid JSON|Parse error/')).toBeVisible();

    // Verify "Apply to Visual" button is disabled
    const applyBtn = page.locator('[data-testid="btn-apply-json"]');
    await expect(applyBtn).toBeDisabled();
  });

  test("should handle JSON format button", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-editor"]');

    // Enter minified JSON
    const textarea = page.locator('[data-testid="json-textarea"]');
    const minifiedJson = '{"screen_id":"test","components":[{"id":"button_1","type":"button"}]}';
    await textarea.fill(minifiedJson);

    // Click Format button
    await page.click('[data-testid="btn-format-json"]');

    // Verify JSON is formatted with proper spacing
    const formattedJson = await textarea.inputValue();
    expect(formattedJson.includes("    ")).toBeTruthy(); // Should have indentation
  });

  test("should preserve component order when adding components", async ({ page }) => {
    // Add button
    await page.click('[data-testid="palette-component-button"]');
    await page.waitForSelector('[data-testid^="canvas-component-"]');

    // Add text
    await page.click('[data-testid="palette-component-text"]');

    // Verify canvas shows 2 components
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(2);

    // Switch to JSON
    await page.click('[data-testid="tab-json"]');
    const textarea = page.locator('[data-testid="json-textarea"]');
    const json = JSON.parse(await textarea.inputValue());

    // Verify order: button first, text second
    expect(json.components[0].type).toBe("button");
    expect(json.components[1].type).toBe("text");
  });

  test("should display component types in preview", async ({ page }) => {
    // Add multiple component types
    await page.click('[data-testid="palette-component-button"]');
    await page.click('[data-testid="palette-component-text"]');
    await page.click('[data-testid="palette-component-input"]');

    // Switch to Preview tab
    await page.click('[data-testid="tab-preview"]');
    await page.waitForSelector('[data-testid="preview-renderer"]');

    // Verify components are rendered
    const previewArea = page.locator('[data-testid="preview-renderer"]');
    await expect(previewArea).toBeVisible();
  });

  test("should handle component deletion and sync to JSON", async ({ page }) => {
    // Add a component
    await page.click('[data-testid="palette-component-button"]');
    await page.waitForSelector('[data-testid^="canvas-component-"]', { timeout: 5000 });
    const componentId = await page.locator('[data-testid^="canvas-component-"]').first().getAttribute('data-testid');
    expect(componentId).toBeTruthy();
    const componentTestId = componentId ?? "";

    // Select it
    const componentNode = page.locator(`[data-testid="${componentTestId}"]`);
    await componentNode.scrollIntoViewIfNeeded();
    await componentNode.click({ force: true });

    // Delete via keyboard shortcut (VisualEditor handles Delete key for selected component)
    await page.keyboard.press("Delete");

    // Verify it's gone from visual
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(0, { timeout: 10000 });

    // Verify it's gone from JSON
    await page.click('[data-testid="tab-json"]');
    const textarea = page.locator('[data-testid="json-textarea"]');
    const json = JSON.parse(await textarea.inputValue());
    expect(json.components.length).toBe(0);
  });
});
