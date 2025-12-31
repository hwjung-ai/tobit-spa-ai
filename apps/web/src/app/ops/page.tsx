"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import BlockRenderer, { type AnswerEnvelope } from "../../components/answer/BlockRenderer";

type OpsMode = "all" | "metric" | "hist" | "graph";
const OPS_MODES: OpsMode[] = ["all", "metric", "hist", "graph"];

const HISTORY_STORAGE_KEY = "ops:history:v1";
const HISTORY_LIMIT = 40;

const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

interface OpsHistoryEntry {
  id: string;
  createdAt: string;
  mode: OpsMode;
  question: string;
  response: AnswerEnvelope;
  status: "ok" | "error";
  summary: string;
}

const mapModeLabel: Record<OpsMode, string> = {
  all: "All",
  metric: "Metric",
  hist: "History",
  graph: "Graph",
};

const buildErrorEnvelope = (mode: OpsMode, errorMessage: string): AnswerEnvelope => ({
  meta: {
    route: mode,
    route_reason: "client error",
    timing_ms: 0,
    summary: errorMessage,
    used_tools: [],
    fallback: true,
    error: errorMessage,
  },
  blocks: [
    {
      type: "markdown",
      title: "Error",
      content: `🟥 ${errorMessage}`,
    },
  ],
});

const formatTimestamp = (value: string) => {
  try {
    return new Date(value).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

const extractSummary = (envelope: AnswerEnvelope | null, question: string) => {
  if (!envelope) {
    return question;
  }
  if (envelope.meta?.summary) {
    return envelope.meta.summary;
  }
  const markdown = envelope.blocks?.find((block) => block.type === "markdown");
  if (markdown && markdown.content) {
    return markdown.content.split("\n")[0];
  }
  return question;
};

const genId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export default function OpsPage() {
  const [history, setHistory] = useState<OpsHistoryEntry[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<OpsMode>("all");
  const [question, setQuestion] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

  useEffect(() => {
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) {
      return;
    }
    try {
      const parsed: OpsHistoryEntry[] = JSON.parse(raw);
      if (parsed.length > 0) {
        setHistory(parsed);
        setSelectedId(parsed[0].id);
      }
    } catch {
      window.localStorage.removeItem(HISTORY_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  const selectedEntry = useMemo(() => {
    return history.find((entry) => entry.id === selectedId) ?? history[0] ?? null;
  }, [history, selectedId]);

  const runQuery = useCallback(async () => {
    if (!question.trim() || isRunning) {
      return;
    }
    setIsRunning(true);
    setStatusMessage(null);
    const payload = { mode, question: question.trim() };
    let envelope: AnswerEnvelope;
    let status: OpsHistoryEntry["status"] = "ok";
    try {
      const response = await fetch(`${apiBaseUrl}/ops/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? data.message ?? "OPS query failed");
      }
      const answer = data.data?.answer as AnswerEnvelope | undefined;
      if (!answer) {
        throw new Error("Empty OPS response");
      }
      envelope = answer;
      status = "ok";
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      envelope = buildErrorEnvelope(mode, message);
      status = "error";
      setStatusMessage(`Error: ${message}`);
    } finally {
      const entry: OpsHistoryEntry = {
        id: genId(),
        createdAt: new Date().toISOString(),
        mode,
        question: question.trim(),
        response: envelope,
        status,
        summary: extractSummary(envelope, question.trim()),
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
    }
  }, [apiBaseUrl, isRunning, mode, question]);

  const selectedModeLabel = mapModeLabel[selectedEntry?.mode ?? mode];

  return (
    <div className="py-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(320px,360px)_minmax(0,1fr)]">
        <div className="flex h-[80vh] flex-col gap-4">
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
                            {mapModeLabel[entry.mode]}
                          </span>
                          <span>{formatTimestamp(entry.createdAt)}</span>
                        </div>
                        <p
                          className="mt-2 text-sm font-semibold leading-snug text-white overflow-hidden text-ellipsis"
                          style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}
                        >
                          {entry.question}
                        </p>
                        <p
                          className="text-[12px] text-slate-400 overflow-hidden text-ellipsis"
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
            <label className="text-[11px] uppercase tracking-[0.3em] text-slate-400">
              Mode
              <select
                value={mode}
                onChange={(event) => setMode(event.target.value as OpsMode)}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none focus:border-sky-500"
              >
                {OPS_MODES.map((item) => (
                  <option key={item} value={item}>
                    {mapModeLabel[item]}
                  </option>
                ))}
              </select>
            </label>
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
              {statusMessage ? (
                <p className="text-[11px] text-rose-300">{statusMessage}</p>
              ) : null}
            </div>
          </div>
        </div>
        <section className="flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 shadow-inner shadow-black/40">
          <header>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">OPS answer</p>
                <h1 className="text-lg font-semibold text-white">
                  {selectedModeLabel} · {selectedEntry ? formatTimestamp(selectedEntry.createdAt) : ""}
                </h1>
                {selectedEntry ? (
                  <p className="text-[12px] text-slate-400">{selectedEntry.question}</p>
                ) : (
                  <p className="text-[12px] text-slate-500">질의를 실행하면 결과가 여기 표시됩니다.</p>
                )}
              </div>
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
