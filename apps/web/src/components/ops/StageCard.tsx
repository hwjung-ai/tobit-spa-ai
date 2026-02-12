"use client";

import { useState } from "react";
import {
  PlayCircle,
  RotateCcw,
  Clock,
  CheckCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  Settings,
  MoreVertical,
  Copy,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface StageInputOutput {
  stageId: string;
  stageName: string;
  stageType: "planner" | "executor" | "validator" | "renderer";
  status: "pending" | "running" | "success" | "error" | "skipped";
  duration?: number;
  startTime?: string;
  endTime?: string;
  input?: unknown;
  output?: unknown;
  error?: string;
  metrics?: {
    inputSize?: number;
    outputSize?: number;
    memoryUsage?: number;
    cpuUsage?: number;
  };
}

interface StageCardProps {
  stage: StageInputOutput;
  showDetails?: boolean;
  onStageAction?: (stageId: string, action: string) => void;
  className?: string;
}

const STAGE_COLORS = {
  planner: {
    bg: "bg-sky-500/10",
    border: "border-sky-400/30",
    text: "text-sky-400",
    icon: <PlayCircle className="h-4 w-4 text-sky-400" />,
  },
  executor: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-400/30",
    text: "text-emerald-400",
    icon: <PlayCircle className="h-4 w-4 text-emerald-400" />,
  },
  validator: {
    bg: "bg-amber-500/10",
    border: "border-amber-400/30",
    text: "text-amber-400",
    icon: <CheckCircle className="h-4 w-4 text-amber-400" />,
  },
  renderer: {
    bg: "bg-purple-500/10",
    border: "border-purple-400/30",
    text: "text-purple-400",
    icon: <Eye className="h-4 w-4 text-purple-400" />,
  },
};

const STATUS_COLORS = {
  pending: "text-[var(--muted-foreground)]",
  running: "text-sky-400 animate-pulse",
  success: "text-emerald-400",
  error: "text-rose-400",
  skipped: "text-[var(--muted-foreground)]",
};

const STATUS_ICONS = {
  pending: <Clock className="h-3 w-3" />,
  running: <PlayCircle className="h-3 w-3" />,
  success: <CheckCircle className="h-3 w-3" />,
  error: <AlertTriangle className="h-3 w-3" />,
  skipped: <Clock className="h-3 w-3" />,
};

