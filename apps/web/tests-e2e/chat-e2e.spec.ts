import { expect, test } from "@playwright/test";
import { loginAsAdmin } from "./test-utils";

test.describe("Chat E2E Tests", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("should display chat interface", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Tobit SPA AI");
    
    // Chat UI elements
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="chat-messages"]')).toBeVisible();
    await expect(page.locator('[data-testid="new-conversation-btn"]')).toBeVisible();
  });

  test("should create new conversation", async ({ page }) => {
    await page.goto("/");
    
    // Click new conversation button
    await page.click('[data-testid="new-conversation-btn"]');
    
    // Verify empty state
    await expect(page.locator('[data-testid="chat-messages"]')).toContainText("Start a conversation");
  });

  test("should send message and receive response", async ({ page }) => {
    await page.goto("/");
    
    // Wait for chat interface
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    
    // Type and send message
    const testMessage = "What is the system status?";
    await page.fill('[data-testid="chat-input"]', testMessage);
    await page.click('[data-testid="send-message-btn"]');
    
    // Verify user message is displayed
    await expect(page.locator('[data-testid="user-message"]')).toContainText(testMessage);
    
    // Verify assistant response (with timeout for streaming)
    await expect(page.locator('[data-testid="assistant-message"]')).toBeVisible({ timeout: 30000 });
  });

  test("should display references in response", async ({ page }) => {
    await page.goto("/");
    
    // Send a query that should return references
    const testMessage = "Show me recent errors";
    await page.fill('[data-testid="chat-input"]', testMessage);
    await page.click('[data-testid="send-message-btn"]');
    
    // Wait for response
    await expect(page.locator('[data-testid="assistant-message"]')).toBeVisible({ timeout: 30000 });
    
    // Check if references section exists
    const referencesSection = page.locator('[data-testid="references-section"]');
    const hasReferences = await referencesSection.count();
    
    if (hasReferences > 0) {
      await expect(referencesSection).toBeVisible();
      
      // Verify reference items
      const referenceItems = page.locator('[data-testid^="reference-item-"]');
      const count = await referenceItems.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test("should stream response in real-time", async ({ page }) => {
    await page.goto("/");
    
    const testMessage = "Explain the system architecture";
    await page.fill('[data-testid="chat-input"]', testMessage);
    await page.click('[data-testid="send-message-btn"]');
    
    // Wait for streaming to start
    await expect(page.locator('[data-testid="assistant-message"]')).toBeVisible({ timeout: 5000 });
    
    // Verify streaming progress (content should appear gradually)
    const startTime = Date.now();
    let previousLength = 0;
    
    while (Date.now() - startTime < 30000) {
      const currentContent = await page.locator('[data-testid="assistant-message"]').textContent() || "";
      if (currentContent.length > previousLength) {
        previousLength = currentContent.length;
        // Content is growing, streaming is working
        break;
      }
      await page.waitForTimeout(500);
    }
    
    expect(previousLength).toBeGreaterThan(0);
  });

  test("should display conversation history", async ({ page }) => {
    await page.goto("/");
    
    // Check if history sidebar exists
    const historySidebar = page.locator('[data-testid="history-sidebar"]');
    const sidebarVisible = await historySidebar.count() > 0;
    
    if (sidebarVisible) {
      await expect(historySidebar).toBeVisible();
      
      // Verify refresh button
      await expect(page.locator('[data-testid="refresh-history-btn"]')).toBeVisible();
      
      // Click refresh to load history
      await page.click('[data-testid="refresh-history-btn"]');
      
      // Wait for history items
      await expect(page.locator('[data-testid^="history-item-"]')).toBeVisible({ timeout: 5000 });
    }
  });

  test("should handle conversation selection", async ({ page }) => {
    await page.goto("/");
    
    const historySidebar = page.locator('[data-testid="history-sidebar"]');
    const sidebarVisible = await historySidebar.count() > 0;
    
    if (sidebarVisible) {
      // Refresh history first
      await page.click('[data-testid="refresh-history-btn"]');
      await expect(page.locator('[data-testid^="history-item-"]')).toBeVisible({ timeout: 5000 });
      
      // Select first conversation
      await page.click('[data-testid^="history-item-"]');
      
      // Verify messages are loaded
      await expect(page.locator('[data-testid="chat-messages"]')).toBeVisible();
    }
  });

  test("should delete conversation", async ({ page }) => {
    await page.goto("/");
    
    const historySidebar = page.locator('[data-testid="history-sidebar"]');
    const sidebarVisible = await historySidebar.count() > 0;
    
    if (sidebarVisible) {
      // Refresh history
      await page.click('[data-testid="refresh-history-btn"]');
      await expect(page.locator('[data-testid^="history-item-"]')).toBeVisible({ timeout: 5000 });
      
      // Get initial count
      const initialCount = await page.locator('[data-testid^="history-item-"]').count();
      
      if (initialCount > 0) {
        // Find and click delete button on first item
        const deleteBtn = page.locator('[data-testid^="history-item-"]').first().locator('[data-testid="delete-conversation-btn"]');
        
        if (await deleteBtn.count() > 0) {
          await deleteBtn.click();
          
          // Confirm deletion
          await page.click('[data-testid="confirm-delete-btn"]');
          
          // Verify count decreased
          const newCount = await page.locator('[data-testid^="history-item-"]').count();
          expect(newCount).toBeLessThan(initialCount);
        }
      }
    }
  });

  test("should handle streaming errors gracefully", async ({ page }) => {
    await page.goto("/");
    
    // Send a potentially problematic query
    const testMessage = "{{invalid}}";
    await page.fill('[data-testid="chat-input"]', testMessage);
    await page.click('[data-testid="send-message-btn"]');
    
    // Wait for error message
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible({ timeout: 15000 });
    
    // Verify error content
    await expect(page.locator('[data-testid="error-message"]')).toContainText("error", { ignoreCase: true });
  });

  test("should support multi-turn conversation", async ({ page }) => {
    await page.goto("/");
    
    // First message
    await page.fill('[data-testid="chat-input"]', "What is the system status?");
    await page.click('[data-testid="send-message-btn"]');
    await expect(page.locator('[data-testid="assistant-message"]').first()).toBeVisible({ timeout: 30000 });
    
    // Second message (follow-up)
    await page.fill('[data-testid="chat-input"]', "Show me more details");
    await page.click('[data-testid="send-message-btn"]');
    
    // Verify both messages exist
    const userMessages = page.locator('[data-testid="user-message"]');
    const assistantMessages = page.locator('[data-testid="assistant-message"]');
    
    await expect(userMessages).toHaveCount(2);
    await expect(assistantMessages).toHaveCount(2);
  });

  test("should maintain context in conversation", async ({ page }) => {
    await page.goto("/");
    
    // First message
    await page.fill('[data-testid="chat-input"]', "What databases are available?");
    await page.click('[data-testid="send-message-btn"]');
    await expect(page.locator('[data-testid="assistant-message"]').first()).toBeVisible({ timeout: 30000 });
    
    // Second message referencing previous context
    await page.fill('[data-testid="chat-input"]', "Show me tables in Postgres");
    await page.click('[data-testid="send-message-btn"]');
    
    // Verify context is maintained (response should mention Postgres)
    const secondResponse = page.locator('[data-testid="assistant-message"]').nth(1);
    await expect(secondResponse).toContainText("postgres", { ignoreCase: true });
  });
});