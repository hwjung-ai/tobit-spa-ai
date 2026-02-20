"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";

/**
 * OPS Progress Stage Types
 */
export type OpsProgressStage =
  | "init"
  | "resolving"
  | "planning"
  | "validating"
  | "executing"
  | "composing"
  | "presenting"
  | "complete"
  | "error";

/**
 * Progress event from SSE
 */
export interface OpsProgressEvent {
  stage: OpsProgressStage;
  message: string;
  elapsed_ms: number;
  details?: Record<string, unknown>;
  completed_stages?: string[];
}

/**
 * Tool call event from SSE
 */
export interface OpsToolCallEvent {
  tool_type: string;
  tool_name: string;
  display_name: string;
  status: "started" | "completed" | "error";
  elapsed_ms: number;
  message?: string;
  result_summary?: string;
}

/**
 * Block event from SSE
 */
export interface OpsBlockEvent {
  block: Record<string, unknown>;
  index: number;
  total: number;
  elapsed_ms: number;
}

/**
 * Complete event from SSE
 */
export interface OpsCompleteEvent {
  answer: string;
  blocks: Record<string, unknown>[];
  meta: Record<string, unknown>;
  trace: Record<string, unknown>;
  next_actions: Record<string, unknown>[];
  timing: {
    total_ms: number;
  };
  completed_stages?: string[];
}

/**
 * Error event from SSE
 */
export interface OpsErrorEvent {
  message: string;
  stage: string;
  elapsed_ms: number;
}

/**
 * Stage display configuration
 */
const STAGE_CONFIG: Record<
  OpsProgressStage,
  { label: string; icon: string; description: string }
> = {
  init: {
    label: "초기화",
    icon: "⚙️",
    description: "질의 처리를 시작합니다",
  },
  resolving: {
    label: "질의 분석",
    icon: "🔍",
    description: "질문을 분석하고 있습니다",
  },
  planning: {
    label: "계획 수립",
    icon: "📋",
    description: "실행 계획을 세우고 있습니다",
  },
  validating: {
    label: "계획 검증",
    icon: "✓",
    description: "계획을 검증하고 있습니다",
  },
  executing: {
    label: "데이터 조회",
    icon: "📊",
    description: "데이터를 조회하고 분석합니다",
  },
  composing: {
    label: "결과 종합",
    icon: "🔄",
    description: "결과를 종합하고 있습니다",
  },
  presenting: {
    label: "응답 생성",
    icon: "✨",
    description: "응답을 생성하고 있습니다",
  },
  complete: {
    label: "완료",
    icon: "✅",
    description: "처리가 완료되었습니다",
  },
  error: {
    label: "오류",
    icon: "❌",
    description: "오류가 발생했습니다",
  },
};

/**
 * Stage order for progress bar
 */
const STAGE_ORDER: OpsProgressStage[] = [
  "init",
  "resolving",
  "planning",
  "validating",
  "executing",
  "composing",
  "presenting",
  "complete",
];

interface OpsProgressIndicatorProps {
  currentStage: OpsProgressStage;
  message?: string;
  elapsedMs?: number;
  completedStages?: string[];
  toolCalls?: OpsToolCallEvent[];
  className?: string;
}

/**
 * OPS Progress Indicator Component
 *
 * ChatGPT-style progress indicator showing current execution stage
 * with animated status updates.
 */
