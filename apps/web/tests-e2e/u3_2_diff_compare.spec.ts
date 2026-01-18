import { test, expect } from "@playwright/test";

test.describe("U3-2-1: Screen Diff / Compare UI", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to screen editor
    await page.goto("/admin/ui-creator/screen-editor");
    // Wait for editor to load
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });
  });

  test("should show Diff tab with added components", async ({ page }) => {
    // Click on Visual Editor tab
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add a new component (e.g., Text field)
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Text")');

    // Navigate to Diff tab
    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    // Verify Diff content is showing
    const diffContent = await page.locator('[data-testid="diff-content"]');
    await expect(diffContent).toBeVisible();

    // Verify summary shows "added" change
    const summary = await page.locator("text=added");
    await expect(summary).toBeVisible();
    await expect(summary).toContainText("added");

    // Verify green indicator for added items
    const addedItem = await page.locator(".text-green-700");
    await expect(addedItem).toBeVisible();
  });

  test("should show Diff with modified components", async ({ page }) => {
    // Click on Visual Editor tab
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // First publish a screen
    await page.click('button:has-text("Publish")');
    await page.waitForSelector('text=published successfully', { timeout: 10000 });

    // Modify a component (e.g., change label)
    await page.click('[data-testid="component-item-0"]');
    await page.fill('input[placeholder="Label"]', "Updated Label");

    // Navigate to Diff tab
    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    // Verify summary shows "modified" change
    const summary = await page.locator("text=modified");
    await expect(summary).toBeVisible();

    // Verify yellow indicator for modified items
    const modifiedItem = await page.locator(".text-amber-700");
    await expect(modifiedItem).toBeVisible();

    // Verify before/after values are shown
    const changeDetails = await page.locator(".line-through");
    await expect(changeDetails).toBeVisible();
  });

  test("should show accurate diff summary counts", async ({ page }) => {
    // Click on Visual Editor tab
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    // Add multiple components
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Text")');
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Button")');

    // Publish first version
    await page.click('button:has-text("Publish")');
    await page.waitForSelector('text=published successfully', { timeout: 10000 });

    // Make mixed changes: add, remove, modify
    // Add one more
    await page.click('button:has-text("Add Component")');
    await page.click('button:has-text("Input")');

    // Remove one
    await page.click('[data-testid="component-0-delete"]');
    await page.click('button:has-text("Confirm")');

    // Modify one
    await page.click('[data-testid="component-item-1"]');
    await page.fill('input[placeholder="Label"]', "Modified");

    // Navigate to Diff tab
    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    // Verify summary counts
    const summary = await page.locator(".px-4.py-3.bg-slate-50");
    const summaryText = await summary.textContent();

    expect(summaryText).toContain("+"); // added
    expect(summaryText).toContain("-"); // removed
    expect(summaryText).toContain("~"); // modified
  });
});
