// Admin UI shared types and utilities

export interface ResponseEnvelope<T = any> {
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
  input_schema: Record<string, any> | null;
  output_contract: Record<string, any> | null;
  mapping_type: string | null;
  content: Record<string, any> | null;
  policy_type: string | null;
  limits: Record<string, any> | null;
  query_sql: string | null;
  query_params: Record<string, any> | null;
  query_metadata: Record<string, any> | null;

  // Metadata
  created_by: string | null;
  published_by: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperationSetting {
  key: string;
  value: any;
  source: "published" | "env" | "default";
  restart_required: boolean;
  description: string;
  default: any;
  allowed_values: any[] | null;
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
  changes: Record<string, any>;
  old_values: Record<string, any> | null;
  new_values: Record<string, any> | null;
  audit_metadata: Record<string, any> | null;
  created_at: string;
}

export const API_BASE_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000")
    : "http://localhost:8000";

export async function fetchApi<T = any>(
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

  // Add Authorization header if token exists
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
    console.log("[API] Adding Authorization header with token");
  } else {
    console.warn("[API] ⚠️ No token found in localStorage for endpoint:", endpoint);
    console.warn("[API] User may not be logged in. Visit /login to authenticate.");
  }

  console.log("[API] Fetching:", endpoint, "with method:", options?.method || "GET");

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: any = {};
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

    // Check if it's a 401 Unauthorized error
    if (response.status === 401) {
      console.error("[API] ❌ Authentication failed (401 Unauthorized)");
      console.error("[API] Possible causes:");
      console.error("[API]   1. User not logged in - visit /login");
      console.error("[API]   2. Token expired - log in again");
      console.error("[API]   3. Invalid token in localStorage");
      // Try to clear potentially stale token
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }

    console.error("[API] Request failed:", {
      endpoint,
      method: options?.method || "GET",
      status: response.status,
      statusText: response.statusText,
      error: errorData,
      rawResponse: rawText.substring(0, 500),
    });

    const errorMessage = errorData?.detail || errorData?.message || `HTTP ${response.status}: ${response.statusText}`;
    const error = new Error(String(errorMessage));
    // Attach status code to error for easier checking in catch blocks
    (error as any).statusCode = response.status;
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
