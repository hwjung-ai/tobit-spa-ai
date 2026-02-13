"use client";

import { useState, useEffect } from "react";
import { authenticatedFetch } from "@/lib/apiClient";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface SystemHealth {
  status: string;
  resource?: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent?: number;
  };
}

interface SystemMetric {
  cpu_percent: number;
  memory_percent: number;
  timestamp?: string;
}

interface Alert {
  id: string;
  type: string;
  severity: string;
  message: string;
  timestamp: string;
}

export default function SystemDashboard() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [metrics, setMetrics] = useState<SystemMetric[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);

      const [healthRes, metricsRes, alertsRes] = await Promise.all([
        authenticatedFetch("/admin/system/health"),
        authenticatedFetch("/admin/system/metrics?limit=24"),
        authenticatedFetch("/admin/system/alerts?limit=10"),
      ]);

      if (healthRes?.data?.health) {
        setHealth(healthRes.data.health);
      }

      if (metricsRes?.data?.metrics) {
        setMetrics(metricsRes.data.metrics.slice(-24));
      }

      if (alertsRes?.data?.alerts) {
        setAlerts(alertsRes.data.alerts);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case "healthy":
        return "bg-emerald-500/10 border-emerald-500/50 text-emerald-400";
      case "warning":
        return "bg-amber-500/10 border-amber-500/50 text-amber-400";
      case "critical":
        return "bg-rose-500/10 border-rose-500/50 text-rose-400";
      default:
        return "bg-[var(--muted-background)] border-[var(--border)] text-[var(--muted-foreground)]";
    }
  };

  if (loading && !health) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-900/20 border border-rose-500/50 rounded-2xl p-6 text-rose-300 text-sm">
        <div className="font-bold mb-2">Error loading system data</div>
        <div>{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* System Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Status */}
        <div className={`p-6 rounded-2xl border ${getHealthColor(health?.status || "unknown")}`}>
          <div className="text-tiny uppercase tracking-wider font-bold mb-2">System Status</div>
          <div className="text-3xl font-bold capitalize">{health?.status || "Unknown"}</div>
        </div>

        {/* Active Alerts */}
        <div className="p-6 rounded-2xl border bg-sky-500/10 border-sky-500/50 text-sky-400">
          <div className="text-tiny uppercase tracking-wider font-bold mb-2">Active Alerts</div>
          <div className="text-3xl font-bold">{alerts.length}</div>
        </div>

        {/* CPU Usage */}
        <div className="p-6 rounded-2xl border bg-purple-500/10 border-purple-500/50 text-purple-400">
          <div className="text-tiny uppercase tracking-wider font-bold mb-2">CPU Usage</div>
          <div className="text-3xl font-bold">
            {health?.resource?.cpu_percent ? health.resource.cpu_percent.toFixed(1) : "N/A"}
            <span className="text-lg ml-1">%</span>
          </div>
        </div>

        {/* Memory Usage */}
        <div className="p-6 rounded-2xl border bg-amber-500/10 border-amber-500/50 text-amber-400">
          <div className="text-tiny uppercase tracking-wider font-bold mb-2">Memory Usage</div>
          <div className="text-3xl font-bold">
            {health?.resource?.memory_percent ? health.resource.memory_percent.toFixed(1) : "N/A"}
            <span className="text-lg ml-1">%</span>
          </div>
        </div>
      </div>

      {/* Resource Usage Chart */}
      {metrics.length > 0 && (
        <div className="border border-variant bg-surface-overlay rounded-2xl p-6">
          <h3 className="text-lg font-bold text-foreground mb-4">Resource Usage (Last 24 Hours)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-tooltip-border)" />
              <XAxis dataKey="timestamp" stroke="var(--chart-text-color)" />
              <YAxis stroke="var(--chart-text-color)" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--chart-tooltip-bg)",
                  border: "1px solid var(--chart-tooltip-border)",
                  borderRadius: "var(--radius-lg)",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="cpu_percent"
                stroke="var(--chart-accent-purple)"
                name="CPU %"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="memory_percent"
                stroke="var(--chart-warning-color)"
                name="Memory %"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Alerts Panel */}
      <div className="border border-variant bg-surface-overlay rounded-2xl p-6">
        <h3 className="text-lg font-bold text-foreground mb-4">System Alerts</h3>

        {alerts.length === 0 ? (
          <div className="bg-emerald-500/10 border border-emerald-500/50 text-emerald-300 p-4 rounded-lg text-sm">
            ✓ No active alerts - System is healthy
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border ${
                  alert.severity === "critical"
                    ? "bg-rose-500/10 border-rose-500/50 text-rose-300"
                    : alert.severity === "warning"
                    ? "bg-amber-500/10 border-amber-500/50 text-amber-300"
                    : "bg-sky-500/10 border-sky-500/50 text-sky-300"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-bold text-sm mb-1">{alert.message}</div>
                    <div className="text-xs opacity-60">
                      {new Date(alert.timestamp).toLocaleString()}
                    </div>
                  </div>
                  <div className="text-tiny uppercase tracking-wider font-bold px-2 py-1 rounded bg-white/10">
                    {alert.severity}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Last Updated */}
      <div className="flex items-center justify-between text-xs text-muted-foreground px-4">
        <div>Last updated: {new Date().toLocaleTimeString()}</div>
        <div>Auto-refresh every 30 seconds</div>
      </div>
    </div>
  );
}
