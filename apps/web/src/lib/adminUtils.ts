// Admin UI shared types and utilities

export interface ResponseEnvelope<T = unknown> {
  time: string;
  code: number;
  message: string;
  data: T;
}

export interface Asset {
  asset_id: string;
  asset_type: "prompt" | "mapping" | "policy" | "query" | "source" | "resolver";
  name: string;
  description: string | null;
  version: number;
  status: "draft" | "published";
  screen_id?: string | null;
  tags?: Record<string, unknown> | null;

  // Type-specific fields
  scope: string | null;
  engine: string | null;
  template: string | null;
  input_schema: Record<string, unknown> | null;
  output_contract: Record<string, unknown> | null;
  mapping_type: string | null;
  content: Record<string, unknown> | null;
  policy_type: string | null;
  limits: Record<string, unknown> | null;
  query_sql: string | null;
  query_params: Record<string, unknown> | null;
  query_metadata: Record<string, unknown> | null;

  // Source Asset fields
  source_type?: string | null;
  connection?: Record<string, unknown> | null;

  // Schema Asset fields
  catalog?: Record<string, unknown> | null;

  // Resolver Asset fields
  config?: Record<string, unknown> | null;

  // Screen-specific fields
  schema_json?: Record<string, unknown> | null;
  screen_schema?: Record<string, unknown> | null;

  // Metadata
  created_by: string | null;
  published_by: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperationSetting {
  key: string;
  value: unknown;
  source: "published" | "env" | "default";
  restart_required: boolean;
  description: string;
  default: unknown;
  allowed_values: unknown[] | null;
  published_by: string | null;
  published_at: string | null;
  [key: string]: unknown;
}

export interface AuditLog {
  audit_id: string;
  trace_id: string;
  parent_trace_id: string | null;
  resource_type: string;
  resource_id: string;
  action: string;
  actor: string;
  changes: Record<string, unknown>;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  audit_metadata: Record<string, unknown> | null;
  created_at: string;
}

export const API_BASE_URL = (() => {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  // Remove trailing slashes for consistency
  return baseUrl.replace(/\/+$/, "");
})();

// Build URL for API requests - empty string means use relative paths (Next.js rewrites proxy)
export const buildApiUrl = (endpoint: string): string => {
  // Ensure endpoint starts with / for absolute path (avoid relative path issues)
  const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  if (!API_BASE_URL) {
    return normalizedEndpoint;
  }
  return `${API_BASE_URL}${normalizedEndpoint}`;
};

const ENABLE_AUTH = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

export interface FetchApiOptions extends RequestInit {
  timeout?: number; // Timeout in milliseconds
}

export async function fetchApi<T = unknown>(
  endpoint: string,
  options?: FetchApiOptions
): Promise<ResponseEnvelope<T>> {
  const url = buildApiUrl(endpoint);
  const timeout = options?.timeout || 30000; // Default 30 seconds

  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options?.headers,
  };

  if (ENABLE_AUTH) {
    if (token) {
      (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
      console.log("[API] Adding Authorization header with token");
    } else {
      console.warn("[API] No token found in localStorage for endpoint:", endpoint);
      console.warn("[API] User may not be logged in. Visit /login to authenticate.");
    }
  } else {
    console.log("[API] Auth disabled (NEXT_PUBLIC_ENABLE_AUTH=false). Skipping token.");
  }

  console.log("[API] Fetching:", endpoint, "with method:", options?.method || "GET", "URL:", url);

  // Create an AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: "same-origin",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    console.log("[API] Fetch successful, status:", response.status);
  } catch (fetchError) {
    clearTimeout(timeoutId);

    // Handle AbortError (timeout)
    if (fetchError instanceof Error && fetchError.name === "AbortError") {
      const error: Error & { statusCode?: number } = new Error(
        `요청 시간이 초과되었습니다 (${timeout / 1000}초). 서버가 응답하지 않습니다.`
      );
      error.statusCode = 408; // Request Timeout
      throw error;
    }
    const error = fetchError instanceof Error ? fetchError : new Error(String(fetchError));
    const errorMsg = error.message;
    const errorName = error.name;

    console.error("[API] Network error - fetch failed:", {
      endpoint,
      url,
      error: fetchError,
      errorMessage: errorMsg,
      errorName: errorName,
      errorStack: error.stack,
    });

    const isTypeError = errorName === "TypeError";
    const isFetchError = errorMsg.includes("fetch") || errorMsg.includes("Failed to fetch");
    const isCORSError = errorMsg.includes("CORS");

    const backendUrl = API_BASE_URL || "http://localhost:3000 (via Next.js rewrites)";
    let userMessage = `Network error: Failed to fetch. Check if backend is running.`;
    if (isFetchError || isCORSError) {
      userMessage = `Network error: Failed to connect to backend (${backendUrl}). Please check if backend is running.`;
    } else if (isTypeError) {
      userMessage = `Network error: ${errorMsg}`;
    }

    const finalError: Error & { statusCode?: number; originalError?: unknown } = new Error(userMessage);
    finalError.statusCode = isCORSError ? 0 : undefined;
    finalError.originalError = fetchError;

    throw finalError;
  }

