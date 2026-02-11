/**
 * Authenticated API client for making requests with JWT tokens.
 * Automatically adds Bearer token to requests and handles token refresh.
 */

// Build URL for API requests - empty string means use relative paths (Next.js rewrites proxy)
const buildUrl = (endpoint: string): string => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  // If baseUrl is empty, just use endpoint (relative path for Next.js rewrites)
  // If baseUrl is set, concatenate properly
  if (!baseUrl) {
    return endpoint;
  }
  return `${baseUrl.replace(/\/+$/, "")}${endpoint}`;
};

const DEFAULT_TENANT_ID = process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || "default";

function normalizeTenantId(rawTenantId: string | null): string {
  if (!rawTenantId || rawTenantId === "t1") {
    return DEFAULT_TENANT_ID;
  }
  return rawTenantId;
}

export interface FetchOptions extends RequestInit {
  headers?: HeadersInit;
  timeout?: number; // Timeout in milliseconds
}

/**
 * Get auth headers for API requests
 * Returns a Headers object with Authorization, X-Tenant-Id, and X-User-Id
 */
export function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  const tenantId = normalizeTenantId(localStorage.getItem("tenant_id"));
  const userId = localStorage.getItem("user_id") || "default";

  const headers: HeadersInit = {
    "X-Tenant-Id": tenantId,
    "X-User-Id": userId,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Make an authenticated fetch request (for PDF, images, or other non-JSON responses)
 * Returns the raw Response object so caller can handle blobs, etc.
 */
export async function fetchWithAuth(
  url: string,
  options?: Omit<RequestInit, "headers"> & { headers?: HeadersInit }
): Promise<Response> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options?.headers ?? {}),
    },
  });

  // Handle 401 Unauthorized
  if (response.status === 401) {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        const refreshUrl = buildUrl("/auth/refresh");
        const refreshResponse = await fetch(refreshUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          localStorage.setItem("access_token", data.data.access_token);

          // Retry with new token
          return fetchWithAuth(url, options);
        }
      } catch (error) {
        console.error("Token refresh failed:", error);
      }
    }

    // Redirect to login
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }

    throw new Error("Authentication failed");
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }

  return response;
}

/**
 * Make an authenticated API request with automatic token handling.
 * - Adds Authorization header with access token
 * - Automatically refreshes token on 401 response
 * - Redirects to login on refresh failure
 */
export async function authenticatedFetch<T = any>(
  endpoint: string,
  options?: FetchOptions
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const tenantId = normalizeTenantId(localStorage.getItem("tenant_id"));
  const userId = localStorage.getItem("user_id");
  const timeout = options?.timeout || 120000; // Default 120 seconds

  // Create an AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const url = buildUrl(endpoint);
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(tenantId && { "X-Tenant-Id": tenantId }),
        ...(userId && { "X-User-Id": userId }),
        ...options?.headers,
      },
    });
    clearTimeout(timeoutId);

    // Handle unauthorized - try to refresh token
    if (response.status === 401) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const refreshUrl = buildUrl("/auth/refresh");
          const refreshResponse = await fetch(refreshUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshResponse.ok) {
            const data = await refreshResponse.json();
            localStorage.setItem("access_token", data.data.access_token);

            // Retry with new token
            return authenticatedFetch(endpoint, options);
          }
        } catch (error) {
          console.error("Token refresh failed:", error);
        }
      }

      // Refresh failed or no refresh token - redirect to login
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }

      throw new Error("Authentication failed");
    }

    if (!response.ok) {
      const text = await response.text();
      let errorMessage = `HTTP ${response.status}`;
      try {
        const json = JSON.parse(text);
        errorMessage = json.message || errorMessage;
      } catch {
        errorMessage = text || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const contentType = response.headers.get("content-type");
    if (contentType?.includes("application/json")) {
      const text = await response.text();
      return text ? JSON.parse(text) : null;
    }

    return response.text() as T;
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle AbortError (timeout)
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`요청 시간이 초과되었습니다 (${timeout / 1000}초). 서버가 읔답하지 않습니다.`);
    }

    throw error;
  }
}

/**
 * Make a simple API request without authentication.
 * Use for login, signup, and other public endpoints.
 */
export async function fetchApi<T = any>(
  endpoint: string,
  options?: FetchOptions
): Promise<T> {
  const url = buildUrl(endpoint);
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let errorMessage = `HTTP ${response.status}`;
    try {
      const json = JSON.parse(text);
      errorMessage = json.message || json.detail || errorMessage;
    } catch {
      errorMessage = text || errorMessage;
    }
    throw new Error(errorMessage);
  }

  const contentType = response.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  }

  return response.text() as T;
}
