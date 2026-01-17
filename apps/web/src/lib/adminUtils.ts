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
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
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