export function OpsProgressIndicator({
  currentStage,
  message,
  elapsedMs,
  completedStages = [],
  toolCalls = [],
  className,
}: OpsProgressIndicatorProps) {
  const config = STAGE_CONFIG[currentStage];
  const currentIndex = STAGE_ORDER.indexOf(currentStage);
  const isError = currentStage === "error";
  const isComplete = currentStage === "complete";

  // Calculate progress percentage
  const progressPercent = isComplete
    ? 100
    : isError
      ? 0
      : Math.min(100, Math.round((currentIndex / (STAGE_ORDER.length - 1)) * 100));

  return (
    <div
      className={cn(
        "rounded-2xl border p-4 transition-all duration-300",
        isError
          ? "border-rose-500/50 bg-rose-500/10"
          : isComplete
            ? "border-emerald-500/50 bg-emerald-500/10"
            : "border-sky-500/30 bg-sky-500/5",
        className
      )}
    >
      {/* Header with icon and stage name */}
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-full text-xl",
            isError
              ? "bg-rose-500/20"
              : isComplete
                ? "bg-emerald-500/20"
                : "bg-sky-500/20"
          )}
        >
          {isError || isComplete ? (
            config.icon
          ) : (
            <span className="animate-pulse">{config.icon}</span>
          )}
        </div>

        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h4
              className={cn(
                "font-semibold",
                isError
                  ? "text-rose-400"
                  : isComplete
                    ? "text-emerald-400"
                    : "text-sky-400"
              )}
            >
              {config.label}
            </h4>
            {elapsedMs !== undefined && (
              <span className="text-xs text-muted-foreground">
                {elapsedMs > 1000
                  ? `${(elapsedMs / 1000).toFixed(1)}s`
                  : `${elapsedMs}ms`}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {message || config.description}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      {!isError && (
        <div className="mt-3">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-elevated">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500 ease-out",
                isComplete ? "bg-emerald-500" : "bg-sky-500"
              )}
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Stage indicators */}
          <div className="mt-2 flex justify-between">
            {STAGE_ORDER.slice(0, -1).map((stage, index) => {
              const stageConfig = STAGE_CONFIG[stage];
              const isCompleted = completedStages.includes(stage);
              const isCurrent = stage === currentStage;
              const isPast = index < currentIndex;

              return (
                <div
                  key={stage}
                  className={cn(
                    "flex flex-col items-center gap-0.5",
                    index === 0 ? "items-start" : index === STAGE_ORDER.length - 2 ? "items-end" : ""
                  )}
                  style={{ width: `${100 / (STAGE_ORDER.length - 1)}%` }}
                >
                  <div
                    className={cn(
                      "text-sm transition-all",
                      isCompleted || isPast
                        ? "text-emerald-400"
                        : isCurrent
                          ? "text-sky-400"
                          : "text-muted-foreground/50"
                    )}
                  >
                    {isCompleted || isPast ? "✓" : isCurrent ? stageConfig.icon : "○"}
                  </div>
                  <span
                    className={cn(
                      "text-[10px] transition-all",
                      isCompleted || isPast
                        ? "text-emerald-400"
                        : isCurrent
                          ? "text-sky-400 font-medium"
                          : "text-muted-foreground/40"
                    )}
                  >
                    {stageConfig.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tool calls list */}
      {toolCalls.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-border pt-3">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">
            실행된 도구
          </p>
          {toolCalls.map((tool, index) => (
            <div
              key={`${tool.tool_name}-${index}`}
              className="flex items-center gap-2 text-sm"
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  tool.status === "completed"
                    ? "bg-emerald-400"
                    : tool.status === "error"
                      ? "bg-rose-400"
                      : "bg-sky-400 animate-pulse"
                )}
              />
              <span className="text-foreground">{tool.display_name}</span>
              {tool.elapsed_ms > 0 && (
                <span className="text-xs text-muted-foreground">
                  {tool.elapsed_ms}ms
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Hook for managing OPS streaming progress
 */
export function useOpsStreamProgress() {
  const [currentStage, setCurrentStage] =
    useState<OpsProgressStage>("init");
  const [message, setMessage] = useState<string>("");
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const [completedStages, setCompletedStages] = useState<string[]>([]);
  const [toolCalls, setToolCalls] = useState<OpsToolCallEvent[]>([]);
  const [blocks, setBlocks] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [result, setResult] = useState<OpsCompleteEvent | null>(null);

  const reset = useCallback(() => {
    setCurrentStage("init");
    setMessage("");
    setElapsedMs(0);
    setCompletedStages([]);
    setToolCalls([]);
    setBlocks([]);
    setError(null);
    setIsComplete(false);
    setResult(null);
  }, []);

  const handleProgressEvent = useCallback(
    (event: OpsProgressEvent) => {
      setCurrentStage(event.stage);
      setMessage(event.message);
      setElapsedMs(event.elapsed_ms);
      if (event.completed_stages) {
        setCompletedStages(event.completed_stages);
      }
    },
    []
  );

  const handleToolCallEvent = useCallback((event: OpsToolCallEvent) => {
    setToolCalls((prev) => [...prev, event]);
  }, []);

  const handleBlockEvent = useCallback((event: OpsBlockEvent) => {
    setBlocks((prev) => [...prev, event.block]);
  }, []);

  const handleCompleteEvent = useCallback((event: OpsCompleteEvent) => {
    setIsComplete(true);
    setCurrentStage("complete");
    setResult(event);
    setElapsedMs(event.timing.total_ms);
  }, []);

  const handleErrorEvent = useCallback((event: OpsErrorEvent) => {
    setCurrentStage("error");
    setError(event.message);
  }, []);

  return {
    currentStage,
    message,
    elapsedMs,
    completedStages,
    toolCalls,
    blocks,
    error,
    isComplete,
    result,
    reset,
    handleProgressEvent,
    handleToolCallEvent,
    handleBlockEvent,
    handleCompleteEvent,
    handleErrorEvent,
  };
}