  if (!response) {
    console.error("[API] Response is null/undefined after successful fetch");
    throw new Error("No response received from server");
  }

  if (!response.ok) {
    let errorData: unknown = {};
    let rawText = "";
    try {
      rawText = await response.text();
      console.log("[API] Raw response text (first 1000 chars):", rawText.substring(0, 1000));
      console.log("[API] Full raw response text:", rawText);
      console.log("[API] Response status:", response.status);
      console.log("[API] Response headers:", {
        contentType: response.headers.get("content-type"),
        contentLength: response.headers.get("content-length"),
      });

      if (rawText) {
        try {
          errorData = JSON.parse(rawText);
        } catch (parseErr) {
          console.error("[API] JSON parse error:", parseErr);
          console.error("[API] Tried to parse as JSON but failed. Raw text:", rawText.substring(0, 200));
          // Check if it looks like HTML (error page)
          if (rawText.includes("<html") || rawText.includes("<HTML") || rawText.includes("<!DOCTYPE")) {
            errorData = { message: `Server returned HTML error page: ${response.status} ${response.statusText}` };
          } else {
            errorData = { message: rawText };
          }
        }
      } else {
        console.warn("[API] Response body is empty!");
        errorData = { message: "Empty response body" };
      }
    } catch (parseError) {
      console.error("[API] Failed to parse error response:", parseError);
      errorData = { message: String(parseError) };
    }

    if (response.status === 401 && ENABLE_AUTH) {
      console.error("[API] Authentication failed (401 Unauthorized)");
      console.error("[API] Possible causes:");
      console.error("[API]   1. User not logged in - visit /login");
      console.error("[API]   2. Token expired - log in again");
      console.error("[API]   3. Invalid token in localStorage");
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    console.error("[API] Request failed:", {
      endpoint,
      method: options?.method || "GET",
      status: response.status,
      statusText: response.statusText,
      error: errorData,
      rawResponse: rawText.substring(0, 500),
    });
    console.error("[API] Full error data:", errorData);
    console.error("[API] Full raw text:", rawText);

    const errorMessage = (errorData as Record<string, unknown>)?.detail || (errorData as Record<string, unknown>)?.message || `HTTP ${response.status}: ${response.statusText}`;
    const error = new Error(String(errorMessage));
    (error as unknown as { statusCode: number }).statusCode = response.status;
    throw error;
  }

  return response.json();
}

export function formatTimestamp(value: string | null): string {
  if (!value) return "";
  try {
    let dateStr = value;
    if (value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(value)) {
      dateStr = `${value}Z`;
    }
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString("ko-KR", {
      timeZone: "Asia/Seoul",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function formatRelativeTime(value: string | null): string {
  if (!value) return "";
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) {
      return `${diffSecs}초 전`;
    }
    if (diffMins < 60) {
      return `${diffMins}분 전`;
    }
    if (diffHours < 24) {
      return `${diffHours}시간 전`;
    }
    if (diffDays < 7) {
      return `${diffDays}일 전`;
    }
    return date.toLocaleString("ko-KR", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return value;
  }
}
