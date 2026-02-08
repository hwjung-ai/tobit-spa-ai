/**
 * API Manager type definitions
 * Extracted from api-manager/page.tsx for reusability
 */

export type ScopeType = "system" | "custom";
export type CenterTab = "definition" | "logic" | "test";
export type LogicType = "sql" | "workflow" | "python" | "script" | "http";
export type SystemView = "discovered" | "registered";

export interface ApiDefinitionItem {
  api_id: string;
  api_name: string;
  api_type: ScopeType;
  method: "GET" | "POST" | "PUT" | "DELETE";
  endpoint: string;
  logic_type: LogicType;
  logic_body: string;
  description: string | null;
  tags: string[];
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  param_schema: Record<string, unknown>;
  runtime_policy: Record<string, unknown>;
  logic_spec: Record<string, unknown>;
  source?: ApiSource;
}

export type ApiSource = "server" | "local";

export interface SystemApiItem extends ApiDefinitionItem {
  source: ApiSource;
}

export interface DiscoveredEndpoint {
  method: string;
  path: string;
  operationId?: string | null;
  summary?: string | null;
  description?: string | null;
  tags?: string[];
  parameters?: unknown[];
  requestBody?: Record<string, unknown> | null;
  responses?: Record<string, unknown> | null;
  source: "openapi" | "router";
}

export interface ExecuteResult {
  executed_sql: string;
  params: Record<string, unknown>;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  duration_ms: number;
}

export interface ExecLogEntry {
  exec_id: string;
  executed_at: string;
  executed_by: string | null;
  status: string;
  duration_ms: number;
  row_count: number;
  request_params: Record<string, unknown> | null;
  error_message: string | null;
}

export interface WorkflowStepResult {
  node_id: string;
  node_type: "sql" | "script";
  status: "success" | "fail";
  duration_ms: number;
  row_count: number;
  columns?: string[];
  output?: Record<string, unknown>;
  error_message?: string | null;
  references?: Record<string, unknown>;
}

export interface WorkflowExecuteResult {
  steps: WorkflowStepResult[];
  final_output: Record<string, unknown>;
  references: Record<string, unknown>[];
}

export type ApiDraftBase = {
  api_name: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  endpoint: string;
  description: string;
  tags: string[];
  params_schema: Record<string, unknown>;
  runtime_policy: Record<string, unknown>;
  is_active: boolean;
};

export type SqlLogic = {
  type: "sql";
  query: string;
  timeout_ms?: number;
};

export type HttpLogic = {
  type: "http";
  spec: {
    method: string;
    url: string;
    headers?: Record<string, string>;
    params?: Record<string, unknown>;
    body?: unknown;
  };
  timeout_ms?: number;
};

export type ApiDraft = ApiDraftBase & {
  logic: SqlLogic | HttpLogic;
  [key: string]: unknown;
};

export type DraftStatus =
  | "idle"
  | "draft_ready"
  | "previewing"
  | "testing"
  | "applied"
  | "saved"
  | "outdated"
  | "error";