export default function StageCard({
  stage,
  showDetails = false,
  onStageAction,
  className
}: StageCardProps) {
  const [expanded, setExpanded] = useState(showDetails);
  const [showInput, setShowInput] = useState(true);
  const [showOutput, setShowOutput] = useState(false);

  const stageColors = STAGE_COLORS[stage.stageType];
  const statusColor = STATUS_COLORS[stage.status];
  const statusIcon = STATUS_ICONS[stage.status];

  const formatDuration = (duration?: number) => {
    if (!duration) return "N/A";
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(2)}s`;
  };

  const formatJsonPreview = (data: unknown, maxLength = 200) => {
    if (!data) return "null";
    const str = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    return str.length > maxLength ? str.slice(0, maxLength) + "..." : str;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleAction = (action: string) => {
    onStageAction?.(stage.stageId, action);
  };

  return (
    <div className={cn(
      "rounded-2xl border overflow-hidden transition-all",
      stageColors.border,
      stageColors.bg,
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b " style={{borderColor: "var(--border)"}}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn("p-1.5 rounded-lg", stageColors.bg)}>
              {stageColors.icon}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">
                {stage.stageName}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <span className={cn("text-xs", stageColors.text)}>
                  {stage.stageType.toUpperCase()}
                </span>
                <span className="" style={{color: "var(--muted-foreground)"}}>·</span>
                <div className="flex items-center gap-1">
                  {statusIcon}
                  <span className={cn("text-xs", statusColor)}>
                    {stage.status}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {stage.duration && (
              <span className="text-xs  font-mono" style={{color: "var(--muted-foreground)"}}>
                {formatDuration(stage.duration)}
              </span>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className=" hover:text-white transition" style={{color: "var(--muted-foreground)"}}
            >
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
            <button
              onClick={() => handleAction("more")}
              className=" hover:text-white transition" style={{color: "var(--muted-foreground)"}}
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Timeline */}
          <div className="flex items-center justify-between text-xs " style={{color: "var(--muted-foreground)"}}>
            <div className="flex items-center gap-2">
              {stage.startTime && (
                <>
                  <span>Started: {new Date(stage.startTime).toLocaleTimeString()}</span>
                  {stage.endTime && (
                    <>
                      <span>·</span>
                      <span>Ended: {new Date(stage.endTime).toLocaleTimeString()}</span>
                    </>
                  )}
                </>
              )}
            </div>
            {stage.metrics && (
              <div className="flex gap-3">
                {stage.metrics.inputSize !== undefined && (
                  <span>In: {stage.metrics.inputSize}</span>
                )}
                {stage.metrics.outputSize !== undefined && (
                  <span>Out: {stage.metrics.outputSize}</span>
                )}
              </div>
            )}
          </div>

          {/* Error Message */}
          {stage.status === "error" && stage.error && (
            <div className="p-3 rounded-lg border border-rose-400/30 bg-rose-400/5">
              <p className="text-sm text-rose-400 font-medium">Error</p>
              <p className="text-xs text-rose-300 mt-1">{stage.error}</p>
            </div>
          )}

          {/* Input/Output Toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowInput(!showInput)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition",
                showInput
                  ? "bg-sky-500/10 text-sky-400 border border-sky-400/30"
                  : "bg-[var(--surface-elevated)] text-[var(--muted-foreground)] hover:bg-[var(--surface-elevated)]"
              )}
            >
              {showInput ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
              Input
            </button>
            <button
              onClick={() => setShowOutput(!showOutput)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition",
                showOutput
                  ? "bg-purple-500/10 text-purple-400 border border-purple-400/30"
                  : "bg-[var(--surface-elevated)] text-[var(--muted-foreground)] hover:bg-[var(--surface-elevated)]"
              )}
            >
              {showOutput ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
              Output
            </button>
          </div>

          {/* Input Data */}
          {showInput && stage.input && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium " style={{color: "var(--foreground-secondary)"}}>Input</p>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(stage.input, null, 2))}
                  className="text-xs  hover: transition" style={{color: "var(--foreground-secondary)"}}
                >
                  <Copy className="h-3 w-3" />
                </button>
              </div>
              <pre className="p-3 rounded-lg  border  text-xs  overflow-x-auto max-h-60" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-overlay)"}}>
                {formatJsonPreview(stage.input)}
              </pre>
            </div>
          )}

          {/* Output Data */}
          {showOutput && stage.output && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium " style={{color: "var(--foreground-secondary)"}}>Output</p>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(stage.output, null, 2))}
                  className="text-xs  hover: transition" style={{color: "var(--foreground-secondary)"}}
                >
                  <Copy className="h-3 w-3" />
                </button>
              </div>
              <pre className="p-3 rounded-lg  border  text-xs  overflow-x-auto max-h-60" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-overlay)"}}>
                {formatJsonPreview(stage.output)}
              </pre>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t " style={{borderColor: "var(--border)"}}>
            <button
              onClick={() => handleAction("rerun")}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-400/30 transition hover:bg-emerald-500/20"
            >
              <RotateCcw className="h-3 w-3" />
              Rerun
            </button>
            <button
              onClick={() => handleAction("debug")}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs   border  transition hover:" style={{borderColor: "var(--border)", color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}
            >
              <Settings className="h-3 w-3" />
              Debug
            </button>
            <button
              onClick={() => handleAction("delete")}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs   border  transition hover:" style={{borderColor: "var(--border)", color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}
            >
              <Trash2 className="h-3 w-3" />
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Stage Card Container for multiple stages
export function StageCardContainer({
  stages,
  maxStages = 5,
  className
}: {
  stages: StageInputOutput[];
  maxStages?: number;
  className?: string;
}) {
  const visibleStages = stages.slice(0, maxStages);
  const hasMore = stages.length > maxStages;

  return (
    <div className={cn("space-y-3", className)}>
      {visibleStages.map((stage, index) => (
        <StageCard
          key={stage.stageId}
          stage={stage}
          showDetails={index === 0} // Only show details for the first stage
        />
      ))}

      {hasMore && (
        <div className="text-center py-3">
          <button className="text-sm  hover: transition" style={{color: "var(--foreground-secondary)"}}>
            +{stages.length - maxStages} more stages
          </button>
        </div>
      )}
    </div>
  );
}