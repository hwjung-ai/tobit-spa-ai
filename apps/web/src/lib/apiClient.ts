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

export interface FetchOptions extends RequestInit {
  headers?: HeadersInit;
  timeout?: number; // Timeout in milliseconds
}

/**
 * Make an authenticated API request with automatic token handling.
 * - Adds Authorization header with access token
 * - Automatically refreshes token on 401 response
 * - Redirects to login on refresh failure
 */
export async function authenticatedFetch<T = unknown>(
  endpoint: string,
  options?: FetchOptions
): Promise<T> {
  const token = localStorage.getItem("access_token");
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
      throw new Error(`요청 시간이 초과되었습니다 (${timeout / 1000}초). 서버가 응답하지 않습니다.`);
    }

    throw error;
  }
}

/**
 * Make a simple API request without authentication.
 * Use for login, signup, and other public endpoints.
 */
export async function fetchApi<T = unknown>(
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
