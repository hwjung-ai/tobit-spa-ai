export type CenterTab = "definition" | "definition-form" | "test" | "logs";
export type TriggerType = "metric" | "event" | "schedule" | "anomaly";

export interface CepRule {
  rule_id: string;
  rule_name: string;
  trigger_type: TriggerType;
  trigger_spec: Record<string, unknown>;
  action_spec: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CepExecLog {
  exec_id: string;
  rule_id: string;
  triggered_at: string;
  status: string;
  duration_ms: number;
  error_message: string | null;
  references: Record<string, unknown>;
}

export interface CepDraft {
  rule_name: string;
  description?: string;
  trigger: Record<string, unknown>;
  conditions?: Record<string, unknown>[];
  enrichments?: Record<string, unknown>[];
  actions?: Record<string, unknown>[];
  references?: Record<string, unknown>;
}

export type DraftStatus = "idle" | "draft_ready" | "previewing" | "testing" | "applied" | "saved" | "outdated" | "error";

export interface Condition {
  id: string;
  field: string;
  op: string;
  value: string;
}

export interface Action {
  id: string;
  type: "webhook" | "notify" | "trigger" | "store";
  endpoint?: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  channels?: string[];
  message?: string;
}
