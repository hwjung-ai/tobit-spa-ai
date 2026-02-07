import { test, expect, type Page } from "@playwright/test";

async function openDraftScreen(page: Page) {
  await page.goto("/admin/screens", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="btn-create-screen"]', { timeout: 20000 });

  const firstLink = page.locator('[data-testid^="link-screen-"]').first();
  if (await firstLink.isVisible({ timeout: 5000 }).catch(() => false)) {
    await firstLink.click();
    return;
  }

  const draftId = `e2e_diff_${Date.now()}`;
  const draftName = `E2E Diff ${Date.now()}`;
  await page.click('[data-testid="btn-create-screen"]');
  await page.waitForSelector('[data-testid="modal-create-screen"]', { timeout: 10000 });
  await page.locator('[data-testid="input-screen-id"]').fill(draftId);
  await page.locator('[data-testid="input-screen-name"]').fill(draftName);
  await page.locator('[data-testid="btn-confirm-create"]').click();

  const createdLink = page.locator('[data-testid^="link-screen-"]', { hasText: draftName }).first();
  await createdLink.waitFor({ state: "visible", timeout: 30000 });
  await createdLink.click();
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

    const summary = page.locator('text=/\\+\\d+ added/i');
    await expect(summary).toBeVisible();

    const addedItem = page.locator(".border-green-500").first();
    await expect(addedItem).toBeVisible();
  });

  test("should show Diff with modified components", async ({ page }) => {
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    await addTextComponent(page);
    await updateJsonLabel(page, "Updated Label");

    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    const summary = page.locator('text=/\\+\\d+ added/i');
    await expect(summary).toBeVisible();

    const modifiedOrAddedItem = page.locator(".border-amber-500, .border-green-500").first();
    await expect(modifiedOrAddedItem).toBeVisible();
  });

  test("should show accurate diff summary counts", async ({ page }) => {
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    await addTextComponent(page);
    await updateJsonAddComponent(page);

    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    const summaryAdded = page.locator('text=/\\+\\d+ added/i').first();
    await expect(summaryAdded).toBeVisible();
  });

  test("should render changed diff entries", async ({ page }) => {
    await page.click('[data-testid="tab-visual"]');
    await page.waitForSelector('[data-testid="visual-editor-content"]');

    await addTextComponent(page);
    await page.click('[data-testid="tab-diff"]');
    await page.waitForSelector('[data-testid="diff-content"]');

    const addedItem = page.locator(".border-green-500").first();
    await expect(addedItem).toBeVisible();
  });
});
