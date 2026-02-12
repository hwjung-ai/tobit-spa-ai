"use client";

import React, { useCallback, useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";
import { fetchApi } from "@/lib/adminUtils";
import LlmLogsContent from "./llm-logs-content";

type LogType = "query-history" | "execution-trace" | "audit" | "api-file" | "web-file" | "llm-logs";

interface LogRecord {
    [key: string]: any;
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

export default function LogsPage() {
    const [logType, setLogType] = useState<LogType>("query-history");
    const [data, setData] = useState<LogData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const [limit] = useState(50);
    const [autoRefresh, setAutoRefresh] = useState(false);
    const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

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
                    endpoint = `/admin/logs/file/api/tail?lines=100`;
                    break;
                case "web-file":
                    endpoint = `/admin/logs/file/web/tail?lines=100`;
                    break;
                case "llm-logs":
                    // LLM logs are handled by separate component
                    break;
            }

            if (logType !== "llm-logs" && endpoint) {
                const response = await authenticatedFetch(endpoint);

                if (response?.data) {
                    setData(response.data);
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
        if (autoRefresh && (logType === "api-file" || logType === "web-file")) {
            const interval = setInterval(fetchLogs, 3000);
            setRefreshInterval(interval);
            return () => clearInterval(interval);
        } else if (refreshInterval) {
            clearInterval(refreshInterval);
            setRefreshInterval(null);
        }
    }, [autoRefresh, logType, fetchLogs, refreshInterval]);

    const renderTable = (records: LogRecord[]) => {
        if (!records || records.length === 0) {
            return (
                <div className="text-center py-8 text-slate-400">
                    No logs found
                </div>
            );
        }

        const columns = Object.keys(records[0]);

        return (
            <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                    <thead>
                        <tr className="border-b border-slate-300 dark:border-slate-800">
                            {columns.map((col) => (
                                <th
                                    key={col}
                                    className="px-3 py-2 text-left font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider"
                                >
                                    {col.replace(/_/g, " ")}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {records.map((record, idx) => (
                            <tr
                                key={idx}
                                className="border-b border-slate-200 dark:border-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800/30"
                            >
                                {columns.map((col) => (
                                    <td key={col} className="px-3 py-2 text-slate-700 dark:text-slate-400">
                                        {typeof record[col] === "object"
                                            ? JSON.stringify(record[col])
                                            : String(record[col] || "-")}
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
            <div className="bg-black/50 rounded p-4 font-mono text-[10px] overflow-auto max-h-[600px]">
                {lines.map((line, idx) => (
                    <div
                        key={idx}
                        className={`py-0.5 ${
                            line.includes("ERROR") || line.includes("error")
                                ? "text-red-400"
                                : line.includes("WARNING") || line.includes("WARN")
                                ? "text-yellow-400"
                                : "text-slate-300"
                        }`}
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
            {/* Header */}
            <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50 mb-2">System Logs</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                    View system logs including query history, execution traces, audit logs, LLM calls, and server logs.
                </p>
            </div>

            {/* Log Type Selector */}
            <div className="flex flex-wrap gap-2">
                <button
                    onClick={() => { setLogType("query-history"); setPage(0); }}
                    className={`px-4 py-2 rounded text-xs font-semibold transition ${
                        logType === "query-history"
                            ? "bg-sky-500 text-white"
                            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                >
                    Query History
                </button>
                <button
                    onClick={() => { setLogType("execution-trace"); setPage(0); }}
                    className={`px-4 py-2 rounded text-xs font-semibold transition ${
                        logType === "execution-trace"
                            ? "bg-sky-500 text-white"
                            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                >
                    Execution Trace
                </button>
                <button
                    onClick={() => { setLogType("audit"); setPage(0); }}
                    className={`px-4 py-2 rounded text-xs font-semibold transition ${
                        logType === "audit"
                            ? "bg-sky-500 text-white"
                            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                >
                    Audit Log
                </button>
                <button
                    onClick={() => { setLogType("llm-logs"); setPage(0); }}
                    className={`px-4 py-2 rounded text-xs font-semibold transition ${
                        logType === "llm-logs"
                            ? "bg-purple-500 text-white"
                            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                >
                    LLM Calls
                </button>
                <button
                    onClick={() => { setLogType("api-file"); setPage(0); }}
                    className={`px-4 py-2 rounded text-xs font-semibold transition ${
                        logType === "api-file"
                            ? "bg-emerald-500 text-white"
                            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                >
                    API Server Logs
                </button>
                <button
                    onClick={() => { setLogType("web-file"); setPage(0); }}
                    className={`px-4 py-2 rounded text-xs font-semibold transition ${
                        logType === "web-file"
                            ? "bg-emerald-500 text-white"
                            : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                >
                    WEB Server Logs
                </button>
            </div>

            {/* Auto Refresh (for file logs) */}
            {(logType === "api-file" || logType === "web-file") && (
                <div className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        id="autoRefresh"
                        checked={autoRefresh}
                        onChange={(e) => setAutoRefresh(e.target.checked)}
                        className="rounded"
                    />
                    <label htmlFor="autoRefresh" className="text-xs text-slate-300">
                        Auto-refresh every 3 seconds
                    </label>
                </div>
            )}

            {/* LLM Logs Content */}
            {logType === "llm-logs" ? (
                <LlmLogsContent />
            ) : (
                <>
                    {/* Loading/Error State */}
                    {loading && (
                        <div className="text-center py-8 text-slate-600 dark:text-slate-400">
                            Loading logs...
                        </div>
                    )}
                    {error && (
                        <div className="bg-red-900/20 border border-red-500/50 rounded p-4 text-red-700 dark:text-red-300 text-sm">
                            Error: {error}
                        </div>
                    )}

                    {/* Content */}
                    {!loading && !error && data && (
                        <div>
                            {/* Database Logs */}
                            {data.records && renderTable(data.records)}

                            {/* File Logs */}
                            {data.lines && renderFileLog(data.lines)}

                            {/* File Info */}
                            {data.file && (
                                <div className="mt-4 text-xs text-slate-500 dark:text-slate-500">
                                    File: {data.file} | Exists: {data.exists ? "Yes" : "No"}
                                </div>
                            )}

                            {/* Pagination */}
                            {data.records && data.total > limit && (
                                <div className="flex items-center justify-between mt-6 text-sm">
                                    <div className="text-slate-600 dark:text-slate-400">
                                        Showing {page * limit + 1} - {Math.min((page + 1) * limit, data.total)} of {data.total}
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setPage(Math.max(0, page - 1))}
                                            disabled={page === 0}
                                            className="px-3 py-1 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            Previous
                                        </button>
                                        <div className="px-3 py-1 text-slate-600 dark:text-slate-400">
                                            Page {page + 1} of {totalPages}
                                        </div>
                                        <button
                                            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                                            disabled={page >= totalPages - 1}
                                            className="px-3 py-1 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            Next
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
