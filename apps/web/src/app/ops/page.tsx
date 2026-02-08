"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import BlockRenderer, {
  type AnswerBlock as RendererAnswerBlock,
  type AnswerMeta,
} from "../../components/answer/BlockRenderer";
import { type NextAction } from "./nextActions";
import { authenticatedFetch } from "@/lib/apiClient/index";
import { useAuth } from "@/contexts/AuthContext";
import {
  type ServerHistoryEntry,
  type CiAnswerPayload,
  type LocalOpsHistoryEntry,
  type AnswerEnvelope,
  type AnswerBlock as ApiAnswerBlock,
  type ResponseEnvelope,
  type StageInput,
  type StageOutput,
} from "@/lib/apiClientTypes";
import OpsSummaryStrip from "@/components/ops/OpsSummaryStrip";
import Toast from "@/components/admin/Toast";
import InspectorStagePipeline from "@/components/ops/InspectorStagePipeline";
import ReplanTimeline, { type ReplanEvent } from "@/components/ops/ReplanTimeline";
import { type OpsHistoryEntry } from "@/components/ops/types/opsTypes";
import {
  type BackendMode,
  type UiMode,
  formatTimestamp,
  normalizeAnswerMeta,
  buildStageSnapshots,
  parseReplanEvents,
  extractSummary,
  normalizeError,
  buildErrorEnvelope,
  normalizeHistoryResponse,
  hydrateServerEntry,
} from "./utils";

const UI_MODES: { id: UiMode; label: string; backend: BackendMode }[] = [
  { id: "all", label: "전체", backend: "all" },
  { id: "ci", label: "구성", backend: "config" },
  { id: "metric", label: "수치", backend: "metric" },
  { id: "history", label: "이력", backend: "hist" },
  { id: "relation", label: "연결", backend: "graph" },
  { id: "document", label: "문서", backend: "document" },
];

const MODE_STORAGE_KEY = "ops:mode:v2"; // v2: default changed to "all"
const HISTORY_LIMIT = 40;

