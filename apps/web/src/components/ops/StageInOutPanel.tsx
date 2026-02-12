"use client";

import { useState } from "react";
import {
  ChevronDown,
  Clock,
  AlertTriangle,
  CheckCircle,
  Eye,
  Copy,
  RotateCcw,
  Maximize2,
  Minimize2
} from "lucide-react";
import { cn } from "@/lib/utils";

interface StageInOutData {
  stage: string;
  input?: unknown;
  output?: unknown;
  duration_ms?: number;
  status?: string;
  timestamp?: string;
  diagnostics?: {
    status: string;
    warnings?: string[];
    errors?: string[];
    empty_flags: Record<string, boolean>;
    counts: Record<string, number>;
  };
  references?: Array<{
    ref_type: string;
    name: string;
    engine?: string | null;
    statement?: string | null;
    params?: Record<string, unknown> | null;
    row_count?: number | null;
    latency_ms?: number | null;
    source_id?: string | null;
  }> | null;
}

interface StageInOutPanelProps {
  className?: string;
  traceId?: string;
  stages: StageInOutData[];
  expandedStages?: string[];
  onStageToggle?: (stage: string) => void;
  compact?: boolean;
}

const STAGE_COLORS = {
  route_plan: {
    bg: "bg-blue-500/10",
    border: "border-blue-400/30",
    text: "text-blue-400",
  },
  validate: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-400/30",
    text: "text-emerald-400",
  },
  execute: {
    bg: "bg-amber-500/10",
    border: "border-amber-400/30",
    text: "text-amber-400",
  },
  compose: {
    bg: "bg-purple-500/10",
    border: "border-purple-400/30",
    text: "text-purple-400",
  },
  present: {
    bg: "bg-rose-500/10",
    border: "border-rose-400/30",
    text: "text-rose-400",
  },
};

const STATUS_ICONS = {
  ok: CheckCircle,
  warning: AlertTriangle,
  error: AlertTriangle,
};

const STATUS_COLORS = {
  ok: "text-emerald-400",
  warning: "text-amber-400",
  error: "text-rose-400",
};

const JsonViewer = ({ data, title }: { data: unknown; title: string }) => {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedJson = JSON.stringify(data, null, 2);

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-white">{title}</h4>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 rounded hover: transition" style={{ backgroundColor: "var(--surface-elevated)" }}
          >
            {expanded ? <Minimize2 className="h-3 w-3 " style={{ color: "var(--muted-foreground)" }} /> : <Maximize2 className="h-3 w-3 " style={{ color: "var(--muted-foreground)" }} />}
          </button>
          <button
            onClick={handleCopy}
            className="p-1 rounded hover: transition" style={{ backgroundColor: "var(--surface-elevated)" }}
          >
            {copied ? (
              <CheckCircle className="h-3 w-3 text-emerald-400" />
            ) : (
              <Copy className="h-3 w-3 " style={{ color: "var(--muted-foreground)" }} />
            )}
          </button>
        </div>
      </div>

      <div
        className={cn(
          "bg-[var(--surface-overlay)] border border-[var(--border)] rounded overflow-hidden",
          expanded ? "max-h-96" : "max-h-24"
        )}
      >
        <pre className="p-3 text-xs font-mono  overflow-auto" style={{ color: "var(--foreground-secondary)" }}>
          {formattedJson}
        </pre>
      </div>
    </div>
  );
};

