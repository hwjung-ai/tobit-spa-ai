type CopilotMetricEvent =
  | "contract_ok"
  | "contract_violation"
  | "auto_repair_attempt"
  | "auto_repair_success"
  | "auto_repair_failed"
  | "parse_success"
  | "parse_failure";

interface CopilotMetricsStore {
  counters: Record<string, number>;
  updated_at: string;
}

const METRICS_KEY = "copilot:metrics:v1";

export const recordCopilotMetric = (
  builderSlug: string,
  event: CopilotMetricEvent,
  reason?: string | null
) => {
  if (typeof window === "undefined") return;

  const scopedKey = `${builderSlug}:${event}`;
  let store: CopilotMetricsStore = {
    counters: {},
    updated_at: new Date().toISOString(),
  };

  try {
    const raw = window.localStorage.getItem(METRICS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as CopilotMetricsStore;
      if (parsed && typeof parsed === "object" && parsed.counters) {
        store = parsed;
      }
    }
  } catch {
    // ignore corrupted local metrics
  }

  store.counters[scopedKey] = (store.counters[scopedKey] ?? 0) + 1;
  store.updated_at = new Date().toISOString();

  try {
    window.localStorage.setItem(METRICS_KEY, JSON.stringify(store));
  } catch {
    // ignore storage quota errors
  }

  if (reason) {
    console.info(`[CopilotMetric] ${scopedKey}`, { reason });
  } else {
    console.info(`[CopilotMetric] ${scopedKey}`);
  }
};

