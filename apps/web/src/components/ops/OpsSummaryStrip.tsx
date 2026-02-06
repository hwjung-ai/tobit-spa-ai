"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Server,
  Database,
  Network,
} from "lucide-react";
import { type OpsSummaryData, type OpsHistoryEntry } from "./types/opsTypes";
import { cn } from "@/lib/utils";
import { authenticatedFetch } from "@/lib/apiClient/index";

interface OpsSummaryStripProps {
  className?: string;
  selectedEntry?: OpsHistoryEntry | null;
  onUpdateData?: (data: OpsSummaryData) => void;
}

interface AggregatedMetrics {
  totalQueries: number;
  successfulQueries: number;
  failedQueries: number;
  avgResponseTime: number;
  recentActivity: Array<{
    timestamp: string;
    type: "ci" | "metric" | "history" | "relation" | "all";
    status: "ok" | "error";
  }>;
}

export default function OpsSummaryStrip({
  className,
  selectedEntry,
  onUpdateData
}: OpsSummaryStripProps) {
  const [metrics, setMetrics] = useState<AggregatedMetrics>({
    totalQueries: 0,
    successfulQueries: 0,
    failedQueries: 0,
    avgResponseTime: 0,
    recentActivity: [],
  });

  const [isLoading, setIsLoading] = useState(false);
  const [healthStatus, setHealthStatus] = useState<Record<string, string>>({
    service: "ok",
    database: "ok",
    network: "ok"
  });

  // Function to aggregate metrics from the real API
  const aggregateMetrics = useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await authenticatedFetch<{
        totalQueries: number;
        successfulQueries: number;
        failedQueries: number;
        avgResponseTime: number;
        recentActivity: AggregatedMetrics["recentActivity"];
        health: Record<string, string>;
      }>("/ops/summary/stats");

      // ResponseEnvelope logic: the actual data is in (response as any).data
      const data = (response as any).data;

      if (!data) {
        throw new Error("No data received from stats endpoint");
      }

      setMetrics({
        totalQueries: data.totalQueries,
        successfulQueries: data.successfulQueries,
        failedQueries: data.failedQueries,
        avgResponseTime: data.avgResponseTime,
        recentActivity: data.recentActivity,
      });

      if (data.health) {
        setHealthStatus(data.health);
      }

      onUpdateData?.({
        totalQueries: data.totalQueries,
        successRate: data.totalQueries > 0 ? (data.successfulQueries / data.totalQueries) * 100 : 0,
        avgResponseTime: data.avgResponseTime,
        recentActivity: data.recentActivity,
      });
    } catch (error) {
      console.error("Failed to load OPS summary metrics:", error);
    } finally {
      setIsLoading(false);
    }
  }, [onUpdateData]);

  useEffect(() => {
    aggregateMetrics();

    // Auto-refresh every 30 seconds
    const interval = setInterval(aggregateMetrics, 30000);
    return () => clearInterval(interval);
  }, [aggregateMetrics]);

  const getStatusColor = (status: "ok" | "error") => {
    return status === "ok" ? "text-emerald-400" : "text-rose-400";
  };

  const getStatusIcon = (status: "ok" | "error") => {
    return status === "ok" ? (
      <CheckCircle className="h-3 w-3" />
    ) : (
      <AlertTriangle className="h-3 w-3" />
    );
  };

  const getModeLabel = (type: string) => {
    const labels: Record<string, string> = {
      ci: "CI",
      metric: "수치",
      history: "이력",
      relation: "연결",
      all: "전체",
    };
    return labels[type] || type;
  };

  const getHealthColor = (status: string) => {
    return status === "ok" ? "text-green-400" : "text-rose-400";
  };

  const getHealthText = (status: string) => {
    return status === "ok" ? "정상" : "장애";
  };

  return (
    <div className={cn(
      "flex flex-wrap items-center gap-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4",
      className
    )}>
      {/* Overview Stats */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 rounded-full border border-slate-700 px-2 py-1 bg-slate-900/50">
          <BarChart3 className="h-3 w-3 text-sky-400" />
          <span className="text-xs text-slate-300 font-medium">
            총 {metrics.totalQueries.toLocaleString()} 건
          </span>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-emerald-700/50 px-2 py-1 bg-emerald-900/20">
          <CheckCircle className="h-3 w-3 text-emerald-400" />
          <span className="text-xs text-emerald-300 font-medium">
            성공 {metrics.successfulQueries.toLocaleString()} 건
          </span>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-rose-700/50 px-2 py-1 bg-rose-900/20">
          <AlertTriangle className="h-3 w-3 text-rose-400" />
          <span className="text-xs text-rose-300 font-medium">
            실패 {metrics.failedQueries.toLocaleString()} 건
          </span>
        </div>
      </div>

      {/* Response Time */}
      <div className="flex items-center gap-2">
        <Clock className="h-3 w-3 text-amber-400" />
        <span className="text-xs text-slate-400">평균 응답시간</span>
        <span className="text-xs font-mono text-amber-300">
          {metrics.avgResponseTime}ms
        </span>
      </div>

      {/* Current Selection */}
      {selectedEntry && (
        <div className="flex items-center gap-2 border-l border-slate-700 pl-4">
          <Activity className="h-3 w-3 text-purple-400" />
          <span className="text-xs text-slate-400">현재 선택</span>
          <span className="text-xs font-semibold text-purple-300">
            {getModeLabel(selectedEntry.uiMode)}
          </span>
          <span className={cn("text-xs", getStatusColor(selectedEntry.status))}>
            {getStatusIcon(selectedEntry.status)}
            <span className="ml-1"> {selectedEntry.status.toUpperCase()}</span>
          </span>
        </div>
      )}

      {/* Recent Activity */}
      <div className="flex items-center gap-2 border-l border-slate-700 pl-4">
        <div className="flex -space-x-1">
          {metrics.recentActivity.slice(0, 5).reverse().map((activity, index) => (
            <div
              key={`${activity.timestamp}-${index}`}
              className={cn(
                "w-2 h-2 rounded-full border border-slate-900",
                activity.status === "ok"
                  ? "bg-emerald-400"
                  : "bg-rose-400"
              )}
            />
          ))}
        </div>
        <span className="text-xs text-slate-400">최근 활동</span>
      </div>

      {/* Refresh Button */}
      <button
        onClick={aggregateMetrics}
        disabled={isLoading}
        className="ml-auto flex items-center gap-1 rounded-full border border-slate-700 px-2 py-1 bg-slate-900/50 transition hover:border-slate-600 disabled:opacity-50"
      >
        <RefreshCw className={cn(
          "h-3 w-3 text-slate-400",
          isLoading && "animate-spin"
        )} />
        <span className="text-xs text-slate-400">새로고침</span>
      </button>

      {/* System Status Indicators */}
      <div className="flex items-center gap-3 border-l border-slate-700 pl-4">
        <Tooltip content="서비스 상태">
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Server className={cn("h-3 w-3", getHealthColor(healthStatus.service))} />
            <span className={getHealthColor(healthStatus.service)}>{getHealthText(healthStatus.service)}</span>
          </div>
        </Tooltip>
        <Tooltip content="데이터베이스">
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Database className={cn("h-3 w-3", getHealthColor(healthStatus.database))} />
            <span className={getHealthColor(healthStatus.database)}>{getHealthText(healthStatus.database)}</span>
          </div>
        </Tooltip>
        <Tooltip content="네트워크">
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Network className={cn("h-3 w-3", getHealthColor(healthStatus.network))} />
            <span className={getHealthColor(healthStatus.network)}>{getHealthText(healthStatus.network)}</span>
          </div>
        </Tooltip>
      </div>
    </div>
  );
}

// Simple Tooltip component
function Tooltip({ content, children }: { content: string; children: React.ReactNode }) {
  const [show, setShow] = useState(false);

  return (
    <div
      className="relative"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-slate-800 text-xs text-white px-2 py-1 rounded whitespace-nowrap">
          {content}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="w-2 h-2 bg-slate-800 rotate-45" />
          </div>
        </div>
      )}
    </div>
  );
}