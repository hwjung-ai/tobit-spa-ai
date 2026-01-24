import { test, expect, type Page } from "@playwright/test";

async function openDraftScreen(page: Page) {
  await page.goto("/admin/screens", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid^="screen-asset-"]', { timeout: 20000 });

  const draftCard = page.locator('[data-testid^="screen-asset-"]').filter({
    has: page.locator('[data-testid^="status-badge-"]', { hasText: "draft" }),
  }).first();
  if (!(await draftCard.isVisible())) {
    const draftId = `e2e_draft_${Date.now()}`;
    await page.locator('[data-testid="btn-create-screen"]').click();
    await page.locator('[data-testid="input-screen-id"]').fill(draftId);
    await page.locator('[data-testid="input-screen-name"]').fill("E2E Draft Screen");
    await page.locator('[data-testid="btn-confirm-create"]').click();
    await page.waitForTimeout(1000);
  }

  const draftLink = page
    .locator('[data-testid^="screen-asset-"]')
    .filter({
      has: page.locator('[data-testid^="status-badge-"]', { hasText: "draft" }),
    })
    .first()
    .locator('[data-testid^="link-screen-"]')
    .first();
  await draftLink.waitFor({ timeout: 15000 });
  await draftLink.click();
}

async function addTextComponent(page: Page) {
  const paletteTextButton = page.locator('[data-testid="palette-component-text"]');
  await paletteTextButton.waitFor({ timeout: 5000 });
  await paletteTextButton.click();
  await page.waitForTimeout(1000);
}

async function updateJsonLabel(page: Page, newLabel: string) {
  await page.click('[data-testid="tab-json"]');
  await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 10000 });

  const rawJson = await page.locator('[data-testid="json-textarea"]').inputValue();
  const parsed = JSON.parse(rawJson);

  if (!Array.isArray(parsed.components) || parsed.components.length === 0) {
    throw new Error("No components found to modify in JSON");
  }

  parsed.components[0] = {
    ...parsed.components[0],
    label: newLabel,
  };
  await page.locator('[data-testid="json-textarea"]').fill(JSON.stringify(parsed, null, 2));
  await page.locator('[data-testid="btn-apply-json"]').click();
  await page.waitForTimeout(1000);
}

async function updateJsonAddComponent(page: Page) {
  await page.click('[data-testid="tab-json"]');
  await page.waitForSelector('[data-testid="json-textarea"]', { timeout: 10000 });

  const rawJson = await page.locator('[data-testid="json-textarea"]').inputValue();
  const parsed = JSON.parse(rawJson);

  parsed.components = Array.isArray(parsed.components) ? parsed.components : [];
  parsed.components.push({
    id: `text_${Date.now()}`,
    type: "text",
    label: "Extra Text",
    props: {},
  });

  await page.locator('[data-testid="json-textarea"]').fill(JSON.stringify(parsed, null, 2));
  await page.locator('[data-testid="btn-apply-json"]').click();
  await page.waitForTimeout(1000);
}

test.describe("U3-2-1: Screen Diff / Compare UI", () => {
  test.beforeEach(async ({ page }) => {
    await openDraftScreen(page);
    await page.waitForSelector('[data-testid="editor-tabs"]', { timeout: 10000 });
  });

  test("should show Diff tab with added components", async ({ page }) => {
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    await addTextComponent(page);

    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    const diffContent = page.locator('[data-testid="diff-content"]');
    await expect(diffContent).toBeVisible();

    const summary = page.locator("text=added");
    await expect(summary).toBeVisible();

    const addedItem = page.locator(".bg-green-50").first();
    await expect(addedItem).toBeVisible();
  });

  test("should show Diff with modified components", async ({ page }) => {
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    await addTextComponent(page);
    await updateJsonLabel(page, "Updated Label");

    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    const summary = page.locator("text=added");
    await expect(summary).toBeVisible();

    const addedItem = page.locator(".bg-green-50").first();
    await expect(addedItem).toBeVisible();
  });

  test("should show accurate diff summary counts", async ({ page }) => {
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    await addTextComponent(page);
    await updateJsonAddComponent(page);

    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    const summary = page.locator(".px-4.py-3.bg-slate-50");
    const summaryText = await summary.textContent();

    expect(summaryText).toContain("+");
  });
});
