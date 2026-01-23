// Admin UI shared types and utilities

export interface ResponseEnvelope<T = unknown> {
  time: string;
  code: number;
  message: string;
  data: T;
}

export interface Asset {
  asset_id: string;
  asset_type: "prompt" | "mapping" | "policy" | "query";
  name: string;
  description: string | null;
  version: number;
  status: "draft" | "published";

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

export const API_BASE_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000")
    : "http://localhost:8000";

const ENABLE_AUTH = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

export async function fetchApi<T = unknown>(
  endpoint: string,
  options?: RequestInit
): Promise<ResponseEnvelope<T>> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Get auth token from localStorage if available
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options?.headers,
  };

  // Add Authorization header if auth is enabled and token exists
  if (ENABLE_AUTH) {
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      console.log("[API] Adding Authorization header with token");
    } else {
      console.warn("[API] ⚠️ No token found in localStorage for endpoint:", endpoint);
      console.warn("[API] User may not be logged in. Visit /login to authenticate.");
    }
  } else {
    console.log("[API] Auth disabled (NEXT_PUBLIC_ENABLE_AUTH=false). Skipping token.");
  }

  console.log("[API] Fetching:", endpoint, "with method:", options?.method || "GET");

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (fetchError) {
    console.error("[API] Network error - fetch failed:", {
      endpoint,
      url,
      error: fetchError,
      errorMessage: (fetchError as Error).message,
      errorName: (fetchError as Error).name,
    });
    throw new Error(`Network error: ${(fetchError as Error).message}. Check if backend is running at ${API_BASE_URL}`);
  }

  if (!response.ok) {
    let errorData: unknown = {};
    let rawText = "";
    try {
      rawText = await response.text();
      console.log("[API] Raw response text:", rawText);
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
          errorData = { message: rawText };
        }
      } else {
        console.warn("[API] Response body is empty!");
        errorData = { message: "Empty response body" };
      }
    } catch (parseError) {
      console.error("[API] Failed to parse error response:", parseError);
      errorData = { message: String(parseError) };
    }

    // Check if it's a 401 Unauthorized error (only if auth is enabled)
    if (response.status === 401 && ENABLE_AUTH) {
      console.error("[API] ❌ Authentication failed (401 Unauthorized)");
      console.error("[API] Possible causes:");
      console.error("[API]   1. User not logged in - visit /login");
      console.error("[API]   2. Token expired - log in again");
      console.error("[API]   3. Invalid token in localStorage");
      // Try to clear potentially stale token
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      // Redirect to login page
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
    // Attach status code to error for easier checking in catch blocks
    (error as unknown as { statusCode: number }).statusCode = response.status;
    throw error;
  }

  return response.json();
}

export function formatTimestamp(value: string | null): string {
  if (!value) return "";
  try {
    let dateStr = value;
    if (value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(value)) {
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
    let dateStr = value;
    if (value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(value)) {
      dateStr = `${value}Z`;
    }
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "방금 전";
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    if (diffDays < 7) return `${diffDays}일 전`;

    return formatTimestamp(value);
  } catch {
    return value;
  }
}
