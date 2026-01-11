export interface RerunActionPayload {
  selected_ci_id?: string;
  selected_secondary_ci_id?: string;
  patch?: {
    view?: "SUMMARY" | "COMPOSITION" | "DEPENDENCY" | "IMPACT" | "PATH" | "NEIGHBORS";
    graph?: {
      depth?: number;
      limits?: {
        max_nodes?: number;
        max_edges?: number;
      };
    };
    aggregate?: {
      group_by?: string[];
      top_n?: number;
    };
    output?: {
      primary?: "text" | "table" | "network" | "path" | "number" | "markdown";
      blocks?: string[];
    };
  };
}

export interface OpenEventBrowserPayload {
  exec_log_id?: string;
  simulation_id?: string;
  tenant_id: string;
}

export type NextAction =
  | { type: "rerun"; label: string; payload: RerunActionPayload }
  | { type: "open_trace"; label: string }
  | { type: "copy_payload"; label: string; payload: unknown }
  | { type: "open_event_browser"; label: string; payload: OpenEventBrowserPayload };
