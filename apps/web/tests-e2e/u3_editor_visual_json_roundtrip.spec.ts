import { test, expect } from "@playwright/test";

test.describe("U3 Visual Editor - JSON Roundtrip", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/admin/screens");
    await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 10000 });

    const screenName = "Test Screen 1";
    const screenId = "test-screen-1";
    const screenLink = page.locator('[data-testid^="link-screen-"]', { hasText: screenName }).first();
    const hasScreen = await screenLink.isVisible({ timeout: 2000 }).catch(() => false);

    if (!hasScreen) {
      await page.click('[data-testid="btn-create-screen"]');
      await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 10000 });
      await page.fill('[data-testid="input-screen-id"]', screenId);
      await page.fill('[data-testid="input-screen-name"]', screenName);
      await page.click('[data-testid="btn-confirm-create"]');
      await page.waitForSelector("text=Screen created successfully", { timeout: 10000 });
    }

    const openLink = page.locator('[data-testid^="link-screen-"]', { hasText: screenName }).first();
    await openLink.waitFor({ timeout: 10000 });
    await openLink.click();
    await page.waitForSelector('[data-testid="screen-editor"]', { timeout: 20000 });
  });

  test("should create and persist a screen with components", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('text="JSON"');
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
    await page.click('text="JSON"');
    await page.waitForSelector('[data-testid="json-editor"]');

    // Verify JSON contains the button component
    const textarea = page.locator('[data-testid="json-textarea"]');
    const jsonContent = await textarea.inputValue();
    expect(jsonContent.includes('"type": "button"')).toBeTruthy();
  });

  test("should sync JSON changes back to visual editor", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('text="JSON"');
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
    await page.click('text="Visual"');
    await page.waitForSelector('[data-testid="canvas-list"]');

    // Verify the text component appears in canvas
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(1);
  });

  test("should validate JSON and show errors for invalid structure", async ({ page }) => {
    // Navigate to JSON tab
    await page.click('text="JSON"');
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
    await page.click('text="JSON"');
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
    await page.click('text="JSON"');
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
    await page.click('text="Preview"');
    await page.waitForSelector('[data-testid="preview-renderer"]');

    // Verify components are rendered
    const previewArea = page.locator('[data-testid="preview-renderer"]');
    await expect(previewArea).toBeVisible();
  });

  test("should handle component deletion and sync to JSON", async ({ page }) => {
    // Add a component
    await page.click('[data-testid="palette-component-button"]');
    const componentId = await page.locator('[data-testid^="canvas-component-"]').first().getAttribute('data-testid');

    // Select it
    await page.click(`[${componentId}]`);

    // Delete it using the delete button
    await page.click(`[data-testid="btn-delete-${componentId?.replace('canvas-component-', '')}"]`);

    // Confirm deletion
    await page.on('dialog', dialog => dialog.accept());

    // Verify it's gone from visual
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(0);

    // Verify it's gone from JSON
    await page.click('text="JSON"');
    const textarea = page.locator('[data-testid="json-textarea"]');
    const json = JSON.parse(await textarea.inputValue());
    expect(json.components.length).toBe(0);
  });
});
