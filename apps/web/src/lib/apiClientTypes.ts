/**
 * Type definitions for API client responses
 * Centralized to ensure consistent typing across application
 */

/**
 * Re-plan event type
 * Re-exported from components/ops/ReplanTimeline for consistency
 * Must be imported at top level to avoid circular dependency issues
 */
export type { ReplanEvent } from "../components/ops/ReplanTimeline";
export type { NextAction } from "../app/ops/nextActions";

export type BackendMode = "config" | "all" | "metric" | "hist" | "graph";
export type UiMode = "ci" | "metric" | "history" | "relation" | "all";

/**
 * Standard API response wrapper
 * All endpoints should return data in this format
 */
export interface ApiResponse<T = unknown> {
  data: T;
}

/**
 * ResponseEnvelope - alternative API response format
 * Used by some admin endpoints
 */
export interface ResponseEnvelope<T = unknown> {
  ok: boolean;
  data?: T;
  json?: unknown;
  message?: string;
  statusCode?: number;
}

/**
 * Type guard to check if a response has valid data
 */
export function hasApiResponseData<T>(response: ApiResponse<unknown>): response is ApiResponse<T> {
  return response !== null && 
         typeof response === 'object' && 
         'data' in response;
}

/**
 * Helper function to extract data from API response with type safety
 * Use this instead of direct response.data access
 */
export function getApiResponseData<T>(response: ApiResponse<unknown>, fallback?: T): T {
  if (hasApiResponseData<T>(response)) {
    return response.data as T;
  }
  return (fallback ?? null) as T;
}

/**
 * API Error response shape
 */
export interface ApiError {
  message: string;
  code?: string | number;
  details?: unknown;
}

/**
 * Type guard for API errors
 */
export function isApiError(error: unknown): error is ApiError {
  return error !== null && 
         typeof error === 'object' && 
         'message' in error;
}

/**
 * Scan-related types
 */
export interface ScanResult {
  success: boolean;
  message: string;
  tables?: Array<{
    table_name: string;
    row_count?: number;
    columns?: string[];
  }>;
}

export function isScanResult(data: unknown): data is ScanResult {
  if (!data || typeof data !== 'object') return false;
  const d = data as Record<string, unknown>;
  return typeof d.success === 'boolean' &&
         typeof d.message === 'string';
}

/**
 * Asset-related types
 */
export interface AssetVersion {
  id: string;
  asset_id: string;
  asset_type: string;
  version: string;
  name: string;
  description?: string;
  created_at: string;
  status: "published" | "draft" | "archived";
  author: string;
  size: number;
  metadata?: Record<string, unknown>;
}

export interface Asset {
  asset_id: string;
  asset_type?: string;
  name?: string;
  description?: string;
  version?: number | string;
  status?: string;
  tags?: string[] | Record<string, unknown> | null;
  updated_at?: string;
  published_at?: string;
  created_at?: string;
  schema_definition?: unknown;
}

export interface ConnectionConfig {
  host?: string;
  port?: number;
  username?: string;
  database?: string;
  timeout?: number;
  ssl_mode?: string;
  connection_params?: Record<string, unknown>;
}

/**
 * Thread-related types
 */
