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
    color: "bg-sky-500/10 border-sky-400/30 text-sky-400",
    label: "User",
    priority: 5
  }
};

const SEVERITY_COLORS = {
  critical: "text-rose-400",
  high: "text-amber-400",
  medium: "text-sky-400",
  low: "text-emerald-400",
};

const StageColors = {
  route_plan: "bg-sky-500/10 border-sky-400/30",
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
    <div className=" border  rounded p-3 text-xs font-mono " style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-overlay)"}}>
      <div className=" mb-1" style={{color: "var(--muted-foreground)"}}>{title}</div>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1"
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
    <div className={cn("flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--surface-overlay)]", className)}>
      {/* Header */}
      <div className="p-4 border-b " style={{borderColor: "var(--border)"}}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              Replan Events
            </h2>
            {traceId && (
              <p className="text-xs  mt-1 break-all" style={{color: "var(--muted-foreground)"}}>
                Trace ID: {traceId}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="text-xs " style={{color: "var(--muted-foreground)"}}>
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
                    : "bg-[var(--surface-elevated)] text-[var(--muted-foreground)] hover:bg-[var(--surface-elevated)]"
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
          <div className="flex items-center justify-center h-24 " style={{color: "var(--muted-foreground)"}}>
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
                  isApproved ? "border-[var(--border)]" : "border-[var(--border)]"
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
                    <span className=" text-xs" style={{color: "var(--muted-foreground)"}}>{event.stage_name}</span>
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
                    <span className="text-xs " style={{color: "var(--muted-foreground)"}}>{formatTime(event.timestamp)}</span>
                    <ChevronDown className={cn(
                      "h-4 w-4 text-[var(--muted-foreground)] transition-transform",
                      isExpanded && "rotate-180"
                    )} />
                  </div>
                </button>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-3 pb-3 pt-2 space-y-3 border-t /50 mt-2" style={{borderColor: "var(--border)"}}>
                    {/* Trigger Reason */}
                    <div>
                      <p className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Reason</p>
                      <p className="text-xs " style={{color: "var(--foreground-secondary)"}}>{event.trigger.reason}</p>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className=" rounded p-2" style={{backgroundColor: "var(--surface-overlay)"}}>
                        <p className="" style={{color: "var(--muted-foreground)"}}>Type</p>
                        <p className="" style={{color: "var(--foreground-secondary)"}}>{event.event_type}</p>
                      </div>
                      <div className=" rounded p-2" style={{backgroundColor: "var(--surface-overlay)"}}>
                        <p className="" style={{color: "var(--muted-foreground)"}}>Stage</p>
                        <p className="" style={{color: "var(--foreground-secondary)"}}>{event.stage_name}</p>
                      </div>
                      {event.decision_metadata && (
                        <>
                          <div className=" rounded p-2" style={{backgroundColor: "var(--surface-overlay)"}}>
                            <p className="" style={{color: "var(--muted-foreground)"}}>Decision</p>
                            <p className={cn(
                              isApproved ? "text-emerald-400" : "text-rose-400"
                            )}>
                              {isApproved ? "Approved" : "Denied"}
                            </p>
                          </div>
                          <div className=" rounded p-2" style={{backgroundColor: "var(--surface-overlay)"}}>
                            <p className="" style={{color: "var(--muted-foreground)"}}>Eval Time</p>
                            <p className="" style={{color: "var(--foreground-secondary)"}}>
                              {((event.decision_metadata.evaluation_time ?? 0) * 1000).toFixed(2)}ms
                            </p>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Timestamp */}
                    <div className="text-xs " style={{color: "var(--muted-foreground)"}}>
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
