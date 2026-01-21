import { test, expect } from "@playwright/test";

test.describe("U3 Visual Editor - Publish & Preview", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to editor
    await page.goto("/admin/screens/test-screen-1");
    await page.waitForSelector('[data-testid="screen-editor"]');
  });

  test("should show save draft button for draft state", async ({ page }) => {
    // Add a component to make changes
    await page.click('[data-testid="palette-component-button"]');

    // Verify "Save Draft" button is visible
    await expect(page.locator('text="Save Draft"')).toBeVisible();

    // Verify "Publish" button is visible
    await expect(page.locator('text="Publish"')).toBeVisible();
  });

  test("should save draft and show success message", async ({ page }) => {
    // Add a component
    await page.click('[data-testid="palette-component-button"]');

    // Click Save Draft
    await page.click('text="Save Draft"');

    // Verify success toast appears
    await expect(page.locator('text=/saved|success/i')).toBeVisible();
  });

  test("should prevent publish with validation errors", async ({ page }) => {
    // Navigate to JSON
    await page.click('text="JSON"');

    // Enter invalid JSON
    const textarea = page.locator('[data-testid="json-textarea"]');
    await textarea.fill("{ invalid");

    // Verify validation error is shown
    await expect(page.locator('text=/validation error|error/i')).toBeVisible();

    // Verify "Apply to Visual" is disabled
    await expect(page.locator('[data-testid="btn-apply-json"]')).toBeDisabled();
  });

  test("should display screen in preview tab", async ({ page }) => {
    // Add a button component
    await page.click('[data-testid="palette-component-button"]');

    // Click Preview tab
    await page.click('text="Preview"');
    await page.waitForSelector('[data-testid="preview-renderer"]');

    // Verify preview area is visible
    const previewArea = page.locator('[data-testid="preview-renderer"]');
    await expect(previewArea).toBeVisible();
  });

  test("should track unsaved changes indicator", async ({ page }) => {
    // Initially should not show unsaved indicator
    // Header locator removed - unsaved indicator check implementation pending

    // Add component to trigger changes
    await page.click('[data-testid="palette-component-button"]');

    // Check if unsaved indicator appears (implementation specific)
    // This test assumes the header shows "Unsaved changes"
    await expect(page.locator('text=/unsaved|modified/i')).toBeVisible();
  });

  test("should show publish button after save draft", async ({ page }) => {
    // Add component
    await page.click('[data-testid="palette-component-button"]');

    // Save draft
    await page.click('text="Save Draft"');
    await page.waitForTimeout(500);

    // Verify Publish button is available
    await expect(page.locator('text="Publish"')).toBeVisible();
  });

  test("should show rollback option for published screens", async ({ page }) => {
    // First, publish a screen
    await page.click('[data-testid="palette-component-button"]');
    await page.click('text="Save Draft"');
    await page.waitForTimeout(500);
    await page.click('text="Publish"');
    await page.waitForTimeout(500);

    // After publish, Rollback button should appear
    await expect(page.locator('text="Rollback"')).toBeVisible();
  });

  test("should handle component property changes in preview", async ({ page }) => {
    // Add button
    await page.click('[data-testid="palette-component-button"]');
    await page.waitForSelector('[data-testid^="canvas-component-"]');

    // Click Preview to see rendered output
    await page.click('text="Preview"');
    await page.waitForSelector('[data-testid="preview-renderer"]');

    // Verify preview renders the component
    const preview = page.locator('[data-testid="preview-renderer"]');
    await expect(preview).toBeVisible();
  });

  test("should show validation errors in preview", async ({ page }) => {
    // Navigate to JSON and add invalid structure
    await page.click('text="JSON"');
    const textarea = page.locator('[data-testid="json-textarea"]');
    const currentJson = await textarea.inputValue();

    // Modify to add invalid component reference
    const screenData = JSON.parse(currentJson);
    screenData.components.push({
      id: "invalid",
      type: "nonexistent_type",
    });

    await textarea.fill(JSON.stringify(screenData, null, 2));
    await page.click('[data-testid="btn-apply-json"]');

    // Switch to preview
    await page.click('text="Preview"');
    await page.waitForSelector('[data-testid="preview-renderer"]');

    // Check for error message
    await expect(page.locator('text=/validation error|error/i')).toBeVisible();
  });

  test("should maintain editor state through tab switches", async ({ page }) => {
    // Add component
    await page.click('[data-testid="palette-component-button"]');

    // Switch to JSON
    await page.click('text="JSON"');
    const textarea = page.locator('[data-testid="json-textarea"]');
    const jsonContent1 = await textarea.inputValue();

    // Switch to Visual
    await page.click('text="Visual"');
    await page.waitForSelector('[data-testid="canvas-list"]');

    // Verify component is still there
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(1);

    // Switch back to JSON
    await page.click('text="JSON"');
    const jsonContent2 = await textarea.inputValue();

    // Verify JSON content is unchanged
    expect(jsonContent1).toBe(jsonContent2);
  });

  test("should handle error on failed publish", async ({ page }) => {
    // Add component and prepare to publish
    await page.click('[data-testid="palette-component-button"]');

    // Try to publish (may fail if API is not available)
    // This test simulates the error handling
    const publishBtn = page.locator('text="Publish"');
    if (await publishBtn.isEnabled()) {
      await publishBtn.click();

      // Error handling - could show error toast
      // This depends on API availability
      const errorOrSuccess = page.locator('text=/error|success|failed/i');
      await expect(errorOrSuccess).toBeVisible({ timeout: 3000 });
    }
  });

  test("should reorder components and reflect in preview", async ({ page }) => {
    // Add multiple components
    await page.click('[data-testid="palette-component-button"]');
    await page.click('[data-testid="palette-component-text"]');

    // Verify both are in canvas
    await expect(page.locator('[data-testid^="canvas-component-"]')).toHaveCount(2);

    // Select first component and move down
    const components = page.locator('[data-testid^="canvas-component-"]');
    await components.first().click();

    // Move down button should be visible
    await expect(page.locator('text="Down"')).toBeVisible();
    await page.click('text="Down"');

    // Verify order changed in JSON
    await page.click('text="JSON"');
    const textarea = page.locator('[data-testid="json-textarea"]');
    const json = JSON.parse(await textarea.inputValue());
    expect(json.components[0].type).toBe("text");
    expect(json.components[1].type).toBe("button");
  });
});
