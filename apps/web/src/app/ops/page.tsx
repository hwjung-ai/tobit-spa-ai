"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import BlockRenderer, { type AnswerEnvelope } from "../../components/answer/BlockRenderer";

type BackendMode = "all" | "metric" | "hist" | "graph";
type UiMode = "ci" | "metric" | "history" | "relation" | "all";

const UI_MODES: { id: UiMode; label: string; backend: BackendMode }[] = [
  { id: "ci", label: "CI", backend: "all" },
  { id: "metric", label: "Metric", backend: "metric" },
  { id: "history", label: "History", backend: "hist" },
  { id: "relation", label: "Relation", backend: "graph" },
  { id: "all", label: "ALL", backend: "all" },
];

const HISTORY_STORAGE_KEY = "ops:history:v1";
const MODE_STORAGE_KEY = "ops:mode";
const HISTORY_LIMIT = 40;

const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

interface OpsHistoryEntry {
  id: string;
  createdAt: string;
  uiMode: UiMode;
  backendMode: BackendMode;
  question: string;
  response: AnswerEnvelope;
  status: "ok" | "error";
  summary: string;
  errorDetails?: string;
}

const formatTimestamp = (value: string) => {
  try {
    return new Date(value).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

const extractSummary = (envelope: AnswerEnvelope | null, question: string) => {
  if (!envelope) {
    return question || "(no summary)";
  }
  if (envelope.meta?.summary) {
    return envelope.meta.summary;
  }
  const markdown = envelope.blocks?.find((block) => block.type === "markdown");
  if (markdown && "content" in markdown && markdown.content) {
    return markdown.content.split("\n")[0];
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

export default function OpsPage() {
  const [history, setHistory] = useState<OpsHistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [uiMode, setUiMode] = useState<UiMode>("all");
  const [question, setQuestion] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isFullScreen, setIsFullScreen] = useState(false);

  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const currentModeDefinition = UI_MODES.find((item) => item.id === uiMode) ?? UI_MODES[0];

  useEffect(() => {
    const rawHistory = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (rawHistory) {
      try {
        const parsed: OpsHistoryEntry[] = JSON.parse(rawHistory);
        if (parsed.length > 0) {
          setHistory(parsed);
          setSelectedId(parsed[0].id);
        }
      } catch {
        window.localStorage.removeItem(HISTORY_STORAGE_KEY);
      }
    }
    const savedMode = window.localStorage.getItem(MODE_STORAGE_KEY) as UiMode | null;
    if (savedMode && UI_MODES.some((item) => item.id === savedMode)) {
      setUiMode(savedMode);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    window.localStorage.setItem(MODE_STORAGE_KEY, uiMode);
  }, [uiMode]);

  const selectedEntry = useMemo(() => {
    return history.find((entry) => entry.id === selectedId) ?? history[0] ?? null;
  }, [history, selectedId]);

  const handleModeSelection = useCallback((modeId: UiMode) => {
    setUiMode(modeId);
    setIsFullScreen(false);
  }, []);

  const selectedLabel =
    UI_MODES.find((entry) => entry.id === (selectedEntry?.uiMode ?? uiMode))?.label ?? currentModeDefinition.label;

  const canFullScreen =
    selectedEntry?.backendMode === "graph" || selectedEntry?.response.meta?.route === "graph";

  const runQuery = useCallback(async () => {
    if (!question.trim() || isRunning) {
      return;
    }
    setIsRunning(true);
    setStatusMessage(null);
    const payload = { mode: currentModeDefinition.backend, question: question.trim() };
    let envelope: AnswerEnvelope;
    let status: OpsHistoryEntry["status"] = "ok";
    let errorDetails: string | undefined;
    try {
      const response = await fetch(`${apiBaseUrl}/ops/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      console.debug("OPS response", { payload, data });
      if (!response.ok) {
        throw response;
      }
      const answer = data.data?.answer as AnswerEnvelope | undefined;
      if (!answer || !Array.isArray(answer.blocks) || typeof answer.meta !== "object") {
        throw new Error("Invalid OPS response format");
      }
      envelope = answer;
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
      console.debug("OPS query error details", normalized.details ?? normalized);
    } finally {
      const entry: OpsHistoryEntry = {
        id: genId(),
        createdAt: new Date().toISOString(),
        uiMode,
        backendMode: currentModeDefinition.backend,
        question: question.trim(),
        response: envelope,
        status,
        summary: extractSummary(envelope, question.trim()),
        errorDetails,
      };
      setHistory((prev) => {
        const next = [entry, ...prev];
        if (next.length > HISTORY_LIMIT) {
          return next.slice(0, HISTORY_LIMIT);
        }
        return next;
      });
      setSelectedId(entry.id);
      setQuestion("");
      setIsRunning(false);
      setIsFullScreen(false);
    }
  }, [apiBaseUrl, currentModeDefinition.backend, isRunning, question, uiMode]);

  const gridColsClass = isFullScreen
    ? "lg:grid-cols-[minmax(0,1fr)]"
    : "lg:grid-cols-[minmax(320px,360px)_minmax(0,1fr)]";
  const shouldShowSidebar = !isFullScreen;

  return (
    <div className="py-6">
      <div className={`grid gap-6 ${gridColsClass}`}>
        <div
          className={`h-[80vh] flex-col gap-4 ${shouldShowSidebar ? "flex" : "hidden"}`}
        >
          <div className="flex flex-1 flex-col overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/70 shadow-inner shadow-black/40">
            <div className="border-b border-slate-800 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Query history</p>
              <p className="text-[11px] text-slate-400">최근 실행한 OPS 질의를 선택해 결과를 확인합니다.</p>
            </div>
            <div className="flex-1 overflow-y-auto px-2 py-2">
              {history.length === 0 ? (
                <p className="text-sm text-slate-500">질의를 실행하면 여기에 기록됩니다.</p>
              ) : (
                <div className="space-y-2">
                  {history.map((entry) => {
                    const isSelected = entry.id === selectedEntry?.id;
                    const label = UI_MODES.find((item) => item.id === entry.uiMode)?.label ?? entry.uiMode;
                    return (
                      <button
                        key={entry.id}
                        onClick={() => setSelectedId(entry.id)}
                        className={`group flex w-full flex-col rounded-2xl border px-3 py-2 text-left transition ${
                          isSelected
                            ? "border-sky-500 bg-sky-500/10 text-white"
                            : "border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-600"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.3em] text-slate-400">
                          <span className="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-200">
                            {label}
                          </span>
                          <span>{formatTimestamp(entry.createdAt)}</span>
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
            <div className="flex flex-wrap gap-2">
              {UI_MODES.map((modeEntry) => (
                <button
                  key={modeEntry.id}
                  onClick={() => handleModeSelection(modeEntry.id)}
                  className={`rounded-full border px-4 py-2 text-[11px] uppercase tracking-[0.3em] transition ${
                    uiMode === modeEntry.id
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
                className="mt-2 w-full resize-none rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none focus:border-sky-500"
                placeholder="예: 최근 배포 중단 이유 알려줘"
              />
            </label>
            <div className="mt-4 flex flex-col gap-2">
              <button
                onClick={runQuery}
                className="rounded-2xl bg-emerald-500/80 px-4 py-2 text-sm font-semibold uppercase tracking-[0.3em] text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
                disabled={isRunning || !question.trim()}
              >
                {isRunning ? "Running…" : "Run query"}
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
                  className={`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.3em] ${
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
            {selectedEntry?.response?.meta ? (
              <div className="mt-2 space-y-1">
                <p>
                  Route: <span className="font-semibold text-white">{selectedEntry.response.meta.route}</span>
                </p>
                <p className="text-[11px] text-slate-400">
                  Reason: {selectedEntry.response.meta.route_reason}
                </p>
                <p className="text-[11px] text-slate-400">
                  Timing: {selectedEntry.response.meta.timing_ms} ms · Used tools:{" "}
                  {selectedEntry.response.meta.used_tools.join(", ") || "N/A"}
                </p>
                <p className="text-[11px] text-slate-400">
                  Fallback: {selectedEntry.response.meta.fallback ? "yes" : "no"}
                </p>
                {selectedEntry.response.meta.error ? (
                  <p className="text-[11px] text-rose-300">Error: {selectedEntry.response.meta.error}</p>
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
          <div className="flex-1 overflow-y-auto">
            {selectedEntry ? (
              <BlockRenderer blocks={selectedEntry.response.blocks} />
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
