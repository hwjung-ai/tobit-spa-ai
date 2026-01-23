"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import BlockRenderer, {
  type AnswerBlock,
  type AnswerEnvelope,
  type AnswerMeta,
} from "../../components/answer/BlockRenderer";
import { type NextAction } from "./nextActions";
import { authenticatedFetch } from "@/lib/apiClient";
import OpsSummaryStrip from "@/components/ops/OpsSummaryStrip";
import { type OpsHistoryEntry } from "@/components/ops/types/opsTypes";

type BackendMode = "config" | "all" | "metric" | "hist" | "graph";
type UiMode = "ci" | "metric" | "history" | "relation" | "all";

const UI_MODES: { id: UiMode; label: string; backend: BackendMode }[] = [
  { id: "ci", label: "구성", backend: "config" },
  { id: "metric", label: "수치", backend: "metric" },
  { id: "history", label: "이력", backend: "hist" },
  { id: "relation", label: "연결", backend: "graph" },
  { id: "all", label: "전체", backend: "all" },
];

const MODE_STORAGE_KEY = "ops:mode";
const HISTORY_LIMIT = 40;

interface CiAnswerPayload {
  answer: string;
  blocks: AnswerBlock[];
  trace?: {
    plan_validated?: unknown;
    policy_decisions?: unknown;
    [key: string]: unknown;
  };
  next_actions?: NextAction[];
  meta?: AnswerMeta;
}

type OpsResponse = AnswerEnvelope | CiAnswerPayload;

interface OpsHistoryEntry {
  id: string;
  createdAt: string;
  uiMode: UiMode;
  backendMode: BackendMode;
  question: string;
  response: OpsResponse;
  status: "ok" | "error";
  summary: string;
  errorDetails?: string;
  trace?: unknown;
  nextActions?: NextAction[];
}

