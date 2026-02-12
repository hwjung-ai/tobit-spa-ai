"use client";

import React, { useCallback, useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";
import LlmLogsContent from "./llm-logs-content";
import { cn } from "@/lib/utils";

type LogType = "query-history" | "execution-trace" | "audit" | "api-file" | "web-file" | "llm-logs";

interface LogRecord {
  [key: string]: unknown;
}

interface LogData {
  records: LogRecord[];
  lines?: string[];
  total: number;
  limit: number;
  offset: number;
  file?: string;
  exists?: boolean;
}

const LOG_TABS: Array<{ type: LogType; label: string; activeClass: string }> = [
  { type: "query-history", label: "Query History", activeClass: "bg-sky-600 text-white hover:bg-sky-500" },
  { type: "execution-trace", label: "Execution Trace", activeClass: "bg-sky-600 text-white hover:bg-sky-500" },
  { type: "audit", label: "Audit Log", activeClass: "bg-sky-600 text-white hover:bg-sky-500" },
  { type: "llm-logs", label: "LLM Calls", activeClass: "bg-sky-600 text-white hover:bg-sky-500" },
  { type: "api-file", label: "API Server Logs", activeClass: "bg-emerald-600 text-white hover:bg-emerald-500" },
  { type: "web-file", label: "WEB Server Logs", activeClass: "bg-emerald-600 text-white hover:bg-emerald-500" },
];

export default function LogsPage() {
  const [logType, setLogType] = useState<LogType>("query-history");
  const [data, setData] = useState<LogData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let endpoint = "";
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: (page * limit).toString(),
      });

      switch (logType) {
        case "query-history":
          endpoint = `/admin/logs/query-history?${params}`;
          break;
        case "execution-trace":
          endpoint = `/admin/logs/execution-trace?${params}`;
          break;
        case "audit":
          endpoint = `/admin/logs/audit?${params}`;
          break;
        case "api-file":
          endpoint = "/admin/logs/file/api/tail?lines=100";
          break;
        case "web-file":
          endpoint = "/admin/logs/file/web/tail?lines=100";
          break;
        case "llm-logs":
          break;
      }

      if (logType !== "llm-logs" && endpoint) {
        const response = await authenticatedFetch(endpoint);
        if (response?.data) {
          setData(response.data as LogData);
        } else {
          setError("No data received");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch logs");
    } finally {
      setLoading(false);
    }
  }, [logType, page, limit]);

  useEffect(() => {
    if (logType !== "llm-logs") {
      fetchLogs();
    }
  }, [fetchLogs, logType]);

  useEffect(() => {
    if (!(logType === "api-file" || logType === "web-file") || !autoRefresh) {
      return;
    }

    const intervalId = setInterval(fetchLogs, 3000);
    return () => clearInterval(intervalId);
  }, [autoRefresh, logType, fetchLogs]);

  const renderTable = (records: LogRecord[]) => {
    if (!records || records.length === 0) {
      return <div className="py-10 text-center text-sm" style={{ color: "var(--muted-foreground)" }}>No logs found</div>;
    }

    const columns = Object.keys(records[0]);

    return (
      <div className="overflow-x-auto rounded-2xl border" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-elevated)" }}>
              {columns.map((col) => (
                <th key={col} className="px-3 py-2 text-left font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                  {col.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.map((record, idx) => (
              <tr key={idx} className="border-b last:border-b-0" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2 align-top" style={{ color: "var(--foreground)" }}>
                    {typeof record[col] === "object" ? JSON.stringify(record[col]) : String(record[col] ?? "-")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderFileLog = (lines: string[]) => {
    return (
      <div className="custom-scrollbar max-h-[600px] overflow-auto rounded-2xl border p-4 font-mono text-[10px]" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)" }}>
        {lines.map((line, idx) => (
          <div
            key={idx}
            className={cn(
              "py-0.5",
              line.includes("ERROR") || line.includes("error")
                ? "text-rose-400"
                : line.includes("WARNING") || line.includes("WARN")
                  ? "text-amber-400"
                  : ""
            )}
            style={{ color: line.includes("ERROR") || line.includes("error") || line.includes("WARNING") || line.includes("WARN") ? undefined : "var(--foreground)" }}
          >
            {line}
          </div>
        ))}
      </div>
    );
  };

  const totalPages = data ? Math.ceil(data.total / limit) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-2 text-lg font-semibold" style={{ color: "var(--foreground)" }}>System Logs</h2>
        <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
          View system logs including query history, execution traces, audit logs, LLM calls, and server logs.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {LOG_TABS.map((tab) => {
          const active = logType === tab.type;
          return (
            <button
              key={tab.type}
              onClick={() => {
                setLogType(tab.type);
                setPage(0);
              }}
              className={cn(
                "rounded-lg border px-4 py-2 text-xs font-semibold tracking-wider transition",
                active
                  ? tab.activeClass
                  : "hover:bg-slate-100 dark:hover:bg-slate-800"
              )}
              style={
                active
                  ? { borderColor: "transparent" }
                  : {
                      borderColor: "var(--border)",
                      backgroundColor: "var(--surface-elevated)",
                      color: "var(--foreground)",
                    }
              }
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {(logType === "api-file" || logType === "web-file") && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="autoRefresh"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="autoRefresh" className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            Auto-refresh every 3 seconds
          </label>
        </div>
      )}

      {logType === "llm-logs" ? (
        <LlmLogsContent />
      ) : (
        <div className="space-y-4 rounded-2xl border p-4" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-elevated)" }}>
          {loading && (
            <div className="py-8 text-center text-sm" style={{ color: "var(--muted-foreground)" }}>
              Loading logs...
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-500/50 bg-rose-900/20 p-4 text-sm text-rose-300">
              Error: {error}
            </div>
          )}

          {!loading && !error && data && (
            <>
              {data.records && renderTable(data.records)}
              {data.lines && renderFileLog(data.lines)}

              {data.file && (
                <div className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                  File: {data.file} | Exists: {data.exists ? "Yes" : "No"}
                </div>
              )}

              {data.records && data.total > limit && (
                <div className="mt-2 flex items-center justify-between text-sm">
                  <div style={{ color: "var(--muted-foreground)" }}>
                    Showing {page * limit + 1} - {Math.min((page + 1) * limit, data.total)} of {data.total}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(Math.max(0, page - 1))}
                      disabled={page === 0}
                      className="rounded-lg border px-3 py-1 transition disabled:cursor-not-allowed disabled:opacity-50"
                      style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
                    >
                      Previous
                    </button>
                    <div className="px-3 py-1" style={{ color: "var(--muted-foreground)" }}>
                      Page {page + 1} of {totalPages}
                    </div>
                    <button
                      onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                      disabled={page >= totalPages - 1}
                      className="rounded-lg border px-3 py-1 transition disabled:cursor-not-allowed disabled:opacity-50"
                      style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
