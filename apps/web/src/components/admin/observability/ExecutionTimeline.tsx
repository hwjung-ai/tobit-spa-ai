"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { authenticatedFetch } from "@/lib/apiClient";

interface TimelineEntry {
  timestamp: string;
  error_count: number;
}

interface ErrorTimeline {
  timeline: TimelineEntry[];
  error_distribution: Record<string, number>;
  recent_errors: Array<{
    exec_id: string;
    rule_id: string;
    rule_name: string;
    triggered_at: string;
    error_message: string | null;
    duration_ms: number;
  }>;
  period: string;
  total_errors: number;
}

export default function ExecutionTimeline() {
  const [timeline, setTimeline] = useState<ErrorTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState("24h");

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch(`/cep/errors/timeline?period=${period}`);
        setTimeline(response.data || null);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch timeline";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [period]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-6 text-slate-400 text-sm">
        Loading error timeline...
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

  if (!timeline) return null;

  const chartData = timeline.timeline.map((entry) => ({
    time: new Date(entry.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    errors: entry.error_count,
  }));

  return (
    <div className="rounded-2xl border border-slate-800/70 bg-slate-900/60 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Error Timeline</h3>
        <div className="flex gap-2">
          {(["1h", "6h", "24h", "7d"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded text-xs uppercase tracking-[0.2em] transition ${
                period === p
                  ? "bg-sky-500/20 text-sky-400 border border-sky-500/50"
                  : "border border-slate-700 text-slate-400 hover:text-slate-300 hover:border-slate-600"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="mb-6">
        {chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-400 text-sm">
            No errors in selected period
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                <XAxis
                  dataKey="time"
                  stroke="#94a3b8"
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                  cursor={{ stroke: "rgba(148, 163, 184, 0.2)" }}
                  formatter={(value) => [value, "Errors"]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="errors"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={false}
                  name="Error Count"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 rounded-lg bg-slate-950/40 border border-slate-800">
          <p className="text-xs text-slate-400 mb-1">Total Errors</p>
          <p className="text-2xl font-semibold text-white">{timeline.total_errors}</p>
        </div>
        {Object.entries(timeline.error_distribution).map(([type, count]) => (
          <div key={type} className="p-4 rounded-lg bg-slate-950/40 border border-slate-800">
            <p className="text-xs text-slate-400 mb-1 capitalize">{type}</p>
            <p className="text-2xl font-semibold text-white">{count}</p>
          </div>
        ))}
      </div>

      {/* Recent Errors List */}
      <div>
        <h4 className="text-sm font-semibold text-white mb-3">Recent Errors</h4>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {timeline.recent_errors.length === 0 ? (
            <p className="text-xs text-slate-400">No errors recorded</p>
          ) : (
            timeline.recent_errors.map((err) => (
              <div
                key={err.exec_id}
                className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/50 hover:border-rose-500/50 transition"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-white truncate">
                    {err.rule_name}
                  </span>
                  <span className="text-xs text-slate-400">
                    {new Date(err.triggered_at).toLocaleTimeString()}
                  </span>
                </div>
                {err.error_message && (
                  <p className="text-xs text-rose-400 truncate">{err.error_message}</p>
                )}
                <p className="text-xs text-slate-500">
                  Duration: {err.duration_ms}ms
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
