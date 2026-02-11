// Note: These types are derived from the backend Python schemas
// You may need to update them when the backend schemas change

export interface ReplanTrigger {
  trigger_type: string;
  stage_name: string;
  severity: string;
  reason: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ReplanPatchDiff {
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export interface ReplanEvent {
  event_type: string;
  stage_name: string;
  trigger: ReplanTrigger;
  patch: ReplanPatchDiff;
  timestamp: string;
  decision_metadata?: Record<string, unknown>;
  execution_metadata?: Record<string, unknown>;
}

export interface UIActionRequest {
  trace_id?: string;
  action_id: string;
  inputs: Record<string, unknown>;
  context: Record<string, unknown>;
}

export interface UIActionResponse {
  trace_id: string;
  status: "ok" | "error";
  blocks: unknown[];
  references: unknown[];
  state_patch?: Record<string, unknown>;
  error?: Record<string, unknown>;
}

export interface OpsQueryRequest {
  mode: "config" | "history" | "relation" | "metric" | "all" | "hist" | "graph";
  question: string;
}

export interface RerunGraphPatch {
  depth?: number;
  limits?: Record<string, number>;
  view?: unknown;
}

export interface RerunAggregatePatch {
  group_by?: string[];
  top_n?: number;
}

export interface RerunOutputPatch {
  primary?: string;
  blocks?: string[];
}

export interface RerunMetricPatch {
  time_range?: string;
  agg?: "count" | "max" | "min" | "avg";
  mode?: "aggregate" | "series";
}

export interface RerunHistoryPatch {
  time_range?: "last_24h" | "last_7d" | "last_30d";
  limit?: number;
}

export interface RerunListPatch {
  offset?: number;
  limit?: number;
}

export interface RerunAutoPathPatch {
  source_ci_code?: string;
  target_ci_code?: string;
}

export interface RerunAutoGraphScopePatch {
  include_metric?: boolean;
  include_history?: boolean;
}

export interface RerunAutoPatch {
  path?: RerunAutoPathPatch;
  graph_scope?: RerunAutoGraphScopePatch;
}

export interface RerunPatch {
  view?: unknown;
  graph?: RerunGraphPatch;
  aggregate?: RerunAggregatePatch;
  output?: RerunOutputPatch;
  metric?: RerunMetricPatch;
  history?: RerunHistoryPatch;
  auto?: RerunAutoPatch;
  list?: RerunListPatch;
}

export interface RerunContext {
  selected_ci_id?: string;
  selected_secondary_ci_id?: string;
}

export interface RerunRequest {
  base_plan: unknown;
  selected_ci_id?: string;
  selected_secondary_ci_id?: string;
  patch?: RerunPatch;
}

export interface CiAskRequest {
  question: string;
  rerun?: RerunRequest;
}

export interface CiAskResponse {
  answer: string;
  blocks: unknown[];
  trace: Record<string, unknown>;
  next_actions: unknown[];
  meta?: Record<string, unknown>;
}

export interface StageInput {
  stage: string;
  applied_assets: Record<string, string>;
  params: Record<string, unknown>;
  prev_output?: Record<string, unknown>;
  trace_id?: string;
}

export interface StageDiagnostics {
  status: string;
  warnings: string[];
  errors: string[];
  empty_flags: Record<string, boolean>;
  counts: Record<string, number>;
}

export interface StageOutput {
  stage: string;
  result: Record<string, unknown>;
  diagnostics: StageDiagnostics;
  references: unknown[];
  duration_ms: number;
}
