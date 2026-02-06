"use client";

import { useEffect, useState } from "react";

interface Error {
  exec_id: string;
  rule_id: string;
  rule_name: string;
  triggered_at: string;
  error_message: string | null;
  duration_ms: number;
}

interface ErrorsData {
  timeline: Array<{ timestamp: string; error_count: number }>;
  error_distribution: Record<string, number>;
  recent_errors: Error[];
  period: string;
  total_errors: number;
}

export default function RecentErrors() {
  const [errors, setErrors] = useState<Error[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchErrors = async () => {
      try {
        setLoading(true);
        const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/, "");
        const response = await fetch(`${apiBaseUrl}/cep/errors/timeline?period=24h`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data: { data: ErrorsData } = await response.json();
        setErrors(data.data?.recent_errors || []);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch errors";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchErrors();
    // Refresh every 60 seconds
    const interval = setInterval(fetchErrors, 60000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (message: string | null): string => {
    if (!message) return "text-slate-400";
    if (message.toLowerCase().includes("timeout")) return "text-rose-400";
    if (message.toLowerCase().includes("connection")) return "text-orange-400";
    if (message.toLowerCase().includes("validation")) return "text-yellow-400";
    return "text-slate-400";
  };

  const getSeverityBgColor = (message: string | null): string => {
    if (!message) return "bg-slate-800/30";
    if (message.toLowerCase().includes("timeout")) return "bg-rose-800/20 border-rose-800/50";
    if (message.toLowerCase().includes("connection")) return "bg-orange-800/20 border-orange-800/50";
    if (message.toLowerCase().includes("validation")) return "bg-yellow-800/20 border-yellow-800/50";
    return "bg-slate-800/30";
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-6 text-slate-400 text-sm">
        Loading recent errors...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-800/70 bg-rose-900/60 p-6 text-rose-400 text-sm">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Recent Errors</h3>
        <span className="text-xs uppercase tracking-[0.2em] text-slate-400">
          {errors.length} errors
        </span>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {errors.length === 0 ? (
          <div className="p-6 text-center rounded-lg bg-slate-950/40 border border-slate-800">
            <div className="inline-block p-3 rounded-full bg-emerald-500/10 mb-3">
              <svg
                className="w-6 h-6 text-emerald-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-sm text-slate-400">No errors in the last 24 hours</p>
          </div>
        ) : (
          errors.map((err) => (
            <div
              key={err.exec_id}
              className={`p-4 rounded-lg border cursor-pointer transition ${getSeverityBgColor(
                err.error_message
              )}`}
            >
              {/* Header */}
              <button
                onClick={() =>
                  setExpandedId(expandedId === err.exec_id ? null : err.exec_id)
                }
                className="w-full text-left"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3 flex-1">
                    <div
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${getSeverityColor(
                        err.error_message
                      ).replace("text-", "bg-")}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-semibold truncate">{err.rule_name}</p>
                      <p className="text-xs text-slate-400">
                        {new Date(err.triggered_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                    <span className="text-xs text-slate-400">{err.duration_ms}ms</span>
                    <svg
                      className={`w-4 h-4 text-slate-400 transition ${
                        expandedId === err.exec_id ? "rotate-180" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 14l-7 7m0 0l-7-7m7 7V3"
                      />
                    </svg>
                  </div>
                </div>

                {/* Error Message Preview */}
                {err.error_message && (
                  <p className={`text-xs ${getSeverityColor(err.error_message)} truncate`}>
                    {err.error_message}
                  </p>
                )}
              </button>

              {/* Expanded Details */}
              {expandedId === err.exec_id && (
                <div className="mt-4 pt-4 border-t border-slate-700/50 space-y-3">
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Execution ID</p>
                    <p className="text-xs font-mono text-slate-300 break-all">
                      {err.exec_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Rule ID</p>
                    <p className="text-xs font-mono text-slate-300 break-all">
                      {err.rule_id}
                    </p>
                  </div>
                  {err.error_message && (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Error Message</p>
                      <p className={`text-xs font-mono ${getSeverityColor(err.error_message)} break-words`}>
                        {err.error_message}
                      </p>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className="text-slate-400 mb-1">Duration</p>
                      <p className="text-white font-semibold">{err.duration_ms}ms</p>
                    </div>
                    <div>
                      <p className="text-slate-400 mb-1">Timestamp</p>
                      <p className="text-white font-semibold">
                        {new Date(err.triggered_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
