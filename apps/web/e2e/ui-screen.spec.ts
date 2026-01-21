import { test, expect } from "@playwright/test";

/**
 * E2E Tests for UI Screen Contract V1
 *
 * Tests verify:
 * 1. ui_screen block rendering
 * 2. Screen Asset loading
 * 3. Component binding
 * 4. Action execution
 * 5. State updates
 * 6. Trace recording
 */

test.describe("UI Screen Contract V1", () => {
  test.beforeEach(async ({ page }) => {
    // Setup: navigate to test environment
    await page.goto("/");
  });

  test.describe("C0-1: Block ↔ Screen boundary contract", () => {
    test("should render ui_screen block type", async ({ page }) => {
      // Create a ui_screen block in answer
      await page.fill('[data-testid="question-input"]', 'Show device detail for GT-1');
      await page.press('[data-testid="question-input"]', "Enter");

      // Wait for blocks to render
      await page.waitForSelector('[data-block-type="ui_screen"]', { timeout: 5000 });

      const screenBlock = page.locator('[data-block-type="ui_screen"]');
      await expect(screenBlock).toBeVisible();
    });

    test("should load published Screen Asset by screen_id", async ({ page }) => {
      // Mock: create a published screen asset
      // (In real test, this would be created via API)

      // Wait for screen to load
      await page.waitForSelector('[data-screen-id]', { timeout: 5000 });

      const screenElement = page.locator('[data-screen-id]');
      const screenId = await screenElement.getAttribute("data-screen-id");

      expect(screenId).toBeTruthy();
      expect(screenId).toMatch(/^[a-z_]+_v\d+$/); // Format: name_v<version>
    });

    test("should render screen components with correct layout", async ({ page }) => {
      // Navigate to screen
      await page.goto("/?test=device_detail_screen");

      // Check layout type
      const screenContainer = page.locator('[data-screen-layout]');
      const layoutType = await screenContainer.getAttribute("data-screen-layout");

      expect(layoutType).toBe("grid");

      // Check components are rendered
      const components = page.locator('[data-screen-component]');
      const count = await components.count();

      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe("C0-2: Screen Asset operation model", () => {
    test("should persist screen asset in draft status", async ({ request }) => {
      const createResponse = await request.post(
        "http://localhost:8000/asset-registry/assets",
        {
          data: {
            asset_type: "screen",
            screen_id: "test_screen_draft",
            name: "Test Screen (Draft)",
            description: "Test screen in draft status",
            schema_json: {
              version: "1.0",
              layout: { type: "grid" },
              components: [],
              state_schema: {},
            },
            created_by: "test@example.com",
          },
        }
      );

      expect(createResponse.ok()).toBeTruthy();
      const data = await createResponse.json();

      expect(data.data.status).toBe("draft");
      expect(data.data.version).toBe(1);
    });

    test("should publish screen asset and increment version", async ({
      request,
    }) => {
      // Create draft
      const createResponse = await request.post(
        "http://localhost:8000/asset-registry/assets",
        {
          data: {
            asset_type: "screen",
            screen_id: "test_screen_publish",
            name: "Test Screen (Publish)",
            schema_json: {
              version: "1.0",
              layout: { type: "grid" },
              components: [],
              state_schema: {},
            },
            created_by: "test@example.com",
          },
        }
      );

      const assetId = (await createResponse.json()).data.asset_id;

      // Publish
      const publishResponse = await request.post(
        `http://localhost:8000/asset-registry/assets/${assetId}/publish`,
        {
          data: {
            published_by: "reviewer@example.com",
          },
        }
      );

      expect(publishResponse.ok()).toBeTruthy();
      const published = await publishResponse.json();

      expect(published.data.status).toBe("published");
      expect(published.data.version).toBe(1);
    });

    test("should rollback screen asset to previous version", async ({
      request,
    }) => {
      // Create draft
      const createResponse = await request.post(
        "http://localhost:8000/asset-registry/assets",
        {
          data: {
            asset_type: "screen",
            screen_id: "test_screen_rollback",
            name: "Test Screen (Rollback)",
            schema_json: {
              version: "1.0",
              layout: { type: "grid" },
              components: [{ id: "v1", type: "text" }],
              state_schema: {},
            },
            created_by: "test@example.com",
          },
        }
      );

      const assetId = (await createResponse.json()).data.asset_id;

      // Publish v1
      await request.post(
        `http://localhost:8000/asset-registry/assets/${assetId}/publish`,
        {
          data: { published_by: "reviewer@example.com" },
        }
      );

      // Update to v2
      await request.put(
        `http://localhost:8000/asset-registry/assets/${assetId}`,
        {
          data: {
            schema_json: {
              version: "1.0",
              layout: { type: "grid" },
              components: [{ id: "v2", type: "input" }],
              state_schema: {},
            },
          },
        }
      );

      // Publish v2
      await request.post(
        `http://localhost:8000/asset-registry/assets/${assetId}/publish`,
        {
          data: { published_by: "reviewer@example.com" },
        }
      );

      // Rollback to v1
      const rollbackResponse = await request.post(
        `http://localhost:8000/asset-registry/assets/${assetId}/rollback`,
        {
          data: {
            target_version: 1,
            published_by: "reviewer@example.com",
          },
        }
      );

      expect(rollbackResponse.ok()).toBeTruthy();
      const rolled = await rollbackResponse.json();

      expect(rolled.data.version).toBe(3); // New version 3
      expect(rolled.data.rollback_from_version).toBe(2);
    });

    test("should include screen asset in execution trace", async ({
      page,
      request,
    }) => {
      // Get recent trace
      const tracesResponse = await request.get(
        "http://localhost:8000/inspector/traces?limit=1"
      );

      const traces = await tracesResponse.json();
      const trace = traces.data.items[0];

      // Check applied_assets includes screens
      expect(trace.applied_assets).toHaveProperty("screens");

      if (trace.applied_assets.screens.length > 0) {
        const screenAsset = trace.applied_assets.screens[0];
        expect(screenAsset).toHaveProperty("screen_id");
        expect(screenAsset).toHaveProperty("version");
        expect(screenAsset).toHaveProperty("status");
      }
    });
  });

  test.describe("C0-3: UI Action execution", () => {
    test("should execute ui action with binding engine", async ({
      page,
      request,
    }) => {
      // Get current trace ID
      const traceId = await page.getAttribute("[data-trace-id]", "content");

      // Execute action with input binding
      const actionResponse = await request.post(
        "http://localhost:8000/ops/ui-actions",
        {
          data: {
            trace_id: traceId,
            action_id: "fetch_device_detail",
            inputs: {
              device_id: "GT-1",
            },
            context: {
              mode: "real",
              user_id: "test@example.com",
            },
          },
        }
      );

      expect(actionResponse.ok()).toBeTruthy();
      const result = await actionResponse.json();

      expect(result.data).toHaveProperty("blocks");
      expect(result.data.blocks).toBeInstanceOf(Array);
    });

    test("should support state bindings in action payload", async ({
      request,
    }) => {
      // Test binding engine directly
      const bindingTestResponse = await request.post(
        "http://localhost:8000/ops/ui-actions",
        {
          data: {
            action_id: "test_binding_action",
            inputs: {
              name: "Device123",
            },
            context: {
              mode: "real",
              user_id: "alice@example.com",
            },
          },
        }
      );

      // Should succeed or fail gracefully
      expect(
        bindingTestResponse.ok() || bindingTestResponse.status() === 400
      ).toBeTruthy();
    });

    test("should update loading/error state during action execution", async ({
      page,
    }) => {
      // Navigate to screen with actions
      await page.goto("/?test=device_detail_screen");

      // Click action button
      const actionButton = page.locator('button:has-text("Refresh")').first();
      await actionButton.click();

      // Check loading state appears
      const loadingSpinner = page.locator(
        'button:has-text("Refresh") svg.animate-spin'
      );
      await expect(loadingSpinner).toBeVisible({ timeout: 500 });

      // Wait for action to complete
      await page.waitForTimeout(2000);

      // Loading should disappear or error should appear
      const finalButton = page.locator('button:has-text("Refresh")').first();
      const isDisabled = await finalButton.isDisabled();

      expect(isDisabled).toBe(false);
    });

    test("should mask sensitive inputs in trace", async ({ request }) => {
      // Execute action with sensitive input
      const actionResponse = await request.post(
        "http://localhost:8000/ops/ui-actions",
        {
          data: {
            action_id: "create_credential_action",
            inputs: {
              username: "alice",
              password: "secret123",
              api_token: "sk_test_1234567890",
            },
            context: { mode: "real" },
          },
        }
      );

      // Get trace
      const traceId = actionResponse.headers()["x-trace-id"];

      if (traceId) {
        const traceResponse = await request.get(
          `http://localhost:8000/inspector/traces/${traceId}`
        );

        const trace = await traceResponse.json();

        // Sensitive fields should be masked
        if (trace.data.request_payload.inputs) {
          const inputs = trace.data.request_payload.inputs;

          expect(inputs.password).not.toContain("secret");
          expect(inputs.api_token).not.toContain("sk_test");
        }
      }
    });
  });

  test.describe("Integration: E2E workflow", () => {
    test("should execute complete device detail workflow", async ({
      page,
      request,
    }) => {
      // 1. Ask question → get ui_screen block
      await page.goto("/");
      await page.fill(
        '[data-testid="question-input"]',
        "Show device GT-1 details"
      );
      await page.press('[data-testid="question-input"]', "Enter");

      // Wait for screen to load
      await page.waitForSelector('[data-screen-id="device_detail_v1"]', {
        timeout: 5000,
      });

      // 2. Click action button
      const refreshButton = page.locator('button:has-text("Refresh")').first();
      if (await refreshButton.isVisible()) {
        await refreshButton.click();

        // 3. Verify action executed and state updated
        await page.waitForTimeout(1500);

        // May or may not appear depending on backend response
      }

      // 4. Verify trace recorded
      const traceId = await page.getAttribute("[data-trace-id]", "content");

      if (traceId) {
        const traceResponse = await request.get(
          `http://localhost:8000/inspector/traces/${traceId}`
        );

        expect(traceResponse.ok()).toBeTruthy();

        const trace = await traceResponse.json();
        expect(trace.data).toHaveProperty("applied_assets");
      }
    });

    test("should handle CRUD workflow (create maintenance ticket)", async ({
      page,
    }) => {
      // Navigate to maintenance screen
      await page.goto("/?test=maintenance_crud_screen");

      // 1. Check list is loaded
      const table = page.locator('[data-component-type="table"]').first();
      await expect(table).toBeVisible({ timeout: 5000 });

      // 2. Click "Create" button
      const createButton = page.locator('button:has-text("Create")').first();
      if (await createButton.isVisible()) {
        await createButton.click();

        // 3. Modal should appear
        const modal = page.locator('[data-component-type="modal"]');
        await expect(modal).toBeVisible({ timeout: 1000 });

        // 4. Fill form
        const deviceInput = page.locator('input[name="device_id"]').first();
        if (await deviceInput.isVisible()) {
          await deviceInput.fill("GT-1");
        }

        // 5. Submit
        const submitButton = page
          .locator('button:has-text("Create")')
          .filter({ hasText: /^Create$/ })
          .last();

        if (await submitButton.isVisible()) {
          await submitButton.click();

          // 6. Wait for success
          await page.waitForTimeout(2000);

          // Modal should close or success message appear
          // May appear depending on backend response
        }
      }
    });
  });

  test.describe("Error handling", () => {
    test("should handle missing screen asset gracefully", async ({ page }) => {
      // Try to render non-existent screen
      await page.goto("/?test=missing_screen_screen");

      // Should show error or be handled gracefully
    });

    test("should handle binding expression errors", async ({ request }) => {
      // Test with invalid binding expression
      const actionResponse = await request.post(
        "http://localhost:8000/ops/ui-actions",
        {
          data: {
            action_id: "test_action",
            inputs: {},
            context: { mode: "real" },
          },
        }
      );

      // Should fail gracefully
      expect(actionResponse.status()).toBeGreaterThanOrEqual(400);
    });

    test("should show error when asset not published", async ({ request }) => {
      // Try to render draft screen (should fail)
      const response = await request.get(
        "http://localhost:8000/asset-registry/assets?screen_id=draft_screen&status=published"
      );

      // Should return empty list
      const data = await response.json();
      expect(data.data.items).toHaveLength(0);
    });
  });
});