export interface ThreadRead {
  id: string;
  title: string;
  tenant_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface MessageRead {
  id: string;
  thread_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  token_in?: number;
  token_out?: number;
}

export interface ThreadDetail {
  id: string;
  title: string;
  tenant_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  messages: MessageRead[];
}

/**
 * Trace-related types
 */
export interface TraceSummaryRow {
  trace_id: string;
  created_at: string;
  feature: string;
  status: string;
  duration_ms: number;
  question_snippet: string;
  applied_asset_versions: string[];
  route?: string;
  replan_count?: number;
}

export interface TraceListResponse {
  traces: TraceSummaryRow[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * AnswerBlock type for OPS/CI responses
 */
export interface AnswerBlock {
  type: string;
  title?: string | null;
  payload_summary?: string | null;
  references?: Array<{
    ref_type: string;
    name: string;
    engine?: string | null;
    statement?: string | null;
    params?: Record<string, unknown> | null;
    row_count?: number | null;
    latency_ms?: number | null;
    source_id?: string | null;
  }>;
  [key: string]: unknown;
}

/**
 * Execution step type
 */
export interface ExecutionStep {
  step_id: string | null;
  tool_name: string | null;
  status: string;
  duration_ms: number;
  request: Record<string, unknown> | null;
  response: Record<string, unknown> | null;
  error: {
    message: string;
    details?: unknown;
    stack?: string;
  } | null;
  timestamp?: string;
  references?: Array<{
    ref_type: string;
    name: string;
    engine?: string | null;
    statement?: string | null;
    params?: Record<string, unknown> | null;
    row_count?: number | null;
    latency_ms?: number | null;
    source_id?: string | null;
  } | null>;
}

/**
 * Flow span type
 */
export interface FlowSpan {
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: string;
  status: string;
  ts_start_ms: number;
  ts_end_ms: number;
  duration_ms: number;
  summary: {
    note?: string;
    error_type?: string;
    error_message?: string;
  };
  links: {
    plan_path?: string;
    tool_call_id?: string;
    block_id?: string;
  };
  tool_name?: string;
  request?: Record<string, unknown> | null;
  response?: Record<string, unknown> | null;
  error?: string | null;
  timestamp?: string;
}

/**
 * Stage input/output types
 */
export interface StageInput {
  stage: string;
  input?: Record<string, unknown> | null;
}

export interface StageOutput {
  stage: string;
  result?: Record<string, unknown> | null;
  diagnostics?: {
    status?: string;
    warnings?: string[];
    errors?: string[];
  } | null | undefined;
  references?: Array<{
    ref_type: string;
    name: string;
    engine?: string | null;
    statement?: string | null;
    params?: Record<string, unknown> | null;
    row_count?: number | null;
    latency_ms?: number | null;
    source_id?: string | null;
  } | null | undefined>;
  duration_ms?: number;
}

/**
 * UI rendered block type
 */
export interface UIRenderedBlock {
  block_type: string;
  component_name: string;
  ok: boolean;
  error?: string;
}

/**
 * Execution trace detail type
 */
export interface ExecutionTraceDetail {
  trace_id: string;
  parent_trace_id: string | null;
  created_at: string;
  feature: string;
  endpoint: string;
  method: string;
  ops_mode: string;
  question: string;
  status: string;
  duration_ms: number;
  request_payload: Record<string, unknown> | null;
  route?: string | null;
  applied_assets: {
    prompt?: {
      asset_id: string | null;
      name: string | null;
      version: number | null;
      source: string | null;
      scope?: string | null;
      engine?: string | null;
      policy_type?: string | null;
      mapping_type?: string | null;
      screen_id?: string | null;
      status?: string | null;
    } | null;
    policy?: {
      asset_id: string | null;
      name: string | null;
      version: number | null;
      source: string | null;
      scope?: string | null;
      engine?: string | null;
      policy_type?: string | null;
      mapping_type?: string | null;
      screen_id?: string | null;
      status?: string | null;
    } | null;
    mapping?: {
      asset_id: string | null;
      name: string | null;
      version: number | null;
      source: string | null;
      scope?: string | null;
      engine?: string | null;
      policy_type?: string | null;
      mapping_type?: string | null;
      screen_id?: string | null;
      status?: string | null;
    } | null;
    queries?: Array<{
      asset_id: string | null;
      name: string | null;
      version: number | null;
      source: string | null;
      scope?: string | null;
      engine?: string | null;
      policy_type?: string | null;
      mapping_type?: string | null;
      screen_id?: string | null;
      status?: string | null;
    } | null>;
    screens?: Array<{
      asset_id: string | null;
      name: string | null;
      version: number | null;
      source: string | null;
      scope?: string | null;
      engine?: string | null;
      policy_type?: string | null;
      mapping_type?: string | null;
      screen_id?: string | null;
      status?: string | null;
    } | null>;
  } | null;
  asset_versions: string[] | null;
  fallbacks: Record<string, boolean> | null;
  plan_raw: Record<string, unknown> | null;
  plan_validated: Record<string, unknown> | null;
  execution_steps: ExecutionStep[] | null;
  references: Array<{
    ref_type: string;
    name: string;
    engine?: string | null;
    statement?: string | null;
    params?: Record<string, unknown> | null;
    row_count?: number | null;
    latency_ms?: number | null;
    source_id?: string | null;
  }> | null;
  answer: {
    envelope_meta: Record<string, unknown> | null;
    blocks: AnswerBlock[] | null;
  } | null;
  ui_render: {
    rendered_blocks: UIRenderedBlock[] | null;
    warnings: string[] | null;
  } | null;
  audit_links: Record<string, unknown> | null;
  flow_spans: FlowSpan[] | null;
  stage_inputs?: StageInput[] | null;
  stage_outputs?: StageOutput[] | null;
  replan_events?: ReplanEvent[] | null;
}

/**
 * ReplanTimelineEvent - alias for ReplanEvent for compatibility
 */
export type ReplanTimelineEvent = ReplanEvent;

/**
 * Reference entry type
 */
export interface ReferenceEntry {
  ref_type: string;
  name: string;
  engine?: string | null;
  statement?: string | null;
  params?: Record<string, unknown> | null;
  row_count?: number | null;
  latency_ms?: number | null;
  source_id?: string | null;
}

/**
 * Asset summary type
 */
export interface AssetSummary {
  asset_id: string | null;
  name: string | null;
  version: number | string | null;
  source: string | null;
  scope?: string | null;
  engine?: string | null;
  policy_type?: string | null;
  mapping_type?: string | null;
  screen_id?: string | null;
  status?: string | null;
  description?: string | null;
  tags?: string[] | null;
  created_at?: string | null;
  updated_at?: string | null;
}

/**
 * Asset override type
 */
export interface AssetOverride {
  asset_type: string;
  asset_name: string;
  version: string;
  reason: string;
}

/**
 * Stage status type
 */
export type StageStatus = "pending" | "ok" | "warning" | "error" | "skipped";

/**
 * Stage snapshot type for pipeline display
 */
export interface StageSnapshot {
  name: string;
  label: string;
  status: StageStatus;
  duration_ms?: number;
  input: StageInput | null;
  output: StageOutput | null;
  diagnostics: {
    warnings?: string[];
    errors?: string[];
    status?: string;
  } | null;
}

/**
 * CI Answer payload type
 */
export interface CiAnswerPayload {
  answer: string;
  blocks: AnswerBlock[];
  data?: { answer?: AnswerEnvelope };
  trace?: {
    plan_validated?: unknown;
    policy_decisions?: unknown;
    [key: string]: unknown;
  };
  next_actions?: NextAction[];
  nextActions?: NextAction[];
  meta?: {
    model?: string;
    tokens?: {
      input: number;
      output: number;
    };
    [key: string]: unknown;
  };
}

/**
 * API Server history entry type
 */
export interface ApiServerHistoryEntry {
  id: string;
  tenant_id: string;
  user_id: string;
  feature: string;
  question: string;
  summary: string | null;
  status: "ok" | "error";
  response: AnswerEnvelope | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

/**
 * Local OPS history entry type
 */
export interface LocalOpsHistoryEntry {
  id: string;
  createdAt: string;
  uiMode: UiMode;
  backendMode: BackendMode;
  question: string;
  response: AnswerEnvelope | CiAnswerPayload;
  status: "ok" | "error";
  meta?: {
    route?: string;
    route_reason?: string;
    timing_ms?: number;
    summary?: string;
    used_tools?: string[];
    fallback?: boolean;
    error?: string;
    trace_id?: string;
    nextActions?: NextAction[];
    next_actions?: NextAction[];
    errorDetails?: string;
  };
  summary?: string;
  errorDetails?: string;
  trace?: {
    plan_validated?: unknown;
    policy_decisions?: unknown;
    [key: string]: unknown;
  };
  nextActions?: NextAction[];
  next_actions?: NextAction[];
}

/**
 * Answer envelope type
 */
export interface AnswerEnvelope {
  status?: number | string;
  ok?: boolean;
  answer?: string;
  blocks?: AnswerBlock[];
  meta?: {
    model?: string;
    tokens?: {
      input: number;
      output: number;
    };
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

/**
 * Server history entry type
 */
export interface ServerHistoryEntry {
  id: string;
  created_at: string;
  question: string;
  status: "ok" | "error";
  summary?: string | null;
  metadata?: {
    backendMode?: BackendMode | string;
    backend_mode?: BackendMode | string;
    uiMode?: UiMode | string;
    ui_mode?: UiMode | string;
    route?: string;
    route_reason?: string;
    timing_ms?: number;
    summary?: string;
    used_tools?: string[];
    fallback?: boolean;
    error?: string;
    errorDetails?: string;
    error_details?: string;
    trace_id?: string;
    trace?: {
      plan_validated?: unknown;
      policy_decisions?: unknown;
      [key: string]: unknown;
    };
    nextActions?: NextAction[];
    next_actions?: NextAction[];
  } | null;
  response?: AnswerEnvelope | CiAnswerPayload | null;
  feature?: string;
  [key: string]: unknown;
}

/**
 * Fetch options for API requests
 */
export interface FetchOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: string;
  credentials?: RequestCredentials;
  [key: string]: unknown;
}