export default function OpsPage() {
  const { isLoading: authLoading, user } = useAuth();
  const [history, setHistory] = useState<LocalOpsHistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [uiMode, setUiMode] = useState<UiMode>("all");  // Default mode is "전체" (all)
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

  const fetchHistory = useCallback(async () => {
     setHistoryLoading(true);
     setHistoryError(null);
     try {
       const payload = await authenticatedFetch<{ history: ServerHistoryEntry[] }>(`/history/?feature=ops&limit=${HISTORY_LIMIT}`);
       const rawHistory = (payload as { data?: { history: ServerHistoryEntry[] } })?.data?.history ?? [];
       const hydrated = rawHistory
         .map((entry: ServerHistoryEntry): LocalOpsHistoryEntry | null => hydrateServerEntry(entry))
         .filter((entry): entry is LocalOpsHistoryEntry => Boolean(entry));
       hydrated.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
       if (hydrated.length === 0) {
         setHistory([]);
         setSelectedId(null);
       } else {
         setHistory(hydrated);
         setSelectedId((prev) =>
           prev && hydrated.some((item: LocalOpsHistoryEntry) => item.id === prev) ? prev : hydrated[0].id
         );
       }
     } catch (error: unknown) {
       console.error("Failed to load OPS history", error);
       setHistoryError(error instanceof Error ? error.message : "Failed to load history");
     } finally {
       setHistoryLoading(false);
     }
   }, []);

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
    if (authLoading) {
      return;
    }
    fetchHistory();
  }, [authLoading, fetchHistory, user?.id]);

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
  const meta = ((selectedEntry?.response as any)?.data?.meta ?? null) as AnswerMeta | null;
  const traceData = selectedEntry?.trace as
    | {
      plan_validated?: unknown;
      policy_decisions?: Record<string, unknown>;
      [key: string]: unknown;
    }
    | undefined;
  const traceContents = useMemo(() => (traceData ? JSON.stringify(traceData, null, 2) : ""), [traceData]);
  const currentTraceId =
    typeof selectedEntry?.response?.meta?.trace_id === "string"
      ? selectedEntry.response.meta.trace_id
      : typeof selectedEntry?.trace?.trace_id === "string"
        ? selectedEntry.trace.trace_id
        : undefined;

  // Build stage snapshots from trace data
  const stageSnapshots = useMemo(() => {
  const stageInputs = (traceData as { stage_inputs?: StageInput[] })?.stage_inputs;
  const stageOutputs = (traceData as { stage_outputs?: StageOutput[] })?.stage_outputs;
  return buildStageSnapshots(stageInputs, stageOutputs);
}, [traceData]);

  // Build replan events from trace data
  const replanEvents = useMemo(() => {
    const events = (traceData as { replan_events?: ReplanEvent[] })?.replan_events;
    return parseReplanEvents(events);
  }, [traceData]);

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
    const fallbackTraceId =
      typeof history[0]?.response?.meta?.trace_id === "string"
        ? history[0].response.meta.trace_id
        : typeof history[0]?.trace?.trace_id === "string"
          ? history[0].trace.trace_id
          : undefined;
    const traceId = currentTraceId ?? fallbackTraceId;

    if (!traceId) {
      setStatusMessage("trace_id가 없습니다. 질의 응답에 trace_id가 포함되어 있는지 확인해주세요.");
      return;
    }

    // Navigate directly to inspector - it will handle missing traces gracefully
    router.push(`/admin/inspector?trace_id=${encodeURIComponent(traceId)}`);
  }, [currentTraceId, router, history]);

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
    let envelope: AnswerEnvelope = buildErrorEnvelope(requestedMode.backend, "No response");
    let status: LocalOpsHistoryEntry["status"] = "ok";
    let errorDetails: string | undefined;
    let trace: unknown;
    let nextActions: NextAction[] | undefined;
    try {
      if (requestedMode.id === "all") {
        // "all" mode uses /ops/ask endpoint for orchestration
        const response = await authenticatedFetch<ResponseEnvelope<CiAnswerPayload>>(`/ops/ask`, {
          method: "POST",
          body: JSON.stringify({ question: question.trim() }),
        });
        const ciPayload = response?.data;
        if (!ciPayload || !Array.isArray(ciPayload.blocks)) {
          throw new Error("Invalid all mode response format");
        }
        const meta = normalizeAnswerMeta(ciPayload.meta, ciPayload.answer);
        envelope = {
          meta: meta as unknown as AnswerEnvelope["meta"],
          blocks: ciPayload.blocks,
        };
        trace = ciPayload.trace;
        nextActions = ciPayload.next_actions ?? ciPayload.nextActions;
      } else {
        // All other modes (ci/config, metric, history, relation, document) use /ops/query
        const data = await authenticatedFetch<ResponseEnvelope<{ answer?: AnswerEnvelope; trace?: unknown }>>(`/ops/query`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        const payloadData = data?.data as
          | { answer?: AnswerEnvelope; trace?: unknown }
          | { data?: { answer?: AnswerEnvelope; trace?: unknown } }
          | undefined;
        const answerCandidate =
          (payloadData as { answer?: AnswerEnvelope })?.answer ??
          (payloadData as { data?: { answer?: AnswerEnvelope } })?.data?.answer ??
          (payloadData as { answer?: { answer?: AnswerEnvelope } })?.answer?.answer ??
          (payloadData as { answer?: { data?: { answer?: AnswerEnvelope } } })?.answer?.data?.answer;
        const normalizedAnswer = normalizeHistoryResponse({ data: { answer: answerCandidate } } as ServerHistoryEntry["response"]);
        if (normalizedAnswer && Array.isArray((normalizedAnswer as AnswerEnvelope).blocks)) {
          envelope = normalizedAnswer as AnswerEnvelope;
        } else {
          const rawAnswerText =
            typeof (answerCandidate as AnswerEnvelope | undefined)?.answer === "string"
              ? (answerCandidate as AnswerEnvelope).answer
              : typeof answerCandidate === "string"
                ? answerCandidate
                : undefined;
          if (rawAnswerText) {
            const meta = normalizeAnswerMeta((answerCandidate as AnswerEnvelope | undefined)?.meta, rawAnswerText);
            envelope = {
              meta: meta as unknown as AnswerEnvelope["meta"],
              blocks: [
                {
                  type: "markdown",
                  content: rawAnswerText,
                } as ApiAnswerBlock,
              ],
            };
          } else {
            throw new Error("Invalid OPS response format");
          }
        }
        trace =
          (payloadData as { trace?: unknown })?.trace ??
          (payloadData as { data?: { trace?: unknown } })?.data?.trace;
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
      // Refresh history from server (server writes final history entry)
      setSelectedId(null);
      await fetchHistory();
      setQuestion("");
      setIsRunning(false);
      setIsFullScreen(false);
    }
  }, [currentModeDefinition, isRunning, question, fetchHistory]);

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
      const basePlan = (selectedEntry.trace as { plan_validated?: unknown })?.plan_validated;
      if (!basePlan) {
        setStatusMessage("Unable to rerun: missing plan snapshot");
        return;
      }
      setIsRunning(true);
      setStatusMessage(null);
      let envelope: AnswerEnvelope = buildErrorEnvelope(selectedEntry.backendMode ?? "config", "No response");
      let trace: unknown;
      let nextActions: NextAction[] | undefined;
      let status: LocalOpsHistoryEntry["status"] = "ok";
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
        const data = await authenticatedFetch<ResponseEnvelope<CiAnswerPayload>>(`/ops/ci/ask`, {
          method: "POST",
          body: JSON.stringify(rerunBody),
        });
        const ciPayload = data?.data;
        if (!ciPayload || !Array.isArray(ciPayload.blocks)) {
          throw new Error("Invalid CI response format");
        }
        const meta = normalizeAnswerMeta(ciPayload.meta, ciPayload.answer);
        envelope = {
          meta: meta as unknown as AnswerEnvelope["meta"],
          blocks: ciPayload.blocks,
        };
        trace = ciPayload.trace;
        nextActions = ciPayload.next_actions ?? ciPayload.nextActions;
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
        // Server already persists history entries; refresh list only.
        setSelectedId(null);
        await fetchHistory();
        setIsRunning(false);
        setTraceOpen(false);
      }
    },
    [currentModeDefinition.backend, fetchHistory, selectedEntry]
  );

  const gridColsClass = isFullScreen
    ? "lg:grid-cols-[minmax(0,1fr)]"
    : "lg:grid-cols-[minmax(320px,360px)_minmax(0,1fr)]";
  const shouldShowSidebar = !isFullScreen;

  return (
    <>
    <div className="py-6">
      {/* OPS Summary Strip */}
      <div className="mb-6">
        <OpsSummaryStrip
          selectedEntry={selectedEntry as OpsHistoryEntry | null}
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
                          {entry.trace?.trace_id && (
                            <p className="mt-1 text-[10px] text-slate-500 font-mono overflow-hidden"
                              style={{ display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical" }}
                            >
                              Trace: {entry.trace.trace_id}
                            </p>
                          )}
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
              {statusMessage ? null : null}
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
                  Timing: {meta.timing_ms} ms · Used tools: {meta.used_tools?.join(", ") || "N/A"}
                </p>
                <p className="text-[11px] text-slate-400">
                  Fallback: {meta.fallback ? "yes" : "no"}
                </p>
                {meta.error ? (
                  <p className="text-[11px] text-rose-300">Error: {String(meta.error)}</p>
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
          {/* Stage Pipeline Inspector */}
          {stageSnapshots.length > 0 && (
            <InspectorStagePipeline
              stages={stageSnapshots}
              traceId={currentTraceId}
              className="rounded-2xl"
            />
          )}

          {/* Replan Timeline */}
          {replanEvents.length > 0 && (
            <ReplanTimeline
              events={replanEvents}
              traceId={currentTraceId}
              className="rounded-2xl max-h-96"
            />
          )}

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
                blocks={selectedEntry.response.blocks as RendererAnswerBlock[]}
                nextActions={selectedEntry.nextActions}
                onAction={handleNextAction}
                traceId={currentTraceId}
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

    <Toast
      message={statusMessage ?? ""}
      type={statusMessage?.includes("trace_id가 없습니다") ? "warning" : statusMessage?.includes("찾을 수 없습니다") ? "error" : "info"}
      onDismiss={() => setStatusMessage(null)}
      duration={3000}
    />
    </>
  );
 }
