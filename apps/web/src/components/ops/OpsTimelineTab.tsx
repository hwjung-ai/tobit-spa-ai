"use client";

import { useState, useEffect, useCallback } from "react";
import { formatRelativeTime } from "./utils/TimeUtils";
import {
  Activity,
  Clock,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Search,
  Server,
  Database,
  Network,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { type OpsHistoryEntry } from "./types/opsTypes";

interface TimelineEntry {
  id: string;
  timestamp: string;
  type: "ci" | "metric" | "history" | "relation" | "all";
  status: "ok" | "error";
  message: string;
  duration?: number;
  details?: {
    traceId?: string;
    question?: string;
    route?: string;
    usedTools?: string[];
  };
}

interface OpsTimelineTabProps {
  className?: string;
  onSelectEntry?: (entry: OpsHistoryEntry) => void;
}

// Mock data generator - in real implementation, this would fetch from API
const generateMockTimeline = (): TimelineEntry[] => {
  const now = new Date();
  const timeline: TimelineEntry[] = [];

  // Generate last 24 hours of data
  for (let i = 0; i < 24; i++) {
    const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
    const type = ["ci", "metric", "history", "relation", "all"][Math.floor(Math.random() * 5)] as TimelineEntry["type"];
    const status = Math.random() > 0.2 ? "ok" : "error";

    timeline.push({
      id: `timeline-${i}`,
      timestamp: timestamp.toISOString(),
      type,
      status,
      message: `${type.toUpperCase()} query ${status === "ok" ? "completed" : "failed"} successfully`,
      duration: Math.floor(Math.random() * 1000) + 100,
      details: {
        traceId: `trace-${i}`,
        question: `Sample ${type} query #${i}`,
        route: "orch",
        usedTools: ["executor", "validator", "renderer"],
      },
    });
  }

  return timeline.reverse();
};

export default function OpsTimelineTab({
  className,
  onSelectEntry
}: OpsTimelineTabProps) {
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | TimelineEntry["type"]>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadTimeline = useCallback(async () => {
    setIsLoading(true);
    try {
      // In real implementation, this would be:
      // const response = await authenticatedFetch("/ops/timeline?limit=50");
      // const data = response.data.timeline;

      const mockData = generateMockTimeline();
      setTimeline(mockData);
    } catch (error) {
      console.error("Failed to load timeline:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTimeline();

    // Auto refresh if enabled
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(loadTimeline, 30000); // 30 seconds
    }
    return () => clearInterval(interval);
  }, [loadTimeline, autoRefresh]);

  const filteredTimeline = timeline.filter(entry => {
    const matchesFilter = filter === "all" || entry.type === filter;
    const matchesSearch = searchTerm === "" ||
      entry.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.details?.question?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusIcon = (status: TimelineEntry["status"]) => {
    return status === "ok" ? (
      <CheckCircle className="h-3 w-3 text-emerald-400" />
    ) : (
      <AlertTriangle className="h-3 w-3 text-rose-400" />
    );
  };

  const getTypeIcon = (type: TimelineEntry["type"]) => {
    const icons = {
      ci: <Server className="h-3 w-3 text-sky-400" />,
      metric: <Database className="h-3 w-3 text-amber-400" />,
      history: <Clock className="h-3 w-3 text-purple-400" />,
      relation: <Network className="h-3 w-3 text-green-400" />,
      all: <Activity className="h-3 w-3 " style={{color: "var(--muted-foreground)"}} />,
    };
    return icons[type];
  };

  const getStatusColor = (status: TimelineEntry["status"]) => {
    return status === "ok" ? "border-emerald-400 bg-emerald-400/5" : "border-rose-400 bg-rose-400/5";
  };

  const getDurationColor = (duration?: number) => {
    if (!duration) return "text-[var(--muted-foreground)]";
    if (duration < 300) return "text-emerald-400";
    if (duration < 800) return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className={cn(
      "flex flex-col h-full rounded-2xl border border-[var(--border)] bg-[var(--surface-overlay)]",
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b " style={{borderColor: "var(--border)"}}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">
            OPS Timeline
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(
                "flex items-center gap-1 px-2 py-1 rounded-full text-xs border transition",
                autoRefresh
                  ? "border-emerald-400 text-emerald-400 bg-emerald-400/5"
                  : "border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--border)]"
              )}
            >
              <RefreshCw className={cn(
                "h-3 w-3",
                autoRefresh && "animate-spin"
              )} />
              Auto Refresh
            </button>
            <button
              onClick={loadTimeline}
              disabled={isLoading}
              className="flex items-center gap-1 px-2 py-1 rounded-full text-xs border   transition hover: disabled:opacity-50" style={{borderColor: "var(--border)", color: "var(--muted-foreground)"}}
            >
              <RefreshCw className={cn(
                "h-3 w-3",
                isLoading && "animate-spin"
              )} />
              Refresh
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-4">
          {["all", "ci", "metric", "history", "relation"].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type as "all" | TimelineEntry["type"])}
              className={cn(
                "px-3 py-1 rounded-full text-xs border transition capitalize",
                filter === type
                  ? "border-sky-400 text-sky-300 bg-sky-400/10"
                  : "border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--border)]"
              )}
            >
              {type === "all" ? "All" : type}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-3 w-3 " style={{color: "var(--muted-foreground)"}} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search timeline entries..."
            className="w-full pl-9 pr-3 py-2  border  rounded-lg text-sm text-white placeholder-slate-500 focus:border-sky-500 outline-none" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
          />
        </div>
      </div>

      {/* Timeline Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredTimeline.length === 0 ? (
          <div className="text-center py-8">
            <Activity className="h-8 w-8  mx-auto mb-2" style={{color: "var(--muted-foreground)"}} />
            <p className="text-sm " style={{color: "var(--muted-foreground)"}}>
              {isLoading ? "Loading timeline..." : "No timeline entries found"}
            </p>
          </div>
        ) : (
          filteredTimeline.map((entry) => (
            <div
              key={entry.id}
              className={cn(
                "p-3 rounded-lg border transition hover:border-[var(--border)] cursor-pointer",
                getStatusColor(entry.status)
              )}
              onClick={() => {
                if (entry.details) {
                  // In real implementation, this would fetch the full entry
                  onSelectEntry?.({
                    id: entry.id,
                    createdAt: entry.timestamp,
                    uiMode: entry.type,
                    backendMode: "config",
                    question: entry.details.question || "",
                    response: {},
                    status: entry.status,
                    summary: entry.message,
                    trace: { trace_id: entry.details.traceId },
                  });
                }
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  {/* Icon */}
                  <div className="mt-0.5">
                    {getStatusIcon(entry.status)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-white">
                        {entry.type.toUpperCase()}
                      </span>
                      <span className="text-xs " style={{color: "var(--muted-foreground)"}}>·</span>
                      <span className="text-xs " style={{color: "var(--muted-foreground)"}}>
                        {formatRelativeTime(entry.timestamp)}
                      </span>
                    </div>

                    <p className="text-sm  mb-2 truncate" style={{color: "var(--foreground-secondary)"}}>
                      {entry.message}
                    </p>

                    {/* Additional Info */}
                    {entry.details?.question && (
                      <p className="text-xs  mb-1 truncate" style={{color: "var(--muted-foreground)"}}>
                        Question: {entry.details.question}
                      </p>
                    )}

                    <div className="flex items-center gap-3 text-xs">
                      {entry.duration && (
                        <span className={cn("font-mono", getDurationColor(entry.duration))}>
                          {entry.duration}ms
                        </span>
                      )}
                      {entry.details?.route && (
                        <span className="" style={{color: "var(--muted-foreground)"}}>
                          Route: {entry.details.route}
                        </span>
                      )}
                      {entry.details?.traceId && (
                        <span className="font-mono " style={{color: "var(--muted-foreground)"}}>
                          ID: {entry.details.traceId.slice(0, 8)}...
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="flex items-center gap-1">
                  {getTypeIcon(entry.type)}
                  {getStatusIcon(entry.status)}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Summary Footer */}
      <div className="p-3 border-t  /30" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
        <div className="flex items-center justify-between text-xs " style={{color: "var(--muted-foreground)"}}>
          <span>
            Showing {filteredTimeline.length} of {timeline.length} entries
          </span>
          <span>
            Last updated: {formatRelativeTime(new Date().toISOString())}
          </span>
        </div>
      </div>
    </div>
  );
}
