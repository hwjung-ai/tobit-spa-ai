import { test, expect } from "@playwright/test";

test.describe("OPS Document Search", () => {
  test.beforeEach(async ({ page }) => {
    // Login before running tests
    await page.goto("http://localhost:3000");

    // Check if already logged in
    const currentUrl = page.url();
    if (currentUrl.includes("/login")) {
      await page.fill('input[name="email"]', "admin@example.com");
      await page.fill('input[name="password"]', "admin123");
      await page.click('button[type="submit"]');
      await page.waitForURL("**/admin**", { timeout: 5000 });
    }
  });

  test("should search for documents and display references", async ({ page }) => {
    // Navigate to OPS page
    await page.goto("http://localhost:3000/ops");
    await page.waitForLoadState("networkidle");

    // Select document mode
    await page.click('button:has-text("문서")');

    // Wait for mode selection
    await page.waitForTimeout(500);

    // Search for documents
    await page.fill('[data-testid="ops-query-input"]', "네트워크");

    // Submit search
    await page.click('[data-testid="ops-query-submit"]');

    // Wait for results
    await page.waitForTimeout(5000);

    // Check if references block is displayed
    const referencesBlock = page.locator('[data-testid="references-block"]');
    await expect(referencesBlock).toBeVisible();

    // Check if document items are displayed
    const referenceItems = page.locator('[data-testid="reference-item"]');
    await expect(referenceItems).toHaveCountGreaterThan(0);

    // Check if first item has title, snippet, and URL
    const firstItem = referenceItems.first();
    await expect(firstItem.locator('[data-testid="reference-title"]')).toBeVisible();
    await expect(firstItem.locator('[data-testid="reference-snippet"]')).toBeVisible();

    // Check if the item is clickable (has pointer cursor)
    const itemBox = await firstItem.boundingBox();
    expect(itemBox).toBeTruthy();
  });

  test("should navigate to document viewer when clicking reference", async ({ page }) => {
    // Navigate to OPS page
    await page.goto("http://localhost:3000/ops");
    await page.waitForLoadState("networkidle");

    // Select document mode
    await page.click('button:has-text("문서")');

    // Search for documents
    await page.fill('[data-testid="ops-query-input"]', "네트워크");
    await page.click('[data-testid="ops-query-submit"]');

    // Wait for results
    await page.waitForTimeout(5000);

    // Click on first reference
    const firstReference = page.locator('[data-testid="reference-item"]').first();
    await firstReference.click();

    // Wait for navigation to document viewer
    await page.waitForURL("**/documents/*/viewer**", { timeout: 5000 });

    // Verify document viewer page is loaded
    await expect(page.locator('[data-testid="document-viewer"]')).toBeVisible();
  });

  test("should show hover effect on reference items", async ({ page }) => {
    // Navigate to OPS page
    await page.goto("http://localhost:3000/ops");
    await page.waitForLoadState("networkidle");

    // Select document mode
    await page.click('button:has-text("문서")');

    // Search for documents
    await page.fill('[data-testid="ops-query-input"]', "네트워크");
    await page.click('[data-testid="ops-query-submit"]');

    // Wait for results
    await page.waitForTimeout(5000);

    // Hover over first reference item
    const firstReference = page.locator('[data-testid="reference-item"]').first();
    await firstReference.hover();

    // Check if cursor changes to pointer
    const cursor = await firstReference.evaluate(el => {
      return window.getComputedStyle(el).cursor;
    });
    expect(cursor).toBe("pointer");
  });
});
