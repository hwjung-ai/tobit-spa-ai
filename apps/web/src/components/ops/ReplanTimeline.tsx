"use client";

import { useState } from "react";
import {
  Clock,
  AlertTriangle,
  RefreshCw,
  X,
  Bug,
  Lightbulb,
  TrendingUp,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ReplanEvent {
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
  };
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

  if (!patch || (!patch.before && !patch.after)) {
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
          {patch.before && renderJson(patch.before, "Before")}
          {patch.after && renderJson(patch.after, "After")}
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
  const [selectedEvent, setSelectedEvent] = useState<ReplanEvent | null>(null);
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

  return (
    <div className={cn("flex flex-col h-full rounded-2xl border border-slate-800 bg-slate-950/60", className)}>
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              Replan Event Timeline
            </h2>
            {traceId && (
              <p className="text-xs text-slate-400 mt-1">
                Trace ID: {traceId.slice(0, 8)}...
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

      {/* Timeline */}
      <div className="flex-1 overflow-auto p-4">
        {filteredEvents.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-slate-500">
            <div className="text-center">
              <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No replan events found</p>
            </div>
          </div>
        ) : (
          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-700"></div>

            {/* Events */}
            <div className="space-y-4">
              {filteredEvents.map((event, index) => {
                const triggerConfig = TRIGGER_CONFIG[event.trigger.trigger_type] || TRIGGER_CONFIG.error;
                const Icon = triggerConfig.icon;
                const stageColor = StageColors[event.stage_name as keyof typeof StageColors] || StageColors.route_plan;
                const eventId = event.id ?? `${event.stage_name}-${event.timestamp}-${index}`;
                const isSelected =
                  selectedEvent &&
                  (selectedEvent.id ?? `${selectedEvent.stage_name}-${selectedEvent.timestamp}`) ===
                    `${event.stage_name}-${event.timestamp}`;

                return (
                  <div
                    key={eventId}
                    className={cn(
                      "relative cursor-pointer transition-all hover:scale-[1.02]",
                      isSelected && "ring-2 ring-blue-400"
                    )}
                    onClick={() => {
                      setSelectedEvent(event);
                      onEventSelect?.(event);
                    }}
                  >
                    {/* Timeline Dot */}
                    <div className="absolute left-2 top-4 transform -translate-x-1/2">
                      <div className={cn(
                        "w-3 h-3 rounded-full border-2",
                        triggerConfig.color,
                        event.decision_metadata.should_replan ? "ring-2 ring-white" : "opacity-50"
                      )}>
                        <Icon className="h-2 w-2 mx-auto" />
                      </div>
                    </div>

                    {/* Event Card */}
                    <div className={cn(
                      "ml-8 p-3 rounded-lg border transition-all",
                      triggerConfig.color,
                      event.decision_metadata.should_replan ? "border-slate-600" : "border-slate-700/50",
                      selectedEvent?.id === event.id && "ring-1 ring-white/10"
                    )}>
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4" />
                            <h3 className="text-sm font-medium text-white">
                              {triggerConfig.label} Event
                            </h3>
                            <span className={cn(
                              "text-xs px-1.5 py-0.5 rounded-full",
                              stageColor,
                              "font-medium"
                            )}>
                              {event.stage_name.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                            <span>{formatTime(event.timestamp)}</span>
                            <span className={cn(
                              "flex items-center gap-1",
                              SEVERITY_COLORS[event.trigger.severity as keyof typeof SEVERITY_COLORS]
                            )}>
                              {event.trigger.severity} severity
                            </span>
                          </div>
                        </div>

                        {event.decision_metadata.should_replan && (
                          <div className="flex items-center gap-1 px-2 py-1 rounded bg-green-500/10 border border-green-400/30">
                            <RefreshCw className="h-3 w-3 text-emerald-400" />
                            <span className="text-xs text-emerald-400">Replanned</span>
                          </div>
                        )}
                      </div>

                      {/* Trigger Reason */}
                      <div className="mt-2">
                        <p className="text-xs text-slate-300">
                          <strong>Reason:</strong> {event.trigger.reason}
                        </p>
                      </div>

                      {/* Decision Metadata */}
                      <div className="mt-2 p-2 rounded bg-slate-900/50 text-xs">
                        <p>Decision: {event.decision_metadata.should_replan ? "Approved" : "Denied"}</p>
                        <p>Evaluation time: {(event.decision_metadata.evaluation_time * 1000).toFixed(2)}ms</p>
                      </div>

                      {/* Patch Diff Toggle */}
                      {event.patch && (
                        <PatchDiffViewer patch={event.patch} />
                      )}
                    </div>

                    {/* Connection Line */}
                    {index < filteredEvents.length - 1 && (
                      <div className="absolute left-3.5 top-12 w-px h-6 bg-slate-700"></div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Selected Event Details */}
      {selectedEvent && (
        <div className="p-4 border-t border-slate-800 bg-slate-900/30">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Event Details</h3>
            <button
              onClick={() => setSelectedEvent(null)}
              className="text-slate-400 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-slate-400">Event Type</p>
                <p className="font-medium text-white">
                  {selectedEvent.event_type}
                </p>
              </div>
              <div>
                <p className="text-slate-400">Stage</p>
                <p className="font-medium text-white capitalize">
                  {selectedEvent.stage_name.replace(/_/g, ' ')}
                </p>
              </div>
              <div>
                <p className="text-slate-400">Trigger Type</p>
                <p className="font-medium text-white">
                  {selectedEvent.trigger.trigger_type}
                </p>
              </div>
              <div>
                <p className="text-slate-400">Decision</p>
                <p className={cn(
                  "font-medium",
                  selectedEvent.decision_metadata.should_replan ? "text-emerald-400" : "text-rose-400"
                )}>
                  {selectedEvent.decision_metadata.should_replan ? "Approved" : "Denied"}
                </p>
              </div>
            </div>

            <div>
              <p className="text-slate-400 mb-1">Trigger Reason</p>
              <p className="text-sm text-slate-300">
                {selectedEvent.trigger.reason}
              </p>
            </div>

            <div>
              <p className="text-slate-400 mb-1">Timestamp</p>
              <p className="text-sm text-slate-300">
                {new Date(selectedEvent.timestamp).toLocaleString()}
              </p>
            </div>

            <div>
              <p className="text-slate-400 mb-1">Patch Information</p>
              <div className="bg-slate-800/50 rounded p-2 text-slate-300 text-xs">
                <p>Changes detected at stage: {selectedEvent.stage_name}</p>
                {selectedEvent.patch && (
                  <div className="mt-1">
                    <p>Before: {Object.keys(selectedEvent.patch.before || {}).length} properties</p>
                    <p>After: {Object.keys(selectedEvent.patch.after || {}).length} properties</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