interface ServerHistoryEntry {
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

const formatTimestamp = (value: string) => {
  if (!value) return "";
  try {
    let dateStr = value;
    // If it looks like an ISO string (has T) but no timezone info (no Z, no +HH:MM/ -HH:MM), treat as UTC
    if (value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(value)) {
      dateStr = `${value}Z`;
    }
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

const safeStringify = (value: unknown) => {
  if (value == null) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

const previewFromBlock = (block: AnswerBlock) => {
  switch (block.type) {
    case "markdown":
      return block.content;
    case "table":
      return block.rows?.[0]?.join(" ");
    case "timeseries":
      return block.series?.[0]?.name ?? "";
    case "graph":
      return block.nodes?.[0]?.data?.label ?? "";
    case "references":
      return block.items?.[0]?.title ?? "";
    case "text":
      return block.text;
    case "number":
      return `${block.label}: ${block.value}`;
    case "network":
      return `${block.nodes.length} nodes`;
    case "path":
      return `Hops: ${block.hop_count}`;
    default:
      return "";
  }
};

const extractSummary = (envelope: AnswerEnvelope | null, question: string) => {
  if (!envelope) {
    return question || "(no summary)";
  }
  if (envelope.meta?.summary) {
    return safeStringify(envelope.meta.summary);
  }
  const candidate = envelope.blocks?.map(previewFromBlock).find((value) => value);
  if (candidate) {
    return candidate.split("\n")[0];
  }
  return question || "(no summary)";
};

const normalizeError = async (error: unknown) => {
  if (error instanceof Error) {
    return { message: error.message, details: error.stack };
  }
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

const buildErrorEnvelope = (backendMode: BackendMode, message: string): AnswerEnvelope => ({
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

const genId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const hydrateServerEntry = (entry: ServerHistoryEntry): OpsHistoryEntry | null => {
  const metadata = entry.metadata ?? {};
  const backendMode =
    (metadata?.backendMode ||
      metadata?.backend_mode ||
      entry.feature ||
      "config") as BackendMode;
  const response = entry.response;
  const envelope =
    response && Array.isArray(response.blocks)
      ? response
      : buildErrorEnvelope(backendMode, "Missing response data from history");
  if (!envelope.blocks || !Array.isArray(envelope.blocks)) {
    return null;
  }
  const uiMode =
    (metadata?.uiMode ?? metadata?.ui_mode ?? "ci") as UiMode;
  const status = entry.status === "error" ? "error" : "ok";
  return {
    id: entry.id,
    createdAt: entry.created_at,
    uiMode,
    backendMode,
    question: entry.question,
    response: envelope,
    status,
    summary: entry.summary ?? extractSummary(envelope, entry.question),
    errorDetails: metadata?.errorDetails ?? metadata?.error_details,
    trace: metadata?.trace,
    nextActions: metadata?.nextActions as NextAction[] | undefined,
  };
};

export default function OpsPage() {
  const [history, setHistory] = useState<OpsHistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [uiMode, setUiMode] = useState<UiMode>("all");
  const [question, setQuestion] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [traceCopyStatus, setTraceCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const router = useRouter();

  const currentModeDefinition = UI_MODES.find((item) => item.id === uiMode) ?? UI_MODES[0];
  const pushHistoryEntry = useCallback(
    (entry: OpsHistoryEntry) => {
      setHistory((prev) => {
        const next = [entry, ...prev];
        if (next.length > HISTORY_LIMIT) {
          return next.slice(0, HISTORY_LIMIT);
        }
        return next;
      });
      setSelectedId(entry.id);
    },
    [setHistory, setSelectedId]
  );

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const payload = await authenticatedFetch(`/history?feature=ops&limit=${HISTORY_LIMIT}`);
      const rawHistory = (payload?.data?.history ?? []) as ServerHistoryEntry[];
      const hydrated = rawHistory
        .map(hydrateServerEntry)
        .filter((entry): entry is OpsHistoryEntry => Boolean(entry));
      if (hydrated.length === 0) {
        setHistory([]);
        setSelectedId(null);
      } else {
        setHistory(hydrated);
        setSelectedId((prev) =>
          prev && hydrated.some((item) => item.id === prev) ? prev : hydrated[0].id
        );
      }
    } catch (error: unknown) {
      console.error("Failed to load OPS history", error);
      setHistoryError(error?.message || "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const persistHistoryEntry = useCallback(
    async (entry: OpsHistoryEntry) => {
      try {
        await authenticatedFetch(`/history`, {
          method: "POST",
          body: JSON.stringify({
            feature: "ops",
            question: entry.question,
            summary: entry.summary,
            status: entry.status,
            response: entry.response,
            metadata: {
              uiMode: entry.uiMode,
              backendMode: entry.backendMode,
              trace: entry.trace,
              nextActions: entry.nextActions,
              errorDetails: entry.errorDetails,
            },
          }),
        });
      } catch (error) {
        console.error("Failed to persist OPS history", error);
      }
    },
    []
  );

  const deleteHistoryEntry = useCallback(
    async (id: string) => {
      try {
        await authenticatedFetch(`/history/${id}`, {
          method: "DELETE",
        });
      } catch (error) {
        console.error("Failed to delete OPS history entry", error);
      }
    },
    []
  );

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    const savedMode = window.localStorage.getItem(MODE_STORAGE_KEY) as UiMode | null;
    if (savedMode && UI_MODES.some((item) => item.id === savedMode)) {
      setUiMode(savedMode);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(MODE_STORAGE_KEY, uiMode);
  }, [uiMode]);

  const selectedEntry = useMemo(() => {
    // If selectedId is set, find that specific entry
    if (selectedId) {
      const found = history.find((entry) => entry.id === selectedId);
      if (found) return found;
    }
    // Otherwise, return the most recent entry (first in array)
    return history[0] ?? null;
  }, [history, selectedId]);
  const meta = selectedEntry?.response?.meta;
  const traceData = selectedEntry?.trace as
    | {
      plan_validated?: unknown;
      policy_decisions?: Record<string, unknown>;
      [key: string]: unknown;
    }
    | undefined;
  const traceContents = useMemo(() => (traceData ? JSON.stringify(traceData, null, 2) : ""), [traceData]);
  const currentTraceId = selectedEntry?.response?.meta?.trace_id;

  useEffect(() => {
    setTraceOpen(false);
  }, [selectedEntry?.id]);

  useEffect(() => {
    setTraceCopyStatus("idle");
  }, [traceContents]);

  const handleModeSelection = useCallback((modeId: UiMode) => {
    setUiMode(modeId);
    setIsFullScreen(false);
  }, []);

  const handleCopyTrace = useCallback(async () => {
    if (!traceContents) {
      return;
    }
    try {
      await navigator.clipboard.writeText(traceContents);
      setTraceCopyStatus("copied");
      setTimeout(() => setTraceCopyStatus("idle"), 2000);
    } catch {
      setTraceCopyStatus("failed");
      setTimeout(() => setTraceCopyStatus("idle"), 2000);
    }
  }, [traceContents]);

  const handleCopyResultTraceId = useCallback(async () => {
    if (!currentTraceId) {
      return;
    }
    try {
      await navigator.clipboard.writeText(currentTraceId);
      setStatusMessage("Trace ID가 클립보드에 복사되었습니다.");
    } catch {
      setStatusMessage("Trace ID 복사에 실패했습니다.");
    }
  }, [currentTraceId]);

  const openInspectorTrace = useCallback(async () => {
    // Use selectedEntry's trace_id if available, otherwise use the most recent entry
    const traceId = currentTraceId || history[0]?.response?.meta?.trace_id;

    if (!traceId) {
      setStatusMessage("trace_id가 없습니다. 질의 응답에 trace_id가 포함되어 있는지 확인해주세요.");
      return;
    }

    // Verify trace exists before navigating
    try {
      setStatusMessage("Inspector에서 trace를 확인하는 중...");
      const response = await authenticatedFetch(`/inspector/traces/${encodeURIComponent(traceId)}`);
      if (!response?.data?.trace) {
        setStatusMessage(`Trace를 찾을 수 없습니다 (${traceId.slice(0, 8)}...). 서버에 저장되지 않았을 수 있습니다.`);
        return;
      }
      setStatusMessage(null);
      router.push(`/admin/inspector?trace_id=${encodeURIComponent(traceId)}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "알 수 없는 오류";
      if (errorMessage.includes("404") || errorMessage.includes("not found")) {
        setStatusMessage(`Trace (${traceId.slice(0, 8)}...)가 서버에 저장되지 않았습니다. 질의를 다시 실행해주세요.`);
      } else {
        setStatusMessage(`Trace 확인 실패: ${errorMessage}`);
      }
    }
  }, [currentTraceId, router, selectedEntry, history]);

  const traceCopyLabel =
    traceCopyStatus === "copied" ? "Copied!" : traceCopyStatus === "failed" ? "Retry" : "Copy";
  const traceCopyVariantClasses =
    traceCopyStatus === "copied"
      ? "border-emerald-500 text-emerald-300 hover:border-emerald-400"
      : traceCopyStatus === "failed"
        ? "border-rose-500 text-rose-300 hover:border-rose-400"
        : "border-slate-800 text-slate-400 hover:border-white hover:text-white";

  const handleRemoveHistory = useCallback(
    (id: string) => {
      setHistory((prev) => {
        const filtered = prev.filter((entry) => entry.id !== id);
        if (id === selectedId) {
          setSelectedId(filtered[0]?.id ?? null);
        }
        return filtered;
      });
      void deleteHistoryEntry(id);
    },
    [selectedId, deleteHistoryEntry]
  );

  const selectedLabel =
    UI_MODES.find((entry) => entry.id === (selectedEntry?.uiMode ?? uiMode))?.label ?? currentModeDefinition.label;

  const canFullScreen =
    selectedEntry?.backendMode === "graph" || meta?.route === "graph";

  const runQuery = useCallback(async () => {
    if (!question.trim() || isRunning) {
      return;
    }
    setIsRunning(true);
    setStatusMessage(null);
    const requestedMode = currentModeDefinition;
    const payload = { mode: requestedMode.backend, question: question.trim() };
    let envelope: AnswerEnvelope;
    let status: OpsHistoryEntry["status"] = "ok";
    let errorDetails: string | undefined;
    let trace: unknown;
    let nextActions: NextAction[] | undefined;
    try {
      if (requestedMode.id === "ci") {
        const response = await authenticatedFetch(`/ops/ci/ask`, {
          method: "POST",
          body: JSON.stringify({ question: question.trim() }),
        });
        const ciPayload = response.data;
        if (!ciPayload || !Array.isArray(ciPayload.blocks)) {
          throw new Error("Invalid CI response format");
        }
        const meta =
          ciPayload.meta ??
          ({
            route: "ci",
            route_reason: "CI tab",
            timing_ms: 0,
            summary: ciPayload.answer,
            used_tools: [],
          } as AnswerMeta);
        envelope = {
          meta,
          blocks: ciPayload.blocks,
        };
        trace = ciPayload.trace;
        nextActions = ciPayload.next_actions;
      } else {
        const data = await authenticatedFetch(`/ops/query`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        const answer = data.data?.answer as AnswerEnvelope | undefined;
        if (!answer || !Array.isArray(answer.blocks) || typeof answer.meta !== "object") {
          throw new Error("Invalid OPS response format");
        }
        envelope = answer;
      }
    } catch (rawError) {
      const normalized = await normalizeError(rawError);
      envelope = buildErrorEnvelope(currentModeDefinition.backend, normalized.message);
      status = "error";
      if (normalized.details) {
        errorDetails =
          typeof normalized.details === "string"
            ? normalized.details
            : JSON.stringify(normalized.details, null, 2);
      }
      setStatusMessage(`Error: ${normalized.message}`);
    } finally {
      const entry: OpsHistoryEntry = {
        id: genId(),
        createdAt: new Date().toISOString(),
        uiMode: requestedMode.id,
        backendMode: requestedMode.backend,
        question: question.trim(),
        response: envelope,
        status,
        summary: extractSummary(envelope, question.trim()),
        errorDetails,
        trace,
        nextActions,
      };
      pushHistoryEntry(entry);
      void persistHistoryEntry(entry);
      setQuestion("");
      setIsRunning(false);
      setIsFullScreen(false);
    }
  }, [currentModeDefinition, isRunning, question, pushHistoryEntry, persistHistoryEntry]);

  const handleNextAction = useCallback(
    async (action: NextAction) => {
      if (!selectedEntry) {
        return;
      }
      if (action.type === "open_trace") {
        setTraceOpen(true);
        return;
      }
      if (action.type === "copy_payload") {
        const payload =
          typeof action.payload === "string" ? action.payload : JSON.stringify(action.payload ?? {}, null, 2);
        try {
          await navigator.clipboard?.writeText(payload);
          setStatusMessage("Payload copied to clipboard");
        } catch {
          window.prompt("Copy payload", payload);
        }
        return;
      }
      if (action.type === "open_event_browser") {
        const params = new URLSearchParams();
        if (action.payload.exec_log_id) {
          params.set("exec_log_id", action.payload.exec_log_id);
        } else if (action.payload.simulation_id) {
          params.set("simulation_id", action.payload.simulation_id);
        }
        const query = params.toString();
        const url = `/cep-events${query ? `?${query}` : ""}`;
        window.open(url, "_blank");
        return;
      }
      if (action.type !== "rerun") {
        return;
      }
      const basePlan = selectedEntry.trace?.plan_validated;
      if (!basePlan) {
        setStatusMessage("Unable to rerun: missing plan snapshot");
        return;
      }
      setIsRunning(true);
      setStatusMessage(null);
      let envelope: AnswerEnvelope;
      let trace: unknown;
      let nextActions: NextAction[] | undefined;
      let status: OpsHistoryEntry["status"] = "ok";
      let errorDetails: string | undefined;
      try {
        const rerunBody: {
          question: string;
          rerun: {
            base_plan: unknown;
            selected_ci_id?: string;
            selected_secondary_ci_id?: string;
            patch?: unknown;
          };
        } = {
          question: selectedEntry.question,
          rerun: {
            base_plan: basePlan,
          },
        };
        if (action.payload?.selected_ci_id) {
          rerunBody.rerun.selected_ci_id = action.payload.selected_ci_id;
        }
        if (action.payload?.selected_secondary_ci_id) {
          rerunBody.rerun.selected_secondary_ci_id = action.payload.selected_secondary_ci_id;
        }
        if (action.payload?.patch) {
          rerunBody.rerun.patch = action.payload.patch;
        }
        const data = await authenticatedFetch(`/ops/ci/ask`, {
          method: "POST",
          body: JSON.stringify(rerunBody),
        });
        const ciPayload = data.data;
        if (!ciPayload || !Array.isArray(ciPayload.blocks)) {
          throw new Error("Invalid CI response format");
        }
        const meta =
          ciPayload.meta ??
          ({
            route: "ci",
            route_reason: "CI tab",
            timing_ms: 0,
            summary: ciPayload.answer,
            used_tools: [],
          } as AnswerMeta);
        envelope = {
          meta,
          blocks: ciPayload.blocks,
        };
        trace = ciPayload.trace;
        nextActions = ciPayload.next_actions;
      } catch (rawError) {
        const normalized = await normalizeError(rawError);
        envelope = buildErrorEnvelope(currentModeDefinition.backend, normalized.message);
        status = "error";
        if (normalized.details) {
          errorDetails =
            typeof normalized.details === "string"
              ? normalized.details
              : JSON.stringify(normalized.details, null, 2);
        }
        setStatusMessage(`Error: ${normalized.message}`);
      } finally {
        const entry: OpsHistoryEntry = {
          id: genId(),
          createdAt: new Date().toISOString(),
          uiMode: selectedEntry.uiMode ?? "ci",
          backendMode: selectedEntry.backendMode ?? "config",
          question: selectedEntry.question,
          response: envelope,
          status,
          summary: extractSummary(envelope, selectedEntry.question),
          errorDetails,
          trace,
          nextActions,
        };
        pushHistoryEntry(entry);
        setIsRunning(false);
        setTraceOpen(false);
      }
    },
    [currentModeDefinition.backend, pushHistoryEntry, selectedEntry]
  );

  const gridColsClass = isFullScreen
    ? "lg:grid-cols-[minmax(0,1fr)]"
    : "lg:grid-cols-[minmax(320px,360px)_minmax(0,1fr)]";
  const shouldShowSidebar = !isFullScreen;

  return (
    <div className="py-6">
      {/* OPS Summary Strip */}
      <div className="mb-6">
        <OpsSummaryStrip
          selectedEntry={selectedEntry}
          onUpdateData={() => {
            // Handle summary data updates if needed
          }}
        />
      </div>

      <div className={`grid gap-6 ${gridColsClass}`}>
        <div
          className={`h-[80vh] flex-col gap-4 ${shouldShowSidebar ? "flex" : "hidden"}`}
        >
          <div className="flex flex-1 flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 shadow-inner shadow-black/40">
            <div className="border-b border-slate-800 px-4 py-3">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Query history</p>
                {historyLoading ? (
                  <span className="text-xs text-slate-400">Loading…</span>
                ) : null}
              </div>
              <p className="text-[11px] text-slate-400">최근 실행한 OPS 질의를 선택해 결과를 확인합니다.</p>
              {historyError ? (
                <p className="mt-1 text-[11px] text-rose-400">{historyError}</p>
              ) : null}
            </div>
            <div className="flex-1 overflow-y-auto px-2 py-2 custom-scrollbar">
              {history.length === 0 ? (
                <p className="text-sm text-slate-500">질의를 실행하면 여기에 기록됩니다.</p>
              ) : (
                <div className="space-y-2">
                  {history.map((entry) => {
                    const isSelected = entry.id === selectedEntry?.id;
                    const label = UI_MODES.find((item) => item.id === entry.uiMode)?.label ?? entry.uiMode;
                    return (
                      <div
                        key={entry.id}
                        className={`group relative flex w-full flex-col rounded-2xl border px-3 py-2 text-left transition ${isSelected
                          ? "border-sky-500 bg-sky-500/10 text-white"
                          : "border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-600"
                          }`}
                      >
                        <button
                          onClick={() => setSelectedId(entry.id)}
                          className="text-left"
                        >
                          <div className="flex items-center justify-between pr-8 text-[11px] text-slate-400">
                            <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-200">
                              {label}
                            </span>
                            <span className="tracking-normal">{formatTimestamp(entry.createdAt)}</span>
                          </div>
                          <p
                            className="mt-2 text-sm font-semibold leading-snug text-white overflow-hidden"
                            style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}
                          >
                            {entry.question}
                          </p>
                          <p
                            className="text-[12px] text-slate-400 overflow-hidden"
                            style={{ display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical" }}
                          >
                            {entry.summary}
                          </p>
                        </button>
                        <button
                          onClick={(event) => {
                            event.stopPropagation();
                            event.preventDefault();
                            handleRemoveHistory(entry.id);
                          }}
                          className="absolute right-2 top-2 hidden h-6 w-6 items-center justify-center rounded-full border border-rose-400 bg-slate-900 text-[10px] text-rose-400 transition group-hover:flex"
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-[0.45] flex-col rounded-3xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="mb-3 space-y-1">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Run OPS query</p>
              <p className="text-[11px] text-slate-400">mode를 선택하고 질문을 작성한 뒤 실행하세요.</p>
            </div>
            <div className="flex gap-1 flex-nowrap">
              {UI_MODES.map((modeEntry) => (
                <button
                  key={modeEntry.id}
                  onClick={() => handleModeSelection(modeEntry.id)}
                  className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.3em] transition ${uiMode === modeEntry.id
                    ? "border-sky-500 bg-sky-500/10 text-white"
                    : "border-slate-800 bg-slate-950 text-slate-400 hover:border-slate-600"
                    }`}
                >
                  {modeEntry.label}
                </button>
              ))}
            </div>
            <label className="mt-4 text-[11px] uppercase tracking-[0.3em] text-slate-400">
              Question
              <textarea
                rows={4}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                className="mt-2 w-full resize-none rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none focus:border-sky-500 tracking-normal"
                placeholder="예: 최근 배포 중단 이유 알려줘"
              />
            </label>
            <div className="mt-4 flex flex-col gap-2">
              <button
                onClick={runQuery}
                className="rounded-2xl bg-emerald-500/80 px-4 py-2 text-sm font-semibold uppercase tracking-[0.3em] text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
                disabled={isRunning || !question.trim()}
              >
                {isRunning ? <span className="animate-pulse">Running…</span> : "메시지 전송"}
              </button>
              {statusMessage ? <p className="text-[11px] text-rose-300">{statusMessage}</p> : null}
            </div>
          </div>
        </div>
        <section
          className="flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 shadow-inner shadow-black/40"
          style={isFullScreen ? { gridColumn: "span 2" } : undefined}
        >
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">OPS answer</p>
              <h1 className="text-lg font-semibold text-white">
                {selectedLabel}
                {selectedEntry ? ` · ${formatTimestamp(selectedEntry.createdAt)}` : ""}
              </h1>
              {selectedEntry ? (
                <p className="text-[12px] text-slate-400">{selectedEntry.question}</p>
              ) : (
                <p className="text-[12px] text-slate-500">질의를 실행하면 결과가 여기 표시됩니다.</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {selectedEntry ? (
                <span
                  className={`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.3em] ${selectedEntry.status === "ok"
                    ? "border border-emerald-400 text-emerald-300"
                    : "border border-rose-400 text-rose-300"
                    }`}
                >
                  {selectedEntry.status.toUpperCase()}
                </span>
              ) : null}
              {canFullScreen ? (
                <button
                  onClick={() => setIsFullScreen((prev) => !prev)}
                  className="rounded-full border border-slate-700 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-500"
                >
                  {isFullScreen ? "Exit full screen" : "Full screen"}
                </button>
              ) : null}
            </div>
          </header>
          <details className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[12px] text-slate-300">
            <summary className="cursor-pointer text-[11px] uppercase tracking-[0.3em] text-slate-500">
              Meta · used tools · timing
            </summary>
            {meta ? (
              <div className="mt-2 space-y-1">
                <p>
                  Route: <span className="font-semibold text-white">{meta.route}</span>
                </p>
                <p className="text-[11px] text-slate-400">
                  Reason: {meta.route_reason}
                </p>
                <p className="text-[11px] text-slate-400">
                  Timing: {meta.timing_ms} ms · Used tools: {meta.used_tools.join(", ") || "N/A"}
                </p>
                <p className="text-[11px] text-slate-400">
                  Fallback: {meta.fallback ? "yes" : "no"}
                </p>
                {meta.error ? (
                  <p className="text-[11px] text-rose-300">Error: {meta.error}</p>
                ) : null}
                {selectedEntry.errorDetails ? (
                  <details className="mt-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-[11px] text-slate-300">
                    <summary className="cursor-pointer uppercase tracking-[0.3em] text-slate-400">
                      Details
                    </summary>
                    <pre className="mt-2 max-h-40 overflow-auto text-xs text-slate-300">
                      {selectedEntry.errorDetails}
                    </pre>
                  </details>
                ) : null}
              </div>
            ) : (
              <p className="mt-2 text-[11px] text-slate-400">No meta available.</p>
            )}
          </details>
          <details
            open={traceOpen}
            onToggle={(event) => setTraceOpen(event.currentTarget.open)}
            className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3 text-[12px] text-slate-300"
          >
            <summary className="flex items-center justify-between cursor-pointer text-[11px] uppercase tracking-[0.3em] text-slate-500">
              <span>Trace · plan / policy</span>
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  handleCopyTrace();
                }}
                disabled={!traceContents}
                className={`rounded-2xl border px-3 py-1 text-[10px] uppercase tracking-[0.3em] transition disabled:opacity-60 ${traceCopyVariantClasses}`}
              >
                {traceCopyLabel}
              </button>
            </summary>
            {traceData ? (
              <pre className="mt-2 max-h-64 overflow-auto rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-[11px] text-slate-100">
                {traceContents}
              </pre>
            ) : (
              <p className="mt-2 text-[11px] text-slate-400">No trace captured yet.</p>
            )}
          </details>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
            <span className="font-mono text-slate-200">
              Trace ID: {currentTraceId ?? "없음"}
            </span>
            {currentTraceId ? (
              <>
                <button
                  onClick={handleCopyResultTraceId}
                  className="px-3 py-1 rounded-lg border border-slate-700 text-[10px] uppercase tracking-[0.2em] transition hover:border-slate-500"
                >
                  Copy trace_id
                </button>
                <button
                  onClick={openInspectorTrace}
                  className="px-3 py-1 rounded-lg border border-slate-700 text-[10px] uppercase tracking-[0.2em] transition hover:border-slate-500"
                >
                  Open in Inspector
                </button>
              </>
            ) : null}
          </div>
          <div className="flex-1 overflow-y-auto">
            {selectedEntry && Array.isArray(selectedEntry.response?.blocks) ? (
              <BlockRenderer
                blocks={selectedEntry.response.blocks}
              nextActions={selectedEntry.nextActions}
              onAction={handleNextAction}
              traceId={selectedEntry.response.meta?.trace_id ?? undefined}
            />
            ) : (
              <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
                <p className="text-sm text-slate-500">Run a query to visualize OPS data.</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
