import { test, expect } from "@playwright/test";

test.describe("Admin Status Badge Consistency", () => {
  test("assets/tools status badges use fixed compact height class", async ({ page }) => {
    await page.goto("/admin/assets", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);

    const assetStatusBadge = page
      .locator('.ag-row .ag-cell[col-id="status"] span')
      .first();

    if ((await assetStatusBadge.count()) > 0) {
      await expect(assetStatusBadge).toHaveClass(/h-5/);
    }

    await page.goto("/admin/tools", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(500);

    const toolStatusBadge = page
      .locator('.ag-row .ag-cell[col-id="status"] span')
      .first();

    if ((await toolStatusBadge.count()) > 0) {
      await expect(toolStatusBadge).toHaveClass(/h-5/);
    }
  });
});