export default function StageInOutPanel({
  className,
  traceId,
  stages,
  expandedStages: initialExpandedStages,
  onStageToggle,
  compact = false,
}: StageInOutPanelProps) {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(
    new Set(initialExpandedStages || [])
  );
  const [allExpanded, setAllExpanded] = useState(false);

  const handleStageToggle = (stage: string) => {
    const newSet = new Set(expandedStages);
    if (newSet.has(stage)) {
      newSet.delete(stage);
    } else {
      newSet.add(stage);
    }
    setExpandedStages(newSet);
    onStageToggle?.(stage);
  };

  const toggleAllStages = () => {
    const newExpanded = !allExpanded;
    if (newExpanded) {
      const allStageNames = stages.map(s => s.stage);
      setExpandedStages(new Set(allStageNames));
    } else {
      setExpandedStages(new Set());
    }
    setAllExpanded(newExpanded);
  };

  const getStageConfig = (stageName: string) => {
    return STAGE_COLORS[stageName as keyof typeof STAGE_COLORS] || STAGE_COLORS.route_plan;
  };

  const getStatusConfig = (status?: string) => {
    const Icon = status && STATUS_ICONS[status as keyof typeof STATUS_ICONS] || Eye;
    return {
      Icon,
      color: status && STATUS_COLORS[status as keyof typeof STATUS_COLORS] || "text-[var(--muted-foreground)]",
    };
  };

  return (
    <div className={cn("flex flex-col h-full rounded-2xl border border-[var(--border)] bg-[var(--surface-overlay)]", className)}>
      {/* Header */}
      <div className="p-4 border-b " style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              Stage In/Out Panel
            </h2>
            {traceId && (
              <p className="text-xs  mt-1" style={{ color: "var(--muted-foreground)" }}>
                Trace ID: {traceId.slice(0, 8)}...
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleAllStages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs   border  transition hover:" style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-elevated)" ,  backgroundColor: "var(--surface-elevated)" }}
            >
              {allExpanded ? "Collapse All" : "Expand All"}
              <ChevronDown className={`h-3 w-3 transition-transform ${allExpanded ? 'rotate-180' : ''}`} />
            </button>
            {compact && (
              <button
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs   border  transition hover:" style={{ borderColor: "var(--border)" ,  color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-elevated)" ,  backgroundColor: "var(--surface-elevated)" }}
              >
                <RotateCcw className="h-3 w-3" />
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Stages List */}
      <div className="flex-1 overflow-auto">
        <div className="p-4 space-y-3">
          {stages.map((stage, index) => {
            const stageConfig = getStageConfig(stage.stage);
            const statusConfig = getStatusConfig(stage.diagnostics?.status);
            const isExpanded = expandedStages.has(stage.stage);

            return (
              <div key={stage.stage} className="space-y-2">
                {/* Stage Header */}
                <div
                  onClick={() => handleStageToggle(stage.stage)}
                  className={cn(
                    "p-3 rounded-lg border cursor-pointer transition-all hover:border-[var(--border)]",
                    stageConfig.bg,
                    stageConfig.border,
                    isExpanded && "border-[var(--border)]",
                    expandedStages.has(stage.stage) && "ring-1 ring-white/10"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn("p-1 rounded", stageConfig.bg)}>
                        <Eye className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-white capitalize">
                          {stage.stage.replace(/_/g, ' ')}
                        </h3>
                        {stage.timestamp && (
                          <p className="text-xs " style={{ color: "var(--muted-foreground)" }}>
                            {new Date(stage.timestamp).toLocaleTimeString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className={cn("px-2 py-1 rounded-full text-xs flex items-center gap-1", stageConfig.bg)}>
                        <statusConfig.Icon className="h-3 w-3" />
                        <span className={statusConfig.color}>
                          {stage.diagnostics?.status || stage.status || "unknown"}
                        </span>
                      </div>
                      {stage.duration_ms !== undefined && (
                        <div className="text-xs  flex items-center gap-1" style={{ color: "var(--muted-foreground)" }}>
                          <Clock className="h-3 w-3" />
                          {stage.duration_ms}ms
                        </div>
                      )}
                      <ChevronDown
                        className={cn(
                          "h-4 w-4 text-[var(--muted-foreground)] transition-transform",
                          isExpanded && "rotate-180"
                        )}
                      />
                    </div>
                  </div>

                  {/* Diagnostics Summary */}
                  {stage.diagnostics && (
                    <div className="mt-2 flex items-center gap-4 text-xs">
                      {stage.diagnostics.warnings.length > 0 && (
                        <div className="flex items-center gap-1 text-amber-400">
                          <AlertTriangle className="h-3 w-3" />
                          {stage.diagnostics.warnings.length} warning(s)
                        </div>
                      )}
                      {stage.diagnostics.errors.length > 0 && (
                        <div className="flex items-center gap-1 text-rose-400">
                          <AlertTriangle className="h-3 w-3" />
                          {stage.diagnostics.errors.length} error(s)
                        </div>
                      )}
                      {Object.keys(stage.diagnostics.counts).length > 0 && (
                        <div className="" style={{ color: "var(--muted-foreground)" }}>
                          {Object.entries(stage.diagnostics.counts)
                            .map(([key, value]) => `${key}: ${value}`)
                            .join(", ")}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Stage Details */}
                {isExpanded && (
                  <div className="ml-4 space-y-3 p-3 rounded-lg border  " style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
                    {/* Input Section */}
                    <div>
                      <h4 className="text-xs font-medium  mb-2" style={{ color: "var(--muted-foreground)" }}>INPUT</h4>
                      <JsonViewer
                        data={stage.input || {}}
                        title="Stage Input"
                      />
                    </div>

                    {/* Output Section */}
                    <div>
                      <h4 className="text-xs font-medium  mb-2" style={{ color: "var(--muted-foreground)" }}>OUTPUT</h4>
                      <JsonViewer
                        data={stage.output || {}}
                        title="Stage Output"
                      />
                    </div>

                    {/* References */}
                    {stage.references && stage.references.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium  mb-2" style={{ color: "var(--muted-foreground)" }}>
                          REFERENCES ({stage.references.length})
                        </h4>
                        <div className="space-y-2 max-h-32 overflow-auto">
                          {stage.references.slice(0, 5).map((ref, idx) => (
                            <div
                              key={idx}
                              className="p-2 rounded  border  text-xs font-mono " style={{ borderColor: "var(--border)" ,  color: "var(--foreground-secondary)" ,  backgroundColor: "var(--surface-overlay)" }}
                            >
                              {ref.ref_type || "Reference"}
                            </div>
                          ))}
                          {stage.references.length > 5 && (
                            <div className="text-xs  text-center py-2" style={{ color: "var(--muted-foreground)" }}>
                              +{stage.references.length - 5} more references
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Connection Line */}
                {index < stages.length - 1 && (
                  <div className="flex justify-center py-2">
                    <div className="w-px h-6 " style={{ backgroundColor: "var(--surface-elevated)" }}></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}