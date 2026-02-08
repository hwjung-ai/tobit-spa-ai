import { expect, test } from "@playwright/test";

test.describe("Documents stream E2E", () => {
  test("sends question and renders streamed answer without fetch failure", async ({ page }) => {
    let streamRequestHeaders: Record<string, string> = {};

    await page.route("**/api/documents/", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          time: "2026-02-08T00:00:00Z",
          code: 0,
          message: "OK",
          data: {
            documents: [
              {
                id: "doc-1",
                tenant_id: "t1",
                user_id: "default",
                filename: "gateway-guide.pdf",
                content_type: "application/pdf",
                size: 1234,
                status: "done",
                error_message: null,
                created_at: "2026-02-08T00:00:00Z",
                updated_at: "2026-02-08T00:00:00Z",
              },
            ],
          },
        }),
      });
    });

    await page.route("**/api/documents/doc-1", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          time: "2026-02-08T00:00:00Z",
          code: 0,
          message: "OK",
          data: {
            document: {
              id: "doc-1",
              tenant_id: "t1",
              user_id: "default",
              filename: "gateway-guide.pdf",
              content_type: "application/pdf",
              size: 1234,
              status: "done",
              error_message: null,
              created_at: "2026-02-08T00:00:00Z",
              updated_at: "2026-02-08T00:00:00Z",
              deleted_at: null,
              chunk_count: 4,
            },
          },
        }),
      });
    });

    await page.route("**/history/**", async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            time: "2026-02-08T00:00:00Z",
            code: 0,
            message: "OK",
            data: {
              history: [],
            },
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          time: "2026-02-08T00:00:00Z",
          code: 0,
          message: "OK",
          data: {},
        }),
      });
    });

    await page.route("**/api/documents/doc-1/query/stream", async (route) => {
      streamRequestHeaders = route.request().headers();
      const sseBody =
        'data: {"type":"answer","text":"Gateway composes routing, auth, and policy layers.","meta":{"document_id":"doc-1","chunks":[{"chunk_id":"c1","page":1}]}}\n\n' +
        'data: {"type":"done","text":"","meta":{"document_id":"doc-1","chunks":[{"chunk_id":"c1","page":1}],"references":[{"document_id":"doc-1","document_title":"gateway-guide.pdf","chunk_id":"c1","page":1,"snippet":"Gateway architecture","score":0.94}]}}\n\n';
      await route.fulfill({
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
        body: sseBody,
      });
    });

    await page.goto("/documents");

    await expect(page.getByText("Ask a question")).toBeVisible();
    await page.getByPlaceholder("질문 예: 이 문서의 핵심 요약은?").fill("Tell me gateway structure");
    await page.getByRole("button", { name: "메시지 전송" }).click();

    await expect(page.getByText("Gateway composes routing, auth, and policy layers.").first()).toBeVisible();
    await expect(page.getByText("Failed to fetch")).toHaveCount(0);
    await expect(page.getByText("근거 문서 (1건)")).toBeVisible();

    expect(streamRequestHeaders["x-tenant-id"]).toBe("t1");
    expect(streamRequestHeaders["x-user-id"]).toBe("default");
  });
});
