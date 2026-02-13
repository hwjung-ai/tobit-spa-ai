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
  const [isFullScreen, setIsFullScreen] = useState(false);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      // Refresh can be triggered by changing timestamps
      window.dispatchEvent(new CustomEvent("dashboard-refresh"));
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  return (
    <div className={isFullScreen ? "fixed inset-0 z-50 overflow-auto p-6 animate-in fade-in zoom-in-95 duration-300" : "space-y-6 relative"} style={{ backgroundColor: isFullScreen ? "var(--background)" : undefined }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div />
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsFullScreen(!isFullScreen)}
            className="flex h-10 w-10 items-center justify-center rounded-lg border transition-colors"
            style={{ borderColor: "var(--border)", backgroundColor: "rgba(2, 6, 23, 0.6)", color: "var(--muted-foreground)" }}
            title={isFullScreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          >
            {isFullScreen ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" /></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" /></svg>
            )}
          </button>
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg border" style={{ borderColor: "var(--border)", backgroundColor: "rgba(2, 6, 23, 0.6)" }}>
            <input
              type="checkbox"
              id="auto-refresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="auto-refresh" className="text-sm cursor-pointer" style={{ color: "var(--foreground-secondary)" }}>
              Auto-refresh
            </label>
          </div>
          {autoRefresh && (
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="px-3 py-2 rounded-lg border text-sm"
              style={{ borderColor: "var(--border)", backgroundColor: "rgba(2, 6, 23, 0.6)", color: "var(--foreground-secondary)" }}
            >
              <option value={10}>Every 10s</option>
              <option value={30}>Every 30s</option>
              <option value={60}>Every 60s</option>
              <option value={300}>Every 5m</option>
            </select>
          )}
          <span className="text-sm uppercase tracking-[0.3em] text-sky-400 animate-pulse">
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
      <div className="flex items-center justify-between text-xs px-4 py-3 rounded-lg border" style={{ color: "var(--muted-foreground)", borderColor: "var(--border)", backgroundColor: "rgba(2, 6, 23, 0.4)" }}>
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
