import type { AnswerBlock as RendererAnswerBlock, AnswerMeta } from "@/components/answer/BlockRenderer";
import type { ReplanEvent } from "@/components/ops/ReplanTimeline";
import type {
  AnswerBlock as ApiAnswerBlock,
  AnswerEnvelope,
  CiAnswerPayload,
  LocalOpsHistoryEntry,
  ServerHistoryEntry,
  StageInput,
  StageOutput,
  StageSnapshot,
  StageStatus,
} from "@/lib/apiClientTypes";

export type BackendMode = "config" | "all" | "metric" | "hist" | "graph" | "document";
export type UiMode = "ci" | "metric" | "history" | "relation" | "document" | "all";

export const formatTimestamp = (value: string) => {
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
    const kstOffset = 9 * 60 * 60 * 1000;
    const kstTime = new Date(date.getTime() + kstOffset);
    const year = kstTime.getUTCFullYear();
    const month = String(kstTime.getUTCMonth() + 1).padStart(2, "0");
    const day = String(kstTime.getUTCDate()).padStart(2, "0");
    const hours = String(kstTime.getUTCHours()).padStart(2, "0");
    const minutes = String(kstTime.getUTCMinutes()).padStart(2, "0");
    const seconds = String(kstTime.getUTCSeconds()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} +9:00`;
  } catch {
    return value;
  }
};

const safeStringify = (value: unknown) => {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

export const normalizeAnswerMeta = (meta: unknown, fallbackSummary: string): AnswerMeta => {
  const candidate = (meta ?? {}) as Partial<AnswerMeta>;
  return {
    route: candidate.route ?? "ci",
    route_reason: candidate.route_reason ?? "CI tab",
    timing_ms: candidate.timing_ms ?? 0,
    summary: candidate.summary ?? fallbackSummary,
    used_tools: candidate.used_tools ?? [],
    fallback: candidate.fallback,
    error: candidate.error,
    trace_id: candidate.trace_id,
  };
};

const normalizeStageStatus = (status?: string | null): StageStatus => {
  if (status === "ok" || status === "warning" || status === "error" || status === "skipped") {
    return status;
  }
  return "pending";
};

const previewFromBlock = (block: RendererAnswerBlock | ApiAnswerBlock) => {
  const previewBlock = block as Record<string, unknown>;
  switch (previewBlock.type) {
    case "markdown":
      return previewBlock.content as string;
    case "table":
      return (previewBlock.rows as string[][] | undefined)?.[0]?.join(" ");
    case "timeseries":
      return ((previewBlock.series as Array<{ name?: string }> | undefined)?.[0]?.name) ?? "";
    case "graph":
      return ((previewBlock.nodes as Array<{ data?: { label?: string } }> | undefined)?.[0]?.data?.label) ?? "";
    case "references":
      return ((previewBlock.items as Array<{ title?: string }> | undefined)?.[0]?.title) ?? "";
    case "text":
      return previewBlock.text as string;
    case "number":
      return `${previewBlock.label}: ${previewBlock.value}`;
    case "network":
      return `${(previewBlock.nodes as unknown[] | undefined)?.length ?? 0} nodes`;
    case "path":
      return `Hops: ${previewBlock.hop_count}`;
    default:
      return "";
  }
};

export const buildStageSnapshots = (
  stageInputs?: StageInput[],
  stageOutputs?: StageOutput[]
): StageSnapshot[] => {
  if (!stageInputs || !stageOutputs) return [];
  const stageLabels: Record<string, string> = {
    route_plan: "Route Plan",
    validate: "Validate",
    execute: "Execute",
    compose: "Compose",
    present: "Present",
  };
  return stageInputs.map((input: StageInput, index: number) => {
    const output = stageOutputs.find((entry) => entry?.stage === input.stage);
    const stageName = input.stage || `stage_${index}`;
    return {
      name: stageName,
      label: stageLabels[stageName] || stageName,
      status: normalizeStageStatus(output?.diagnostics?.status),
      duration_ms: output?.duration_ms || 0,
      input,
      output: output || null,
      diagnostics: output?.diagnostics || null,
    };
  });
};

export const parseReplanEvents = (events?: unknown[]): ReplanEvent[] => {
  if (!events || !Array.isArray(events)) return [];
  return events.map((event: Record<string, unknown>) => ({
    id: event.id as string,
    event_type: (event.event_type as string) || "replan_event",
    stage_name: (event.stage_name as string) || "unknown",
    trigger: (event.trigger as {
      trigger_type: string;
      reason: string;
      severity: string;
      stage_name: string;
    }) || {
      trigger_type: "unknown",
      reason: "Unknown trigger",
      severity: "medium",
      stage_name: (event.stage_name as string) || "unknown",
    },
    patch: (event.patch as { before: unknown; after: unknown }) || { before: {}, after: {} },
    timestamp: (event.timestamp as string) || new Date().toISOString(),
    decision_metadata: event.decision_metadata as {
      trace_id: string;
      should_replan: boolean;
      evaluation_time: number;
    } | null,
  }));
};

export const extractSummary = (envelope: AnswerEnvelope | null, question: string): string => {
  if (!envelope) return question || "(no summary)";
  if (envelope.meta?.summary) return safeStringify(envelope.meta.summary);
  const candidate = envelope.blocks?.map(previewFromBlock).find((value) => value);
  if (candidate) return candidate.split("\n")[0];
  return question || "(no summary)";
};

export const normalizeError = async (error: unknown) => {
  if (error instanceof Error) return { message: error.message, details: error.stack };
  if (error instanceof Response) {
    try {
      const data = await error.clone().json();
      return { message: data?.message ?? `${error.status} ${error.statusText}`, details: data };
    } catch {
      const text = await error.clone().text();
      return { message: `${error.status} ${error.statusText}`, details: text };
    }
  }
  if (typeof error === "object" && error !== null) {
    try {
      const obj = error as { message?: string };
      return { message: obj.message ?? "Unknown error", details: obj };
    } catch {
      return { message: "Unknown error", details: error };
    }
  }
  return { message: String(error), details: error };
};

export const buildErrorEnvelope = (backendMode: BackendMode, message: string): AnswerEnvelope => ({
  meta: {
    route: backendMode,
    route_reason: "client error",
    timing_ms: 0,
    summary: message,
    used_tools: [],
    fallback: true,
    error: message,
  },
  blocks: [
    {
      type: "markdown",
      title: "Error",
      content: `🟥 ${message}`,
    },
  ],
});

export const normalizeHistoryResponse = (
  response: ServerHistoryEntry["response"]
): AnswerEnvelope | CiAnswerPayload | null => {
  if (!response || typeof response !== "object") return null;
  const maybeEnvelope = response as AnswerEnvelope;
  if (Array.isArray(maybeEnvelope.blocks)) return maybeEnvelope;
  const responseWithData = response as { data?: unknown };
  const data = responseWithData.data;
  if (data && typeof data === "object") {
    const maybeCi = data as CiAnswerPayload;
    if (Array.isArray(maybeCi.blocks) || typeof maybeCi.answer === "string") return maybeCi;
    const maybeAnswer = (data as { answer?: AnswerEnvelope }).answer;
    if (maybeAnswer && Array.isArray(maybeAnswer.blocks)) return maybeAnswer;
  }
  return null;
};

export const hydrateServerEntry = (entry: ServerHistoryEntry): LocalOpsHistoryEntry | null => {
  const metadata = entry.metadata;
  const backendMode = metadata?.backendMode ?? metadata?.backend_mode ?? entry.feature ?? "config";
  const response = entry.response;
  const normalizedResponse = normalizeHistoryResponse(response);
  if (!normalizedResponse) return null;
  const envelope: AnswerEnvelope | CiAnswerPayload = normalizedResponse;
  let blocks = ((envelope as AnswerEnvelope).blocks ??
    (envelope as CiAnswerPayload).blocks) as ApiAnswerBlock[] | undefined;

  // Fix document URLs: replace old /documents/ URLs with /api/documents/
  if (blocks && Array.isArray(blocks)) {
    blocks = blocks.map((block) => {
      if (block?.type === "references" && Array.isArray(block.items)) {
        return {
          ...block,
          items: (block.items as Array<Record<string, unknown>>).map((item) => {
            const url = typeof item?.url === "string" ? item.url : null;
            if (url && url.includes("/documents/") && !url.includes("/api/documents/")) {
              return {
                ...item,
                url: url.replace("/documents/", "/api/documents/"),
              };
            }
            return item;
          }),
        };
      }
      return block;
    }) as ApiAnswerBlock[];
  }

  if (!blocks || !Array.isArray(blocks)) return null;
  const uiMode = (metadata?.uiMode ?? metadata?.ui_mode ?? "ci") as UiMode;
  const status = entry.status === "error" ? "error" : "ok";
  const traceId =
    metadata?.trace_id ||
    metadata?.trace?.trace_id ||
    (envelope as AnswerEnvelope | CiAnswerPayload)?.meta?.trace_id ||
    (envelope as CiAnswerPayload)?.trace?.trace_id ||
    (response as { data?: { trace?: { trace_id?: string } } })?.data?.trace?.trace_id;
  const responseTrace = (envelope as CiAnswerPayload)?.trace;
  const trace = metadata?.trace
    ? { ...metadata.trace, trace_id: traceId }
    : responseTrace
      ? { ...responseTrace, trace_id: traceId }
      : { trace_id: traceId };

  return {
    id: entry.id,
    createdAt: entry.created_at,
    uiMode,
    backendMode: backendMode as BackendMode,
    question: entry.question,
    thread_id: entry.thread_id ?? metadata?.thread_id ?? null,
    response: { ...envelope, blocks },
    status,
    summary: (entry.summary ?? extractSummary(envelope as AnswerEnvelope, entry.question)) ?? "",
    errorDetails: metadata?.errorDetails ?? metadata?.error_details,
    trace,
    nextActions: metadata?.nextActions ?? metadata?.next_actions,
    next_actions: metadata?.nextActions ?? metadata?.next_actions,
  };
};
