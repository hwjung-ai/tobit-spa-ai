import { expect, test } from "@playwright/test";

test.describe("SIM Workspace", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3000/sim");

    if (page.url().includes("/login")) {
      await page.fill('input[name="email"]', "admin@example.com");
      await page.fill('input[name="password"]', "admin123");
      await page.click('button[type="submit"]');
      await page.waitForLoadState("networkidle");
      await page.goto("http://localhost:3000/sim");
    }
  });

  test("should render SIM page and run a simulation", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "SIM Workspace" })).toBeVisible();
    await expect(page.locator('[data-testid="simulation-question-input"]')).toBeVisible();

    await page.fill(
      '[data-testid="simulation-question-input"]',
      "트래픽이 15% 증가하면 지표가 어떻게 변하는지 알려줘"
    );

    await page.click('[data-testid="simulation-run-button"]');

    await expect(page.locator('[data-testid="simulation-kpi-summary"]')).toBeVisible();
    await expect(page.locator('[data-testid="simulation-evidence-panel"]')).toBeVisible();
  });

  test("should support DL strategy and backtest action", async ({ page }) => {
    await page.getByRole("button", { name: "DL" }).click();
    await page.click('[data-testid="simulation-run-button"]');
    await expect(page.locator("text=Confidence:")).toBeVisible();

    await page.click('[data-testid="simulation-backtest-button"]');
    await expect(page.locator("text=Backtest Report")).toBeVisible();
  });
});
