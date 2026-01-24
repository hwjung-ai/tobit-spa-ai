export interface OpsSummaryData {
  totalQueries: number;
  successRate: number;
  avgResponseTime: number;
  recentActivity: Array<{
    timestamp: string;
    type: "ci" | "metric" | "history" | "relation" | "all";
    status: "ok" | "error";
  }>;
}

export interface OpsHistoryEntry {
  id: string;
  createdAt: string;
  uiMode: "ci" | "metric" | "history" | "relation" | "all";
  backendMode: "config" | "all" | "metric" | "hist" | "graph";
  question: string;
  response: {
    meta?: {
      route?: string;
      route_reason?: string;
      timing_ms?: number;
      summary?: string;
      used_tools?: string[];
      fallback?: boolean;
      error?: string;
      trace_id?: string;
    };
    blocks?: Array<{
      type: string;
      [key: string]: unknown;
    }>;
  };
  status: "ok" | "error";
  summary: string | undefined;
  errorDetails?: string;
  trace?: unknown;
  nextActions?: Array<{
    type: string;
    payload?: unknown;
  }>;
}