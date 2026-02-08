import type { ExecutionTraceDetail } from "../apiClient/index";

export interface FilterState {
  q: string;
  feature: string;
  status: string;
  from: string;
  to: string;
  assetId: string;
}

export interface TraceDetailResponse {
  trace: ExecutionTraceDetail;
  audit_logs?: import("../adminUtils").AuditLog[];
}

export const PER_PAGE = 20;

export const STAGE_ORDER = ["route_plan", "validate", "execute", "compose", "present"];
export const STAGE_LABELS: Record<string, string> = {
  route_plan: "ROUTE+PLAN",
  validate: "VALIDATE",
  execute: "EXECUTE",
  compose: "COMPOSE",
  present: "PRESENT",
};

export const initialFilters: FilterState = {
  q: "",
  feature: "",
  status: "",
  from: "",
  to: "",
  assetId: "",
};

export const createPlaceholderTraceDetail = (traceId: string): ExecutionTraceDetail => ({
  trace_id: traceId,
  parent_trace_id: null,
  created_at: new Date().toISOString(),
  feature: "test",
  endpoint: "/ops/query",
  method: "POST",
  ops_mode: "ci",
  question: "Test trace",
  status: "unknown",
  duration_ms: 0,
  request_payload: null,
  route: "orch",
  applied_assets: {
    prompt: null,
    policy: null,
    mapping: null,
    queries: [],
    screens: [],
  },
  asset_versions: [],
  fallbacks: {},
  plan_raw: null,
  plan_validated: null,
  execution_steps: [],
  references: [],
  answer: { envelope_meta: null, blocks: [] },
  ui_render: { rendered_blocks: [], warnings: [] },
  audit_links: {},
  flow_spans: [],
  stage_inputs: [],
  stage_outputs: [],
  replan_events: [],
});
