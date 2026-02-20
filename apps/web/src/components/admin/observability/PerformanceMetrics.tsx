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
        const response = await authenticatedFetch<{ data?: { stats?: SystemStats } }>("/cep/stats/summary");
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
      <div className="container-section text-sm text-muted-foreground">
        Loading performance metrics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-500/50 bg-amber-900/40 p-6 text-sm text-amber-300">
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
      color: "var(--chart-primary-color)",
    },
    {
      label: "Avg Response",
      value: stats.today_avg_duration_ms.toFixed(0),
      unit: "ms",
      color: "var(--chart-accent-purple)",
    },
    {
      label: "Error Rate",
      value: (stats.today_error_rate * 100).toFixed(1),
      unit: "%",
      color: stats.today_error_rate < 0.05 ? "var(--chart-success-color)" : "var(--chart-accent-orange)",
    },
    {
      label: "Success Rate",
      value: ((1 - stats.today_error_rate) * 100).toFixed(1),
      unit: "%",
      color: "var(--chart-success-color)",
    },
  ];

  return (
    <div className="container-section">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground">Performance Metrics</h3>
        <span className="text-sm uppercase tracking-wider text-muted-foreground">Today</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {metrics.map((metric) => (
          <div key={metric.label} className="p-4 rounded-lg border border-variant bg-surface-base">
            <p className="text-xs uppercase tracking-wider mb-3 text-muted-foreground">
              {metric.label}
            </p>
            <div className="flex items-baseline gap-2">
              <p className={`text-2xl font-semibold ${metric.color}`}>
                {metric.value}
              </p>
              <p className="text-xs text-muted-foreground">{metric.unit}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Detailed Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Execution Stats */}
        <div className="p-4 rounded-lg border border-variant bg-surface-base">
          <h4 className="text-sm font-semibold text-foreground dark:text-slate-50 mb-3">Execution Stats</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Today&apos;s Executions</span>
              <span className="text-foreground dark:text-slate-50 font-semibold">
                {stats.today_execution_count.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Last 24h Executions</span>
              <span className="text-foreground dark:text-slate-50 font-semibold">
                {stats.last_24h_execution_count.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Average per Hour</span>
              <span className="text-foreground dark:text-slate-50 font-semibold">
                {(stats.today_execution_count / 24).toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        {/* Error Stats */}
        <div className="p-4 rounded-lg border border-variant bg-surface-base">
          <h4 className="text-sm font-semibold text-foreground dark:text-slate-50 mb-3">Error Stats</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Today&apos;s Errors</span>
              <span
                className={`font-semibold ${
                  stats.today_error_count > 0 ? "text-rose-400" : "text-emerald-400"
                }`}
              >
                {stats.today_error_count}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Error Rate</span>
              <span
                className={`font-semibold ${
                  stats.today_error_rate < 0.05 ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {(stats.today_error_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Success Rate</span>
              <span className="text-emerald-400 font-semibold">
                {((1 - stats.today_error_rate) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Assessment */}
      <div className="mt-4 p-4 rounded-lg border border-variant bg-surface-base">
        <h4 className="text-sm font-semibold text-foreground dark:text-slate-50 mb-3">Assessment</h4>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                stats.today_avg_duration_ms < 100 ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            <span className="text-muted-foreground">
              Response Time:{" "}
              <span className="text-foreground dark:text-slate-50 font-semibold">
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
            <span className="text-muted-foreground">
              Reliability:{" "}
              <span className="text-foreground dark:text-slate-50 font-semibold">
                {((1 - stats.today_error_rate) * 100).toFixed(1)}%
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                stats.active_rules > 0 ? "bg-emerald-500" : "bg-surface-elevated"
              }`}
            />
            <span className="text-muted-foreground">
              Active Rules:{" "}
              <span className="text-foreground dark:text-slate-50 font-semibold">{stats.active_rules}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
