"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PageHeader } from "@/components/shared";
import { cn } from "@/lib/utils";
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
import ConversationSummaryModal from "@/components/ops/ConversationSummaryModal";
import InspectorStagePipeline from "@/components/ops/InspectorStagePipeline";
import ReplanTimeline, { type ReplanEvent } from "@/components/ops/ReplanTimeline";
import { PdfViewerModal } from "@/components/pdf/PdfViewerModal";
import { type OpsHistoryEntry } from "@/components/ops/types/opsTypes";
import {
  type BackendMode,
  type UiMode,
  formatTimestamp,
  normalizeAnswerMeta,
  buildStageSnapshots,
  parseReplanEvents,
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
  const [uiMode, setUiMode] = useState<UiMode>("all"); // Default mode is "전체" (all)
  const [question, setQuestion] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [traceCopyStatus, setTraceCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [summaryModalOpen, setSummaryModalOpen] = useState(false);
  const [summaryData, setSummaryData] = useState<Record<string, unknown> | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [summaryType, setSummaryType] = useState<"individual" | "overall">("individual");

  // PDF viewer modal state
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("document.pdf");

  // Resizable panel state (left sidebar)
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(340);
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle left sidebar resize
  useEffect(() => {
    if (!isResizingLeft) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      setLeftSidebarWidth(Math.max(250, Math.min(600, e.clientX - rect.left)));
    };

    const handleMouseUp = () => {
      setIsResizingLeft(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizingLeft]);

  const router = useRouter();

  const currentModeDefinition = UI_MODES.find((item) => item.id === uiMode) ?? UI_MODES[0];

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const payload = await authenticatedFetch<{ history: ServerHistoryEntry[] }>(
        `/history/?feature=ops&limit=${HISTORY_LIMIT}`,
      );
      const rawHistory =
        (payload as { data?: { history: ServerHistoryEntry[] } })?.data?.history ?? [];
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
          prev && hydrated.some((item: LocalOpsHistoryEntry) => item.id === prev)
            ? prev
            : hydrated[0].id,
        );
      }
    } catch (error: unknown) {
      console.error("Failed to load OPS history", error);
      setHistoryError(error instanceof Error ? error.message : "Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const deleteHistoryEntry = useCallback(async (id: string) => {
    try {
      await authenticatedFetch(`/history/${id}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error("Failed to delete OPS history entry", error);
    }
  }, []);

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
  const meta = ((selectedEntry?.response as Record<string, unknown>)?.data as Record<string, unknown>)?.meta as AnswerMeta | null ?? null;
  const traceData = selectedEntry?.trace as
    | {
        plan_validated?: unknown;
        policy_decisions?: Record<string, unknown>;
        [key: string]: unknown;
      }
    | undefined;
  const traceContents = useMemo(
    () => (traceData ? JSON.stringify(traceData, null, 2) : ""),
    [traceData],
  );
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
        : "border-variant text-muted-foreground dark:border-variant dark:text-muted-foreground hover:border-variant hover:text-white dark:hover:border-variant";

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
    [selectedId, deleteHistoryEntry],
  );

  const selectedLabel =
    UI_MODES.find((entry) => entry.id === (selectedEntry?.uiMode ?? uiMode))?.label ??
    currentModeDefinition.label;

  const canFullScreen = selectedEntry?.backendMode === "graph" || meta?.route === "graph";

  const runQuery = useCallback(async () => {
    if (!question.trim() || isRunning) {
      return;
    }
    setIsRunning(true);
    setStatusMessage(null);
    const requestedMode = currentModeDefinition;
    const payload = { mode: requestedMode.backend, question: question.trim() };
    let envelope: AnswerEnvelope = buildErrorEnvelope(requestedMode.backend, "No response");
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
      } else {
        // All other modes (ci/config, metric, history, relation, document) use /ops/query
        const data = await authenticatedFetch<
          ResponseEnvelope<{ answer?: AnswerEnvelope; trace?: unknown }>
        >(`/ops/query`, {
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
          (payloadData as { answer?: { data?: { answer?: AnswerEnvelope } } })?.answer?.data
            ?.answer;
        const normalizedAnswer = normalizeHistoryResponse({
          data: { answer: answerCandidate },
        } as ServerHistoryEntry["response"]);
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
            const meta = normalizeAnswerMeta(
              (answerCandidate as AnswerEnvelope | undefined)?.meta,
              rawAnswerText,
            );
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
      }
    } catch (rawError) {
      const normalized = await normalizeError(rawError);
      envelope = buildErrorEnvelope(currentModeDefinition.backend, normalized.message);
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

  // Fetch conversation summary for modal preview
  const fetchConversationSummary = useCallback(async () => {
    if (!history.length) {
      setStatusMessage("대화 내용이 없습니다.");
      return;
    }

    setSummaryLoading(true);
    try {
      // Use the first (latest) entry's thread_id to get the full conversation
      const latestEntry = history[0];
      const threadId = latestEntry.thread_id;
      const historyId = latestEntry.id;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const response = await authenticatedFetch<any>("/ops/conversation/summary", {
        method: "POST",
        body: JSON.stringify({
          ...(threadId ? { thread_id: threadId } : {}),
          ...(threadId ? {} : { history_id: historyId }),
          title: latestEntry.question.substring(0, 50),
          topic: "OPS 분석",
          summary_type: summaryType, // "individual" or "overall"
        }),
      });

      if (response?.data) {
        setSummaryData(response.data);
        setSummaryModalOpen(true);
      }
    } catch (error) {
      console.error("Failed to fetch conversation summary:", error);
      setStatusMessage("요약을 가져오지 못했습니다.");
    } finally {
      setSummaryLoading(false);
    }
  }, [history, summaryType]);

  // Export conversation as PDF
  const exportConversationPdf = useCallback(async () => {
    if (!history.length) {
      setStatusMessage("대화 내용이 없습니다.");
      return;
    }

    setPdfExporting(true);
    try {
      const latestEntry = history[0];
      const threadId = latestEntry.thread_id;
      const historyId = latestEntry.id;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const response = await authenticatedFetch<any>("/ops/conversation/export/pdf", {
        method: "POST",
        body: JSON.stringify({
          ...(threadId ? { thread_id: threadId } : {}),
          ...(threadId ? {} : { history_id: historyId }),
          title: latestEntry.question.substring(0, 40),
          topic: "OPS 분석",
          summary_type: summaryType, // "individual" or "overall"
        }),
      });

      if (response?.data) {
        const { filename, content, content_type } = response.data;

        // Decode base64 content
        const binaryString = atob(content);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }

        // Create blob and show in viewer modal
        const blob = new Blob([bytes], { type: content_type });
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
        setPdfFilename(filename);
        setPdfViewerOpen(true);
      }
    } catch (error) {
      console.error("Failed to export PDF:", error);
      setStatusMessage("PDF 생성에 실패했습니다.");
    } finally {
      setPdfExporting(false);
    }
  }, [history, summaryType]);

  // Cleanup PDF blob URL when modal closes
  const handleClosePdfViewer = useCallback(() => {
    if (pdfBlobUrl) {
      URL.revokeObjectURL(pdfBlobUrl);
    }
    setPdfViewerOpen(false);
    setPdfBlobUrl(null);
  }, [pdfBlobUrl]);

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
          typeof action.payload === "string"
            ? action.payload
            : JSON.stringify(action.payload ?? {}, null, 2);
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
      let envelope: AnswerEnvelope = buildErrorEnvelope(
        selectedEntry.backendMode ?? "config",
        "No response",
      );
      let nextActions: NextAction[] | undefined;
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
        const data = await authenticatedFetch<ResponseEnvelope<CiAnswerPayload>>(`/ops/ask`, {
          method: "POST",
          body: JSON.stringify(rerunBody),
        });
        const ciPayload = data?.data;
        if (!ciPayload || !Array.isArray(ciPayload.blocks)) {
          throw new Error("Invalid CI response format");
        }
        const meta = normalizeAnswerMeta(ciPayload.meta, ciPayload.answer);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        envelope = {
          meta: meta as unknown as AnswerEnvelope["meta"],
          blocks: ciPayload.blocks,
        };
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        nextActions = ciPayload.next_actions ?? ciPayload.nextActions;
      } catch (rawError) {
        const normalized = await normalizeError(rawError);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        envelope = buildErrorEnvelope(currentModeDefinition.backend, normalized.message);
        setStatusMessage(`Error: ${normalized.message}`);
      } finally {
        // Server already persists history entries; refresh list only.
        setSelectedId(null);
        await fetchHistory();
        setIsRunning(false);
        setTraceOpen(false);
      }
    },
    [currentModeDefinition.backend, fetchHistory, selectedEntry],
  );

  const shouldShowSidebar = !isFullScreen;

  return (
    <div
      ref={containerRef}
      className="ops-theme"
      style={{userSelect: isResizingLeft ? "none" : "auto"}}
    >
      {/* Page Header - Standard */}
      <PageHeader
        title="Operations"
        description="OPS Query System을 통해 데이터를 조회하고 분석합니다. 질문과 답변 내용을 추적하고 관리합니다."
      />

      <main className="min-h-[calc(100vh-96px)] py-6">
        {/* Summary Modal */}
        {summaryModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm bg-black/60">
            <div className="relative w-full max-w-2xl rounded-3xl border p-6 border bg-surface-base">
              {/* Header */}
              <div className="flex items-center justify-between border-b p-6 border-border">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">📋</span>
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">대화 요약</h2>
                    <p className="text-xs text-muted-standard">
                      {summaryData?.question_count || history.length}개의 질문
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setSummaryModalOpen(false)}
                  className="rounded-full border px-3 py-1 text-sm transition hover:bg-surface-elevated border text-muted-standard"
                >
                  ✕
                </button>
              </div>

              {/* Content */}
              <div className="max-h-[60vh] overflow-y-auto px-6 py-4 custom-scrollbar">
                {/* Summary Type Selector */}
                <div className="mb-4 flex items-center justify-between rounded-xl border p-3 border bg-surface-elevated">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-foreground">요약 방식:</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setSummaryType("individual");
                          setTimeout(() => fetchConversationSummary(), 100);
                        }}
                        className={cn(
                          "rounded-lg px-3 py-1 text-xs font-medium transition border",
                          summaryType === "individual"
                            ? "bg-sky-500/20 border-sky-500 text-sky-300"
                            : "border text-foreground",
                        )}
                      >
                        개별 요약
                      </button>
                      <button
                        onClick={() => {
                          setSummaryType("overall");
                          setTimeout(() => fetchConversationSummary(), 100);
                        }}
                        className={cn(
                          "rounded-lg px-3 py-1 text-xs font-medium transition border",
                          summaryType === "overall"
                            ? "bg-sky-500/20 border-sky-500 text-sky-300"
                            : "border text-foreground",
                        )}
                      >
                        전체 요약
                      </button>
                    </div>
                  </div>
                  {summaryData?.summary_type && (
                    <span className="text-xs text-muted-standard">
                      {summaryData.summary_type === "individual" ? "개별" : "전체"}
                    </span>
                  )}
                </div>

                {summaryLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <span className="animate-spin text-2xl">⏳</span>
                  </div>
                ) : summaryData ? (
                  <>
                    {/* Overall Summary Section (if available) */}
                    {summaryData.overall_summary && (
                      <div className="mb-4 br-card border p-4 bg-sky-950/30">
                        <h3 className="mb-2 text-sm font-semibold text-sky-300">📝 전체 요약</h3>
                        <pre className="whitespace-pre-wrap text-xs font-sans text-muted-foreground">
                          {summaryData.overall_summary}
                        </pre>
                      </div>
                    )}

                    {/* Metadata */}
                    <div className="mb-4 container-section">
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-xs text-muted-standard">제목</span>
                          <p className="font-semibold text-foreground">{summaryData.title}</p>
                        </div>
                        <div>
                          <span className="text-xs text-muted-standard">일자</span>
                          <p className="text-muted-standard">{summaryData.date}</p>
                        </div>
                        <div className="col-span-2">
                          <span className="text-xs text-muted-standard">주제</span>
                          <p className="text-muted-standard">{summaryData.topic}</p>
                        </div>
                      </div>
                    </div>

                    {/* Q&A Summary */}
                    <div className="space-y-4">
                      <h3 className="text-sm font-semibold text-muted-standard">질의-응답 요약</h3>
                      {summaryData.questions_and_answers
                        ?.slice(0, 5)
                        .map((qa: any, idx: number) => (
                          <div key={idx} className="br-card border p-3 bg-surface-elevated">
                            <div className="mb-2 flex items-center gap-2">
                              <span className="rounded-full bg-sky-500/20 px-2 py-0.5 text-xs font-semibold uppercase text-sky-300">
                                Q{idx + 1}
                              </span>
                              {qa.mode && (
                                <span className="rounded-full border px-2 py-0.5 text-xs border text-muted-standard">
                                  {qa.mode}
                                </span>
                              )}
                            </div>
                            <p className="mb-2 text-sm font-medium text-foreground">
                              {qa.question}
                            </p>
                            {qa.summary && (
                              <p className="text-xs line-clamp-3 text-muted-standard">
                                {qa.summary}
                              </p>
                            )}
                          </div>
                        ))}
                      {summaryData.questions_and_answers?.length > 5 && (
                        <p className="text-center text-xs text-muted-standard">
                          ... 그 외 {summaryData.questions_and_answers.length - 5}개의 질문
                        </p>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="py-12 text-center text-muted-standard">
                    요약 데이터가 없습니다.
                  </div>
                )}
              </div>

              {/* Footer - PDF Export */}
              <div className="flex justify-end border-t px-6 py-4 border-border">
                <button
                  onClick={exportConversationPdf}
                  disabled={pdfExporting || summaryLoading}
                  className="btn-primary flex items-center gap-2"
                >
                  {pdfExporting ? (
                    <>
                      <span className="animate-spin">⏳</span>
                      <span>생성 중...</span>
                    </>
                  ) : (
                    <>
                      <span>📄</span>
                      <span>PDF 리포트 내보내기</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="pb-6">
          {/* OPS Summary Strip + Summary Button */}
          <div className="mb-6 flex items-center justify-between">
            <div className="flex-1">
              <OpsSummaryStrip
                selectedEntry={selectedEntry as OpsHistoryEntry | null}
                onUpdateData={() => {
                  // Handle summary data updates if needed
                }}
              />
            </div>
            {/* Summary Icon Button */}
            <button
              onClick={() => {
                setSummaryModalOpen(true);
                if (!summaryData && history.length > 0) {
                  fetchConversationSummary();
                }
              }}
              disabled={!selectedEntry}
              className="ml-4 flex h-12 w-12 items-center justify-center rounded-full border shadow-lg transition hover:border-primary disabled:cursor-not-allowed disabled:opacity-50 bg-surface-elevated text-muted-standard dark:border-border"
              title="대화 요약 보기"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </button>
          </div>

          <div className="flex gap-0">
            <div
              className={`h-[80vh] flex-col gap-3 ${shouldShowSidebar ? "flex" : "hidden"} flex-shrink-0`}
              style={{width: shouldShowSidebar ? `${leftSidebarWidth}px` : "0"}}
            >
              <div className="flex flex-1 flex-col overflow-hidden rounded-3xl border bg-surface-base shadow-inner shadow-black/40 dark:border-border">
                <div className="border-b px-3 py-2 border-border">
                  <div className="flex items-center justify-between">
                    <p className="left-panel-title">Query history</p>
                    {historyLoading ? (
                      <span className="text-xs text-muted-standard">Loading…</span>
                    ) : null}
                  </div>
                  <p className="text-xs text-muted-standard">
                    최근 실행한 OPS 질의를 선택해 결과를 확인합니다.
                  </p>
                  {historyError ? (
                    <p className="mt-1 text-xs text-rose-400">{historyError}</p>
                  ) : null}
                </div>
                <div className="flex-1 overflow-y-auto px-2 py-1 custom-scrollbar">
                  {history.length === 0 ? (
                    <p className="text-sm text-muted-standard">
                      질의를 실행하면 여기에 기록됩니다.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {history.map((entry) => {
                        const isSelected = entry.id === selectedEntry?.id;
                        const label =
                          UI_MODES.find((item) => item.id === entry.uiMode)?.label ?? entry.uiMode;
                        return (
                          <div
                            key={entry.id}
                            className={cn(
                              "group relative flex w-full flex-col rounded-2xl border px-3 py-2 transition",
                              isSelected
                                ? "bg-surface-elevated border-sky-500 dark:bg-surface-elevated dark:border-sky-500"
                                : "border-transparent hover:bg-surface-elevated dark:hover:bg-surface-elevated hover:border-border dark:hover:border-variant",
                            )}
                          >
                            <button onClick={() => setSelectedId(entry.id)} className="text-left">
                              <div className="flex items-center justify-between pr-8 text-muted-standard">
                                <span className="rounded-full border px-2 py-0.5 text-xs font-semibold uppercase tracking-wider bg-surface-base text-foreground dark:bg-surface-elevated dark:text-slate-50">
                                  {label}
                                </span>
                                <span className="tracking-normal">
                                  {formatTimestamp(entry.createdAt)}
                                </span>
                              </div>
                              <p className="mt-2 text-sm font-semibold leading-snug line-clamp-2 text-foreground">
                                {entry.question}
                              </p>
                              <p className="text-sm line-clamp-1 text-muted-standard">
                                {entry.summary}
                              </p>
                              {entry.trace?.trace_id && (
                                <p className="mt-1 text-xs font-mono line-clamp-1 text-muted-standard">
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
                              className="absolute right-2 top-2 hidden h-6 w-6 items-center justify-center rounded-full border border-rose-400 bg-surface-base text-xs text-rose-400 transition group-hover:flex dark:bg-surface-base"
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
              <div className="flex flex-[0.45] flex-col rounded-3xl border p-3 bg-surface-base dark:border-border">
                <div className="mb-2 space-y-0.5">
                  <p className="left-panel-title">Run OPS query</p>
                  <p className="text-xs text-muted-standard">
                    mode를 선택하고 질문을 작성한 뒤 실행하세요.
                  </p>
                </div>
                <div className="mt-2 flex gap-1 flex-nowrap">
                  {UI_MODES.map((modeEntry) => (
                    <button
                      key={modeEntry.id}
                      onClick={() => handleModeSelection(modeEntry.id)}
                      className={cn(
                        "rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition hover:bg-surface-elevated dark:hover:bg-surface-elevated",
                        uiMode === modeEntry.id
                          ? "bg-primary border-primary text-white hover:bg-sky-500 dark:hover:bg-sky-600"
                          : "border text-foreground dark:border-border",
                      )}
                    >
                      {modeEntry.label}
                    </button>
                  ))}
                </div>
                <label className="mt-3 text-sm uppercase tracking-wider text-muted-standard">
                  Question
                  <textarea
                    rows={4}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    className="mt-2 w-full resize-none rounded-2xl border px-3 py-2 text-sm outline-none focus:border-primary tracking-normal input-container"
                    placeholder="예: 최근 배포 중단 이유 알려줘"
                  />
                </label>
                <div className="mt-3 flex flex-col gap-2">
                  <button
                    onClick={runQuery}
                    className="btn-primary"
                    disabled={isRunning || !question.trim()}
                  >
                    {isRunning ? <span className="animate-pulse">Running…</span> : "메시지 전송"}
                  </button>
                  {statusMessage ? null : null}
                </div>
              </div>
            </div>

            {/* Left Resize Handle */}
            {shouldShowSidebar && (
              <div
                onMouseDown={(event) => {
                  event.preventDefault();
                  setIsResizingLeft(true);
                }}
                className={cn("resize-handle-col", isResizingLeft && "is-active")}
                aria-label="Resize left panel"
                role="separator"
                aria-orientation="vertical"
              >
                <div className="resize-handle-grip" />
              </div>
            )}

            <section
              className="flex flex-col gap-3 rounded-3xl border p-3 shadow-inner shadow-black/40 bg-surface-base dark:border-border flex-1"
            >
              <header className="page-header">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="page-header-content">
                    <p className="text-xs uppercase tracking-wider text-muted-standard">
                      OPS answer
                    </p>
                    <h1 className="page-header-title">
                      {selectedLabel}
                      {selectedEntry ? ` · ${formatTimestamp(selectedEntry.createdAt)}` : ""}
                    </h1>
                    {selectedEntry ? (
                      <p className="page-header-description">{selectedEntry.question}</p>
                    ) : (
                      <p className="page-header-description">
                        질의를 실행하면 결과가 여기 표시됩니다.
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedEntry ? (
                      <span
                        className={`rounded-full px-3 py-1 text-xs uppercase tracking-wider ${
                          selectedEntry.status === "ok"
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
                        className="br-badge border px-3 py-1 text-xs uppercase tracking-wider transition hover:bg-surface-elevated dark:hover:bg-surface-elevated border text-muted-standard dark:border-border"
                      >
                        {isFullScreen ? "Exit full screen" : "Full screen"}
                      </button>
                    ) : null}
                  </div>
                </div>
              </header>
              <details className="rounded-2xl border p-3 text-sm bg-surface-elevated dark:border-border">
                <summary className="cursor-pointer text-sm uppercase tracking-wider text-muted-standard">
                  Meta · used tools · timing
                </summary>
                {meta ? (
                  <div className="mt-2 space-y-1">
                    <p>
                      Route: <span className="font-semibold text-foreground">{meta.route}</span>
                    </p>
                    <p className="text-sm text-muted-standard">Reason: {meta.route_reason}</p>
                    <p className="text-sm text-muted-standard">
                      Timing: {meta.timing_ms} ms · Used tools:{" "}
                      {meta.used_tools?.join(", ") || "N/A"}
                    </p>
                    <p className="text-sm text-muted-standard">
                      Fallback: {meta.fallback ? "yes" : "no"}
                    </p>
                    {meta.error ? (
                      <p className="text-sm text-rose-300">Error: {String(meta.error)}</p>
                    ) : null}
                    {selectedEntry.errorDetails ? (
                      <details className="mt-2 rounded-2xl border p-3 text-sm bg-surface-base dark:bg-surface-base border-border">
                        <summary className="cursor-pointer uppercase tracking-wider text-muted-standard">
                          Details
                        </summary>
                        <pre className="mt-2 max-h-40 overflow-auto text-xs text-muted-standard">
                          {selectedEntry.errorDetails}
                        </pre>
                      </details>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-muted-standard">No meta available.</p>
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
                className="rounded-2xl border p-3 text-sm bg-surface-elevated dark:border-border"
              >
                <summary className="flex items-center justify-between cursor-pointer text-sm uppercase tracking-wider text-muted-standard">
                  <span>Trace · plan / policy</span>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      handleCopyTrace();
                    }}
                    disabled={!traceContents}
                    className={`rounded-2xl border px-3 py-1 text-xs uppercase tracking-wider transition disabled:opacity-60 ${traceCopyVariantClasses}`}
                  >
                    {traceCopyLabel}
                  </button>
                </summary>
                {traceData ? (
                  <pre className="mt-2 max-h-64 overflow-auto rounded-2xl border p-3 text-sm bg-surface-base">
                    {traceContents}
                  </pre>
                ) : (
                  <p className="mt-2 text-sm text-muted-standard">No trace captured yet.</p>
                )}
              </details>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-standard">
                <span className="font-mono text-muted-standard">
                  Trace ID: {currentTraceId ?? "없음"}
                </span>
                {currentTraceId ? (
                  <>
                    <button
                      onClick={handleCopyResultTraceId}
                      className="px-3 py-1 rounded-lg border text-xs uppercase tracking-wider transition hover:bg-surface-elevated dark:hover:bg-surface-elevated border text-muted-standard dark:border-border"
                    >
                      Copy trace_id
                    </button>
                    <button
                      onClick={openInspectorTrace}
                      className="px-3 py-1 rounded-lg border text-xs uppercase tracking-wider transition hover:bg-surface-elevated dark:hover:bg-surface-elevated border text-muted-standard dark:border-border"
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
                  <div className="rounded-3xl border p-6 bg-surface-elevated dark:border-border">
                    <p className="text-sm text-muted-standard">
                      Run a query to visualize OPS data.
                    </p>
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </main>

      <Toast
        message={statusMessage ?? ""}
        type={
          statusMessage?.includes("trace_id가 없습니다")
            ? "warning"
            : statusMessage?.includes("찾을 수 없습니다")
              ? "error"
              : "info"
        }
        onDismiss={() => setStatusMessage(null)}
        duration={3000}
      />

      <ConversationSummaryModal
        isOpen={summaryModalOpen}
        onClose={() => setSummaryModalOpen(false)}
        threadId={selectedEntry?.thread_id ?? null}
        historyId={selectedEntry?.id ?? null}
      />

      <PdfViewerModal
        isOpen={pdfViewerOpen}
        onClose={handleClosePdfViewer}
        pdfBlobUrl={pdfBlobUrl}
        filename={pdfFilename}
      />
    </div>
  );
}
