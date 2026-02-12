"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

interface SystemStats {
  total_rules: number;
  active_rules: number;
  inactive_rules: number;
  today_execution_count: number;
  today_error_count: number;
  today_error_rate: number;
  today_avg_duration_ms: number;
  last_24h_execution_count: number;
  timestamp: string;
}

interface PerformanceMetric {
  label: string;
  value: string;
  unit: string;
  trend?: "up" | "down" | "stable";
  color: string;
}

export default function PerformanceMetrics() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch("/cep/stats/summary");
        setStats(response.data?.stats || null);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch metrics";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    // Refresh every 60 seconds
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border p-6 text-sm" style={{borderColor: "rgba(51, 65, 85, 0.7)", backgroundColor: "rgba(15, 23, 42, 0.6)", color: "var(--muted-foreground)"}}>
        Loading performance metrics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border p-6 text-sm" style={{borderColor: "rgba(159, 18, 57, 0.7)", backgroundColor: "rgba(120, 53, 15, 0.6)", color: "rgba(251, 146, 60, 1)"}}>
        Error: {error}
      </div>
    );
  }

  if (!stats) return null;

  const metrics: PerformanceMetric[] = [
    {
      label: "Throughput",
      value: (stats.today_execution_count / 24).toFixed(1),
      unit: "exec/hour",
      color: "rgba(56, 189, 248, 1)",
    },
    {
      label: "Avg Response",
      value: stats.today_avg_duration_ms.toFixed(0),
      unit: "ms",
      color: "rgba(192, 132, 252, 1)",
    },
    {
      label: "Error Rate",
      value: (stats.today_error_rate * 100).toFixed(1),
      unit: "%",
      color: stats.today_error_rate < 0.05 ? "rgba(52, 211, 153, 1)" : "rgba(251, 146, 60, 1)",
    },
    {
      label: "Success Rate",
      value: ((1 - stats.today_error_rate) * 100).toFixed(1),
      unit: "%",
      color: "rgba(52, 211, 153, 1)",
    },
  ];

  return (
    <div className="rounded-2xl border p-6" style={{borderColor: "rgba(51, 65, 85, 0.7)", backgroundColor: "rgba(15, 23, 42, 0.6)"}}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold" style={{color: "var(--foreground)"}}>Performance Metrics</h3>
        <span className="text-xs uppercase tracking-[0.2em] " style={{color: "var(--muted-foreground)"}}>Today</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {metrics.map((metric) => (
          <div key={metric.label} className="p-4 rounded-lg /40 border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
            <p className="text-xs  uppercase tracking-[0.1em] mb-3" style={{color: "var(--muted-foreground)"}}>
              {metric.label}
            </p>
            <div className="flex items-baseline gap-2">
              <p className={`text-2xl font-semibold ${metric.color}`}>
                {metric.value}
              </p>
              <p className="text-xs " style={{color: "var(--muted-foreground)"}}>{metric.unit}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Detailed Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Execution Stats */}
        <div className="p-4 rounded-lg /40 border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
          <h4 className="text-sm font-semibold text-white mb-3">Execution Stats</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="" style={{color: "var(--muted-foreground)"}}>Today's Executions</span>
              <span className="text-white font-semibold">
                {stats.today_execution_count.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="" style={{color: "var(--muted-foreground)"}}>Last 24h Executions</span>
              <span className="text-white font-semibold">
                {stats.last_24h_execution_count.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="" style={{color: "var(--muted-foreground)"}}>Average per Hour</span>
              <span className="text-white font-semibold">
                {(stats.today_execution_count / 24).toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        {/* Error Stats */}
        <div className="p-4 rounded-lg /40 border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
          <h4 className="text-sm font-semibold text-white mb-3">Error Stats</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="" style={{color: "var(--muted-foreground)"}}>Today's Errors</span>
              <span
                className={`font-semibold ${
                  stats.today_error_count > 0 ? "text-rose-400" : "text-emerald-400"
                }`}
              >
                {stats.today_error_count}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="" style={{color: "var(--muted-foreground)"}}>Error Rate</span>
              <span
                className={`font-semibold ${
                  stats.today_error_rate < 0.05 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {(stats.today_error_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="" style={{color: "var(--muted-foreground)"}}>Success Rate</span>
              <span className="text-emerald-400 font-semibold">
                {((1 - stats.today_error_rate) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Assessment */}
      <div className="mt-4 p-4 rounded-lg /40 border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
        <h4 className="text-sm font-semibold text-white mb-3">Assessment</h4>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                stats.today_avg_duration_ms < 100 ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            <span className="" style={{color: "var(--muted-foreground)"}}>
              Response Time:{" "}
              <span className="text-white font-semibold">
                {stats.today_avg_duration_ms.toFixed(0)}ms
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                stats.today_error_rate < 0.05 ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            <span className="" style={{color: "var(--muted-foreground)"}}>
              Reliability:{" "}
              <span className="text-white font-semibold">
                {((1 - stats.today_error_rate) * 100).toFixed(1)}%
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                stats.active_rules > 0 ? "bg-emerald-500" : "bg-[var(--surface-elevated)]"
              }`}
            />
            <span className="" style={{color: "var(--muted-foreground)"}}>
              Active Rules:{" "}
              <span className="text-white font-semibold">{stats.active_rules}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
