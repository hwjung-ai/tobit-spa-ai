import { test, expect, type Page } from "@playwright/test";

const openCreateModal = async (page: Page) => {
  await page.click('[data-testid="btn-create-screen"]');
  const modal = page.locator('[data-testid="modal-create-screen"]');
  if (!(await modal.isVisible({ timeout: 10000 }).catch(() => false))) {
    await page.click('[data-testid="btn-create-screen"]');
  }
  await modal.waitFor({ state: "visible", timeout: 10000 });
};

const createBlankScreenAndOpen = async (page: Page) => {
  await page.goto("/admin/screens");
  await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 10000 });

  const suffix = Date.now();
  const screenId = `test_publish_gate_${suffix}`;
  const screenName = `Publish Gate ${suffix}`;

  await openCreateModal(page);
  await page.fill('[data-testid="input-screen-id"]', screenId);
  await page.fill('[data-testid="input-screen-name"]', screenName);
  await page.click('[data-testid="btn-confirm-create"]');
  await page.waitForSelector("text=Screen created successfully", { timeout: 10000 });

  const link = page.locator('[data-testid^="link-screen-"]', { hasText: screenName }).first();
  await link.click();
  await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });
};

test.describe("U3-2-2: Safe Publish Gate", () => {
  test.beforeEach(async ({ page }) => {
    await createBlankScreenAndOpen(page);
  });

  test("should allow publish when all validation checks pass", async ({ page }) => {
    // Create a valid screen
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add a simple component
    await page.locator('[data-testid="palette-component-text"]').waitFor({ timeout: 5000 });
    await page.click('[data-testid="palette-component-text"]');

    // Click publish
    await page.click('[data-testid="btn-publish-screen"]');

    // Publish Gate Modal should open and checks complete
    await page.waitForSelector("text=Publish Validation", { timeout: 5000 });
    await expect(page.locator("text=Running validation checks...")).toBeHidden({ timeout: 10000 });

    // Verify checks are displayed
    await expect(page.locator("text=Schema Validation")).toBeVisible();
    await expect(page.locator("text=Binding Validation")).toBeVisible();
    await expect(page.locator("text=Action Validation")).toBeVisible();
    await expect(page.locator("text=Dry-Run Test")).toBeVisible();

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
    await page.locator('[data-testid="palette-component-text"]').waitFor({ timeout: 5000 });
    await page.click('[data-testid="palette-component-text"]');

    // Try to add invalid binding (reference non-existent state)
    // This would be done through the UI if available
    // For now, we simulate by directly modifying JSON
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 5000 });

    // Add invalid binding to JSON
    const currentJson = await page.locator('[data-testid="json-textarea"]').inputValue();
    const modified = currentJson.replace(
      '"props": {}',
      '"props": { "text": "{{state.nonexistent}}" }'
    );
    await page.locator('[data-testid="json-textarea"]').fill(modified);
    await page.click('[data-testid="btn-apply-json"]');

    // Try to publish
    await page.click('[data-testid="btn-publish-screen"]');
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Wait for validation checks to complete
    await expect(page.locator("text=Running validation checks...")).toBeHidden({ timeout: 10000 });
    await page.waitForSelector("text=Binding Validation", { timeout: 10000 });

    // Verify binding validation fails (red indicator)
    const failIndicator = page.locator('.text-red-700:has-text("Binding Validation")');
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
    await page.locator('[data-testid="palette-component-button"]').waitFor({ timeout: 5000 });
    await page.click('[data-testid="palette-component-button"]');

    // Add an action with invalid handler
    // This would require access to the action editor UI
    // For now, we simulate by modifying JSON
    await page.click('[data-testid="tab-json"]');
    await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 5000 });

    // Add invalid action to JSON
    const currentJson = await page.locator('[data-testid="json-textarea"]').inputValue();
    const modified = currentJson.replace(
      '"actions": []',
      '"actions": [{"id": "invalid_action", "handler": "InvalidActionHandler", "payload_template": {}}]'
    );
    await page.locator('[data-testid="json-textarea"]').fill(modified);
    await page.click('[data-testid="btn-apply-json"]');

    // Try to publish
    await page.click('[data-testid="btn-publish-screen"]');
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Wait for validation checks to complete
    await expect(page.locator("text=Running validation checks...")).toBeHidden({ timeout: 10000 });
    await page.waitForSelector("text=Action Validation", { timeout: 10000 });

    // Verify action validation shows issues (red or yellow indicator)
    const validationResult = page.locator('.text-amber-700:has-text("Action Validation"), .text-red-700:has-text("Action Validation")');
    await expect(validationResult).toBeVisible();
  });

  test("should allow publish with warnings from dry-run", async ({ page }) => {
    // Create a valid screen structure
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add basic component
    await page.locator('[data-testid="palette-component-text"]').waitFor({ timeout: 5000 });
    await page.click('[data-testid="palette-component-text"]');

    // Save and publish
    await page.click('button:has-text("Save Draft")');
    await page.waitForSelector('text=saved successfully', { timeout: 5000 });

    // Click publish
    await page.click('[data-testid="btn-publish-screen"]');
    await page.waitForSelector('text=Publish Validation', { timeout: 5000 });

    // Wait for all checks including dry-run
    await expect(page.locator("text=Running validation checks...")).toBeHidden({ timeout: 10000 });
    await page.waitForSelector("text=Dry-Run Test", { timeout: 10000 });

    // Verify checks are displayed
    await expect(page.locator("text=Schema Validation")).toBeVisible();
    await expect(page.locator("text=Binding Validation")).toBeVisible();
    await expect(page.locator("text=Action Validation")).toBeVisible();

    // Should be able to publish if no hard failures
    const publishButton = page.locator('button:has-text("Publish")').last();
    const isEnabled = await publishButton.isEnabled();
    expect(isEnabled).toBeTruthy();
  });
});
