"use client";

import { useState } from "react";
import {
  Clock,
  AlertTriangle,
  X,
  Bug,
  Lightbulb,
  TrendingUp,
  CheckCircle,
  ChevronDown,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface ReplanEvent {
  id?: string;
  event_type: string;
  stage_name: string;
  trigger: {
    trigger_type: string;
    reason: string;
    severity: string;
    stage_name: string;
  };
  patch: {
    before: unknown;
    after: unknown;
  };
  timestamp: string;
  decision_metadata: {
    trace_id: string;
    should_replan: boolean;
    evaluation_time: number;
  } | null;
}

interface ReplanTimelineProps {
  className?: string;
  events: ReplanEvent[];
  traceId?: string;
  triggerFilter?: string[];
  onEventSelect?: (event: ReplanEvent) => void;
}

const TRIGGER_CONFIG = {
  error: {
    icon: AlertTriangle,
    color: "bg-red-500/10 border-red-400/30 text-red-400",
    label: "Error",
    priority: 1
  },
  timeout: {
    icon: Clock,
    color: "bg-amber-500/10 border-amber-400/30 text-amber-400",
    label: "Timeout",
    priority: 2
  },
  policy_violation: {
    icon: Bug,
    color: "bg-purple-500/10 border-purple-400/30 text-purple-400",
    label: "Policy",
    priority: 3
  },
  quality_threshold: {
    icon: TrendingUp,
    color: "bg-emerald-500/10 border-emerald-400/30 text-emerald-400",
    label: "Quality",
    priority: 4
  },
  user_initiated: {
    icon: Lightbulb,
    color: "bg-blue-500/10 border-blue-400/30 text-blue-400",
    label: "User",
    priority: 5
  }
};

const SEVERITY_COLORS = {
  critical: "text-rose-400",
  high: "text-amber-400",
  medium: "text-blue-400",
  low: "text-emerald-400",
};

const StageColors = {
  route_plan: "bg-blue-500/10 border-blue-400/30",
  validate: "bg-emerald-500/10 border-emerald-400/30",
  execute: "bg-amber-500/10 border-amber-400/30",
  compose: "bg-purple-500/10 border-purple-400/30",
  present: "bg-rose-500/10 border-rose-400/30",
};

const PatchDiffViewer = ({ patch }: { patch: unknown }) => {
  const [expanded, setExpanded] = useState(false);

  if (!patch || typeof patch !== 'object') {
    return null;
  }

  const patchObj = patch as { before?: unknown; after?: unknown };

  if (!patchObj.before && !patchObj.after) {
    return null;
  }

  const renderJson = (data: unknown, title: string) => (
    <div className="bg-slate-900/50 border border-slate-700 rounded p-3 text-xs font-mono text-slate-300">
      <div className="text-slate-400 mb-1">{title}</div>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
      >
        <Eye className="h-3 w-3" />
        {expanded ? "Hide" : "Show"} Patch Diff
      </button>

      {expanded && (
        <div className="mt-2 space-y-3">
          {patchObj.before && renderJson(patchObj.before, "Before")}
          {patchObj.after && renderJson(patchObj.after, "After")}
        </div>
      )}
    </div>
  );
};

export default function ReplanTimeline({
  className,
  events = [],
  traceId,
  triggerFilter = [],
  onEventSelect,
}: ReplanTimelineProps) {
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [filteredTriggers, setFilteredTriggers] = useState<Set<string>>(
    new Set(triggerFilter)
  );

  const sortedEvents = [...events].sort((a, b) =>
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  const handleTriggerFilter = (trigger: string) => {
    const newSet = new Set(filteredTriggers);
    if (newSet.has(trigger)) {
      newSet.delete(trigger);
    } else {
      newSet.add(trigger);
    }
    setFilteredTriggers(newSet);
  };

  const filteredEvents = sortedEvents.filter(event =>
    filteredTriggers.size === 0 || filteredTriggers.has(event.trigger.trigger_type)
  );

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const toggleEvent = (event: ReplanEvent, index: number) => {
    const eventId = event.id ?? `${event.stage_name}-${event.timestamp}-${index}`;
    if (expandedEventId === eventId) {
      setExpandedEventId(null);
    } else {
      setExpandedEventId(eventId);
      onEventSelect?.(event);
    }
  };

  return (
    <div className={cn("flex flex-col rounded-2xl border border-slate-800 bg-slate-950/60", className)}>
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              Replan Events
            </h2>
            {traceId && (
              <p className="text-xs text-slate-400 mt-1 break-all">
                Trace ID: {traceId}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="text-xs text-slate-400">
              {filteredEvents.length} event{filteredEvents.length !== 1 ? "s" : ""}
            </div>
          </div>
        </div>

        {/* Trigger Filters */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(TRIGGER_CONFIG).map(([triggerType, config]) => {
            const Icon = config.icon;
            const isActive = filteredTriggers.has(triggerType);

            return (
              <button
                key={triggerType}
                onClick={() => handleTriggerFilter(triggerType)}
                className={cn(
                  "flex items-center gap-1 px-2 py-1 rounded text-xs transition",
                  isActive
                    ? config.color
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                )}
              >
                <Icon className="h-3 w-3" />
                {config.label}
                {isActive && (
                  <X className="h-3 w-3" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Events List - Inline Accordion Style */}
      <div className="p-4 space-y-2 max-h-[600px] overflow-auto">
        {filteredEvents.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-slate-500">
            <div className="text-center">
              <Clock className="h-6 w-6 mx-auto mb-1 opacity-50" />
              <p className="text-xs">No replan events</p>
            </div>
          </div>
        ) : (
          filteredEvents.map((event, index) => {
            const triggerConfig = TRIGGER_CONFIG[event.trigger.trigger_type as keyof typeof TRIGGER_CONFIG] || TRIGGER_CONFIG.error;
            const Icon = triggerConfig.icon;
            const eventId = event.id ?? `${event.stage_name}-${event.timestamp}-${index}`;
            const isExpanded = expandedEventId === eventId;
            const isApproved = event.decision_metadata?.should_replan ?? false;

            return (
              <div
                key={eventId}
                className={cn(
                  "rounded-lg border transition-all",
                  triggerConfig.color,
                  isApproved ? "border-slate-600" : "border-slate-700/50"
                )}
              >
                {/* Summary Bar - Always Visible */}
                <button
                  onClick={() => toggleEvent(event, index)}
                  className="w-full p-3 flex items-center justify-between text-left hover:bg-white/5 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    <span className="text-sm font-medium text-white">{triggerConfig.label}</span>
                    <span className="text-slate-500 text-xs">{event.stage_name}</span>
                    <span className={cn(
                      "px-1.5 py-0.5 rounded text-xs font-medium",
                      SEVERITY_COLORS[event.trigger.severity as keyof typeof SEVERITY_COLORS]
                    )}>
                      {event.trigger.severity}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {isApproved ? (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-400/30 text-xs text-emerald-400">
                        <CheckCircle className="h-3 w-3" />
                        Approved
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-rose-500/10 border border-rose-400/30 text-xs text-rose-400">
                        <X className="h-3 w-3" />
                        Denied
                      </span>
                    )}
                    <span className="text-xs text-slate-400">{formatTime(event.timestamp)}</span>
                    <ChevronDown className={cn(
                      "h-4 w-4 text-slate-400 transition-transform",
                      isExpanded && "rotate-180"
                    )} />
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-3 pb-3 pt-2 space-y-3 border-t border-slate-700/50 mt-2">
                    {/* Trigger Reason */}
                    <div>
                      <p className="text-xs text-slate-500 mb-1">Reason</p>
                      <p className="text-xs text-slate-200">{event.trigger.reason}</p>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-slate-900/50 rounded p-2">
                        <p className="text-slate-500">Type</p>
                        <p className="text-slate-200">{event.event_type}</p>
                      </div>
                      <div className="bg-slate-900/50 rounded p-2">
                        <p className="text-slate-500">Stage</p>
                        <p className="text-slate-200">{event.stage_name}</p>
                      </div>
                      {event.decision_metadata && (
                        <>
                          <div className="bg-slate-900/50 rounded p-2">
                            <p className="text-slate-500">Decision</p>
                            <p className={cn(
                              isApproved ? "text-emerald-400" : "text-rose-400"
                            )}>
                              {isApproved ? "Approved" : "Denied"}
                            </p>
                          </div>
                          <div className="bg-slate-900/50 rounded p-2">
                            <p className="text-slate-500">Eval Time</p>
                            <p className="text-slate-200">
                              {((event.decision_metadata.evaluation_time ?? 0) * 1000).toFixed(2)}ms
                            </p>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Timestamp */}
                    <div className="text-xs text-slate-400">
                      {new Date(event.timestamp).toLocaleString()}
                    </div>

                    {/* Patch Diff */}
                    {event.patch && (
                      <PatchDiffViewer patch={event.patch} />
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
