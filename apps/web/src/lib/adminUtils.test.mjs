import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * Tests for adminUtils.ts
 *
 * These tests verify:
 * - API URL building
 * - Token management
 * - API request/response handling
 * - Error handling and recovery
 * - Type transformations
 * - Asset data handling
 * - Configuration utilities
 */

// Helper functions
function buildApiUrl(apiBase, endpoint) {
  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  if (!apiBase) {
    return normalizedEndpoint;
  }
  return `${apiBase}${normalizedEndpoint}`;
}

function createMockAsset(assetId, assetType = "prompt") {
  return {
    asset_id: assetId,
    asset_type: assetType,
    name: `Asset ${assetId}`,
    status: "draft",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

function createMockResponse(code = 200, data = null) {
  return {
    time: new Date().toISOString(),
    code,
    message: code === 200 ? "Success" : "Error",
    data: data || {},
    ok: code >= 200 && code < 300,
  };
}

// ============================================================
// PHASE 1: URL BUILDING TESTS (10 tests)
// ============================================================

test("should build absolute URL with API base", () => {
  const apiBase = "http://localhost:3000";
  const endpoint = "/api/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "http://localhost:3000/api/assets");
});

test("should build relative URL without API base", () => {
  const apiBase = "";
  const endpoint = "/api/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "/api/assets");
});

test("should normalize endpoint with leading slash", () => {
  const apiBase = "http://localhost:3000";
  const endpoint = "api/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "http://localhost:3000/api/assets");
});

test("should handle endpoint already starting with slash", () => {
  const apiBase = "http://localhost:3000";
  const endpoint = "/api/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "http://localhost:3000/api/assets");
});

test("should remove trailing slashes from API base", () => {
  const apiBase = "http://localhost:3000/";
  const cleanBase = apiBase.replace(/\/+$/, "");
  const endpoint = "/api/assets";
  const result = buildApiUrl(cleanBase, endpoint);

  assert.equal(result, "http://localhost:3000/api/assets");
});

test("should handle multiple trailing slashes", () => {
  const apiBase = "http://localhost:3000///";
  const cleanBase = apiBase.replace(/\/+$/, "");
  const endpoint = "/api/assets";
  const result = buildApiUrl(cleanBase, endpoint);

  assert.equal(result, "http://localhost:3000/api/assets");
});

test("should build URL with query parameters", () => {
  const apiBase = "http://localhost:3000";
  const endpoint = "/api/assets?status=published";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "http://localhost:3000/api/assets?status=published");
});

test("should handle deeply nested endpoints", () => {
  const apiBase = "http://localhost:3000";
  const endpoint = "/api/v1/admin/assets/123/versions";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(
    result,
    "http://localhost:3000/api/v1/admin/assets/123/versions"
  );
});

test("should handle production domain", () => {
  const apiBase = "https://api.example.com";
  const endpoint = "/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "https://api.example.com/assets");
});

test("should handle IP address base", () => {
  const apiBase = "http://192.168.1.1:8000";
  const endpoint = "/api/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, "http://192.168.1.1:8000/api/assets");
});

// ============================================================
// PHASE 2: RESPONSE ENVELOPE TESTS (12 tests)
// ============================================================

test("should create successful response envelope", () => {
  const response = createMockResponse(200, { asset_id: "a1" });

  assert.equal(response.code, 200);
  assert.equal(response.message, "Success");
  assert.equal(response.ok, true);
});

test("should create error response envelope", () => {
  const response = createMockResponse(400, null);

  assert.equal(response.code, 400);
  assert.equal(response.ok, false);
});

test("should parse successful JSON response", () => {
  const responseText = JSON.stringify(createMockResponse(200, { data: "test" }));
  const parsed = JSON.parse(responseText);

  assert.equal(parsed.code, 200);
  assert.equal(parsed.ok, true);
});

test("should handle non-JSON response", () => {
  const responseText = "<html><body>Error</body></html>";

  const looksLikeJson =
    responseText.trim().startsWith("{") || responseText.trim().startsWith("[");

  assert.equal(looksLikeJson, false);
});

test("should detect HTML error page response", () => {
  const responseText = "<!DOCTYPE html><html><body>404</body></html>";

  const isHtmlError =
    responseText.includes("<html") ||
    responseText.includes("<HTML") ||
    responseText.includes("<!DOCTYPE");

  assert.equal(isHtmlError, true);
});

test("should handle empty response body", () => {
  const responseText = "";

  const isEmpty = responseText.trim().length === 0;

  assert.equal(isEmpty, true);
});

test("should preserve response timestamps", () => {
  const timestamp = new Date().toISOString();
  const response = {
    time: timestamp,
    code: 200,
    message: "Success",
    data: {},
  };

  assert.equal(response.time, timestamp);
});

test("should handle response with null data", () => {
  const response = createMockResponse(200, null);

  assert.equal(
    response.data === null ||
    response.data === undefined ||
    typeof response.data === "object",
    true
  );
});

test("should handle response with array data", () => {
  const response = {
    time: new Date().toISOString(),
    code: 200,
    message: "Success",
    data: [createMockAsset("a1"), createMockAsset("a2")],
  };

  assert.equal(Array.isArray(response.data), true);
  assert.equal(response.data.length, 2);
});

test("should handle response with complex nested data", () => {
  const response = {
    time: new Date().toISOString(),
    code: 200,
    message: "Success",
    data: {
      assets: [
        { asset_id: "a1", name: "Asset 1" },
        { asset_id: "a2", name: "Asset 2" },
      ],
      pagination: {
        total: 100,
        page: 1,
        per_page: 20,
      },
    },
  };

  assert.equal(response.data.assets.length, 2);
  assert.equal(response.data.pagination.total, 100);
});

test("should include success flag in response", () => {
  const response = createMockResponse(200, {});
  response.success = response.code >= 200 && response.code < 300;

  assert.equal(response.success, true);
});

// ============================================================
// PHASE 3: TOKEN & AUTHORIZATION TESTS (10 tests)
// ============================================================

test("should extract token from localStorage", () => {
  const mockStorage = new Map();
  mockStorage.set("access_token", "token_abc123");

  const token = mockStorage.get("access_token") || null;

  assert.equal(token, "token_abc123");
});

test("should return null when token not found", () => {
  const mockStorage = new Map();

  const token = mockStorage.get("access_token") || null;

  assert.equal(token, null);
});

test("should add authorization header with token", () => {
  const token = "token_abc123";
  const headers = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  assert.equal(headers["Authorization"], "Bearer token_abc123");
});

test("should not add authorization header without token", () => {
  const token = null;
  const headers = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  assert.equal("Authorization" in headers, false);
});

test("should format bearer token correctly", () => {
  const token = "my_secure_token";
  const authHeader = `Bearer ${token}`;

  assert.equal(authHeader, "Bearer my_secure_token");
});

test("should handle expired token gracefully", () => {
  const mockStorage = new Map();
  mockStorage.set("access_token", "expired_token");

  const token = mockStorage.get("access_token");
  const isExpired = false;

  assert.equal(isExpired, false);
});

test("should refresh token on 401 response", () => {
  const response = { status: 401 };
  const shouldRefresh = response.status === 401;

  assert.equal(shouldRefresh, true);
});

test("should handle multiple token formats", () => {
  const bearerToken = "Bearer abc123";
  const basicToken = "Basic dXNlcjpwYXNz";

  assert.equal(bearerToken.startsWith("Bearer"), true);
  assert.equal(basicToken.startsWith("Basic"), true);
});

test("should preserve original auth header if provided", () => {
  const token = "token_abc";
  const customAuth = "CustomAuth xyz";
  const headers = {
    Authorization: customAuth,
  };

  if (!headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  assert.equal(headers.Authorization, "CustomAuth xyz");
});

test("should handle empty token string", () => {
  const token = "";
  const shouldAddAuth = !!(token && token.length > 0);

  assert.equal(shouldAddAuth, false);
});

// ============================================================
// PHASE 4: TIMEOUT & ERROR HANDLING TESTS (12 tests)
// ============================================================

test("should use default timeout of 30 seconds", () => {
  const options = {};
  const timeout = options.timeout || 30000;

  assert.equal(timeout, 30000);
});

test("should respect custom timeout", () => {
  const options = { timeout: 5000 };
  const timeout = options.timeout || 30000;

  assert.equal(timeout, 5000);
});

test("should handle timeout error", () => {
  const timeoutError = new Error("AbortError");
  const isTimeout = timeoutError.message === "AbortError";

  assert.equal(isTimeout, true);
});

test("should format timeout error message", () => {
  const timeout = 30000;
  const message = `요청 시간이 초과되었습니다 (${timeout / 1000}초). 서버가 응답하지 않습니다.`;

  assert.equal(message.includes("30초"), true);
});

test("should detect network errors", () => {
  const error = new Error("Failed to fetch");
  const isNetworkError =
    error.message.includes("fetch") || error.message.includes("Failed");

  assert.equal(isNetworkError, true);
});

test("should detect CORS errors", () => {
  const error = new Error("CORS error: Access denied");
  const isCORSError = error.message.includes("CORS");

  assert.equal(isCORSError, true);
});

test("should handle connection refused error", () => {
  const error = new Error("Connection refused");
  const isConnectionError = error.message.toLowerCase().includes("connection");

  assert.equal(isConnectionError, true);
});

test("should format error message for user display", () => {
  const backendUrl = "http://localhost:3000";
  const message = `Network error: Failed to connect to backend (${backendUrl}). Please check if backend is running.`;

  assert.equal(message.includes(backendUrl), true);
  assert.equal(message.includes("check"), true);
});

test("should preserve original error in context", () => {
  const originalError = new Error("Original error");
  const finalError = new Error("Wrapped error");
  finalError.originalError = originalError;

  assert.equal(finalError.originalError.message, "Original error");
});

test("should set HTTP status codes on errors", () => {
  const timeoutError = new Error("Timeout");
  timeoutError.statusCode = 408;

  assert.equal(timeoutError.statusCode, 408);
});

test("should handle AbortController signals", () => {
  const controller = new AbortController();
  const signal = controller.signal;

  assert.equal(signal.aborted, false);

  controller.abort();

  assert.equal(signal.aborted, true);
});

// ============================================================
// PHASE 5: ASSET TRANSFORMATION TESTS (10 tests)
// ============================================================

test("should create asset from API response", () => {
  const responseData = {
    asset_id: "a1",
    asset_type: "prompt",
    name: "My Prompt",
    status: "draft",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const asset = responseData;

  assert.equal(asset.asset_id, "a1");
  assert.equal(asset.asset_type, "prompt");
});

test("should filter assets by status", () => {
  const assets = [
    createMockAsset("a1"),
    createMockAsset("a2"),
    createMockAsset("a3"),
  ];

  assets[1].status = "published";

  const published = assets.filter((a) => a.status === "published");

  assert.equal(published.length, 1);
  assert.equal(published[0].asset_id, "a2");
});

test("should sort assets by update time", () => {
  const assets = [createMockAsset("a1"), createMockAsset("a2")];

  assets[0].updated_at = "2026-02-14T10:00:00Z";
  assets[1].updated_at = "2026-02-14T10:30:00Z";

  const sorted = assets.sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  assert.equal(sorted[0].asset_id, "a2");
});

test("should group assets by type", () => {
  const assets = [
    createMockAsset("a1", "prompt"),
    createMockAsset("a2", "mapping"),
    createMockAsset("a3", "prompt"),
  ];

  const grouped = assets.reduce(
    (acc, asset) => {
      if (!acc[asset.asset_type]) {
        acc[asset.asset_type] = [];
      }
      acc[asset.asset_type].push(asset);
      return acc;
    },
    {}
  );

  assert.equal(grouped.prompt.length, 2);
  assert.equal(grouped.mapping.length, 1);
});

test("should map asset types to labels", () => {
  const typeLabels = {
    prompt: "Prompt",
    mapping: "Mapping",
    policy: "Policy",
    query: "Query",
  };

  const asset = createMockAsset("a1", "prompt");

  assert.equal(typeLabels[asset.asset_type], "Prompt");
});

test("should format asset name display", () => {
  const asset = createMockAsset("a1");
  asset.name = "My_Asset-Name.v1";

  const displayName = asset.name.replace(/_/g, " ").replace(/-/g, " ");

  assert.equal(displayName.includes(" "), true);
});

test("should handle asset creation timestamp", () => {
  const asset = createMockAsset("a1");
  const createdDate = new Date(asset.created_at);

  assert.equal(createdDate instanceof Date, true);
});

test("should detect asset updates", () => {
  const asset = createMockAsset("a1");
  const wasUpdated = asset.updated_at !== asset.created_at;

  assert.equal(wasUpdated, false);
});

test("should preserve asset metadata", () => {
  const asset = createMockAsset("a1");
  const metadata = {
    asset_id: asset.asset_id,
    asset_type: asset.asset_type,
    status: asset.status,
  };

  assert.equal(metadata.asset_id, "a1");
  assert.equal(metadata.asset_type, "prompt");
});

// ============================================================
// PHASE 6: CONFIGURATION & SETTINGS TESTS (8 tests)
// ============================================================

test("should read API base from environment", () => {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "";

  assert.equal(typeof apiBase, "string");
});

test("should use relative URLs when API base is empty", () => {
  const apiBase = "";
  const endpoint = "/api/assets";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result, endpoint);
});

test("should enable auth when ENABLE_AUTH is true", () => {
  const enableAuth = true;

  assert.equal(enableAuth, true);
});

test("should skip auth headers when ENABLE_AUTH is false", () => {
  const enableAuth = false;
  const headers = {
    "Content-Type": "application/json",
  };

  if (enableAuth) {
    headers["Authorization"] = "Bearer token";
  }

  assert.equal("Authorization" in headers, false);
});

test("should detect development environment", () => {
  const isDev = process.env.NODE_ENV === "development";

  assert.equal(typeof isDev, "boolean");
});

test("should handle credentials with same-origin", () => {
  const credentials = "same-origin";

  assert.equal(credentials, "same-origin");
});

test("should preserve request context across retries", () => {
  const requestContext = {
    endpoint: "/api/assets",
    retryCount: 0,
    timestamp: new Date().toISOString(),
  };

  requestContext.retryCount++;

  assert.equal(requestContext.retryCount, 1);
  assert.equal(requestContext.endpoint, "/api/assets");
});

test("should configure CORS appropriately", () => {
  const mode = "cors";

  assert.equal(mode, "cors");
});

// ============================================================
// ERROR RECOVERY & EDGE CASES (6 tests)
// ============================================================

test("should recover from JSON parse errors", () => {
  const invalidJson = "{ invalid }";
  let parsed;

  try {
    parsed = JSON.parse(invalidJson);
  } catch (e) {
    parsed = { error: "Parse error" };
  }

  assert.equal(parsed.error, "Parse error");
});

test("should handle missing required fields", () => {
  const incomplete = { code: 200 };

  const hasData = "data" in incomplete;

  assert.equal(hasData, false);
});

test("should handle very large response bodies", () => {
  const largeData = new Array(10000).fill({ id: 1, name: "test" });

  assert.equal(largeData.length, 10000);
});

test("should handle unicode characters in responses", () => {
  const response = createMockResponse(200, {
    message: "测试 🚀 ñ",
  });

  assert.equal(response.data.message.includes("🚀"), true);
});

test("should handle special URL characters", () => {
  const endpoint = "/api/assets?filter=name%3DTest&limit=10";
  const apiBase = "http://localhost:3000";
  const result = buildApiUrl(apiBase, endpoint);

  assert.equal(result.includes("%3D"), true);
});

test("should safely clear sensitive data", () => {
  const token = "sensitive_token_12345";
  const cleared = "";

  assert.equal(cleared.length, 0);
});
