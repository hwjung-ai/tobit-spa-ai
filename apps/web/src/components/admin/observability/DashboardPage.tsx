"use client";

import { useState, useEffect } from "react";
import SystemHealthChart from "./SystemHealthChart";
import AlertChannelStatus from "./AlertChannelStatus";
import RuleStatsCard from "./RuleStatsCard";
import ExecutionTimeline from "./ExecutionTimeline";
import ErrorDistribution from "./ErrorDistribution";
import PerformanceMetrics from "./PerformanceMetrics";
import RecentErrors from "./RecentErrors";

export default function DashboardPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      // Refresh can be triggered by changing timestamps
      window.dispatchEvent(new CustomEvent("dashboard-refresh"));
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">CEP Monitoring Dashboard</h1>
          <p className="text-sm text-slate-400">
            Real-time monitoring of rules, channels, and system health
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-700 bg-slate-900/60">
            <input
              type="checkbox"
              id="auto-refresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="auto-refresh" className="text-sm text-slate-300 cursor-pointer">
              Auto-refresh
            </label>
          </div>
          {autoRefresh && (
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="px-3 py-2 rounded-lg border border-slate-700 bg-slate-900/60 text-sm text-slate-300"
            >
              <option value={10}>Every 10s</option>
              <option value={30}>Every 30s</option>
              <option value={60}>Every 60s</option>
              <option value={300}>Every 5m</option>
            </select>
          )}
          <span className="text-xs uppercase tracking-[0.3em] text-sky-400 animate-pulse">
            Live
          </span>
        </div>
      </div>

      {/* System Health Overview */}
      <section>
        <SystemHealthChart />
      </section>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Rules & Channels */}
        <div className="lg:col-span-2 space-y-6">
          {/* Alert Channels */}
          <section>
            <AlertChannelStatus />
          </section>

          {/* Performance Metrics */}
          <section>
            <PerformanceMetrics />
          </section>
        </div>

        {/* Right Column - Rule Stats */}
        <div>
          <section>
            <RuleStatsCard />
          </section>
        </div>
      </div>

      {/* Error Analysis */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Timeline */}
        <section>
          <ExecutionTimeline />
        </section>

        {/* Error Distribution */}
        <section>
          <ErrorDistribution />
        </section>
      </div>

      {/* Recent Errors */}
      <section>
        <RecentErrors />
      </section>

      {/* Footer Info */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-4 py-3 rounded-lg border border-slate-800 bg-slate-950/40">
        <div>
          Last updated: {new Date().toLocaleTimeString()}
        </div>
        <div>
          Data refreshes every {refreshInterval} seconds
        </div>
      </div>
    </div>
  );
}
