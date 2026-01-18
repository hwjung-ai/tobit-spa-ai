import { test, expect } from "@playwright/test";

test.describe("U3-2-2: Safe Publish Gate", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to screen editor
    await page.goto("/admin/ui-creator/screen-editor");
    // Wait for editor to load
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });
  });

  test("should allow publish when all validation checks pass", async ({ page }) => {
    // Create a valid screen
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add a simple component
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Text")');

    // Click publish
    await page.click('[data-testid="btn-publish-screen"]');

    // Publish Gate Modal should open
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Verify all checks are running
    await page.waitForSelector('text=Schema Validation', { timeout: 5000 });
    await page.waitForSelector('text=Binding Validation', { timeout: 5000 });
    await page.waitForSelector('text=Action Validation', { timeout: 5000 });

    // Wait for checks to complete
    await page.waitForSelector('text=pass', { timeout: 10000 });

    // Verify Publish button is enabled
    const publishButton = page.locator('button:has-text("Publish")').last();
    await expect(publishButton).toBeEnabled();

    // Click publish to confirm
    await publishButton.click();

    // Verify success toast
    await page.waitForSelector('text=published successfully', { timeout: 10000 });
  });

  test("should block publish when binding validation fails", async ({ page }) => {
    // Create a screen with invalid binding
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add a component
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Text")');

    // Try to add invalid binding (reference non-existent state)
    // This would be done through the UI if available
    // For now, we simulate by directly modifying JSON
    await page.click('[data-testid="tab-json"]');
    const jsonEditor = await page.locator('[data-testid="json-editor-content"]');
    await jsonEditor.click();

    // Add invalid binding to JSON
    const currentJson = await page.locator('textarea').inputValue();
    const modified = currentJson.replace(
      '"props": {}',
      '"props": { "text": "{{state.nonexistent}}" }'
    );
    await page.locator('textarea').fill(modified);

    // Try to publish
    await page.click('[data-testid="btn-publish-screen"]');
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Wait for validation checks to complete
    await page.waitForSelector('text=Binding Validation', { timeout: 10000 });

    // Verify binding validation fails (red indicator)
    const failIndicator = await page.locator('.text-red-700:has-text("Binding Validation")');
    await expect(failIndicator).toBeVisible();

    // Verify Publish button is disabled
    const publishButton = page.locator('button:has-text("Publish")').last();
    await expect(publishButton).toBeDisabled();
  });

  test("should block publish when action validation fails", async ({ page }) => {
    // Create a screen with invalid action handler
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add a button component
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Button")');

    // Add an action with invalid handler
    // This would require access to the action editor UI
    // For now, we simulate by modifying JSON
    await page.click('[data-testid="tab-json"]');
    const jsonEditor = await page.locator('[data-testid="json-editor-content"]');
    await jsonEditor.click();

    // Add invalid action to JSON
    const currentJson = await page.locator('textarea').inputValue();
    const modified = currentJson.replace(
      '"actions": []',
      '"actions": [{"id": "invalid_action", "handler": "InvalidActionHandler", "payload_template": {}}]'
    );
    await page.locator('textarea').fill(modified);

    // Try to publish
    await page.click('[data-testid="btn-publish-screen"]');
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Wait for validation checks to complete
    await page.waitForSelector('text=Action Validation', { timeout: 10000 });

    // Verify action validation shows issues (red or yellow indicator)
    const validationResult = await page.locator('.text-amber-700, .text-red-700');
    await expect(validationResult).toContainText('Action Validation');
  });

  test("should allow publish with warnings from dry-run", async ({ page }) => {
    // Create a valid screen structure
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add basic component
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Text")');

    // Save and publish
    await page.click('button:has-text("Save Draft")');
    await page.waitForSelector('text=saved successfully', { timeout: 5000 });

    // Click publish
    await page.click('[data-testid="btn-publish-screen"]');
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Wait for all checks including dry-run
    await page.waitForSelector('text=Dry-Run Test', { timeout: 10000 });

    // Verify checks are displayed
    const checklistItems = await page.locator('[data-testid="validation-check"]');
    expect(await checklistItems.count()).toBeGreaterThanOrEqual(4);

    // Should be able to publish if no hard failures
    const publishButton = page.locator('button:has-text("Publish")').last();
    const isEnabled = await publishButton.isEnabled();
    expect(isEnabled).toBeTruthy();
  });
});
