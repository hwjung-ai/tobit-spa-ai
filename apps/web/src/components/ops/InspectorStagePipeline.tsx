"use client";

import { useState, useEffect } from "react";
import { CheckCircle, AlertTriangle, Clock, PlayCircle, PauseCircle, RotateCcw, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

interface StageNode {
  id: string;
  name: string;
  type: "planner" | "executor" | "validator" | "renderer";
  status: "pending" | "running" | "success" | "error" | "skipped";
  startTime?: string;
  endTime?: string;
  duration?: number;
  position: { x: number; y: number };
  connections: string[]; // IDs of next stages
  input?: unknown;
  output?: unknown;
  error?: string;
}

interface StagePipelineProps {
  className?: string;
  traceId?: string;
  stages?: StageNode[];
  onStageSelect?: (stage: StageNode) => void;
  autoPlay?: boolean;
}

const STAGE_CONFIGS = {
  planner: {
    label: "Planner",
    color: "blue",
    icon: <PlayCircle className="h-4 w-4" />,
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-400/30",
    textColor: "text-blue-400",
  },
  executor: {
    label: "Executor",
    color: "emerald",
    icon: <PlayCircle className="h-4 w-4" />,
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-400/30",
    textColor: "text-emerald-400",
  },
  validator: {
    label: "Validator",
    color: "amber",
    icon: <CheckCircle className="h-4 w-4" />,
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-400/30",
    textColor: "text-amber-400",
  },
  renderer: {
    label: "Renderer",
    color: "purple",
    icon: <Eye className="h-4 w-4" />,
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-400/30",
    textColor: "text-purple-400",
  },
};

const STATUS_CONFIGS = {
  pending: {
    color: "slate",
    icon: <Clock className="h-3 w-3" />,
    bgColor: "bg-slate-500/10",
    textColor: "text-slate-400",
  },
  running: {
    color: "blue",
    icon: <PlayCircle className="h-3 w-3 animate-pulse" />,
    bgColor: "bg-blue-500/10",
    textColor: "text-blue-400",
  },
  success: {
    color: "emerald",
    icon: <CheckCircle className="h-3 w-3" />,
    bgColor: "bg-emerald-500/10",
    textColor: "text-emerald-400",
  },
  error: {
    color: "rose",
    icon: <AlertTriangle className="h-3 w-3" />,
    bgColor: "bg-rose-500/10",
    textColor: "text-rose-400",
  },
  skipped: {
    color: "slate",
    icon: <Clock className="h-3 w-3" />,
    bgColor: "bg-slate-500/10",
    textColor: "text-slate-500",
  },
};

// Mock data generator
const generateMockStages = (): StageNode[] => {
  const now = new Date();
  return [
    {
      id: "planner-1",
      name: "CI Planner",
      type: "planner",
      status: "success",
      startTime: new Date(now.getTime() - 5000).toISOString(),
      endTime: new Date(now.getTime() - 3000).toISOString(),
      duration: 2000,
      position: { x: 100, y: 200 },
      connections: ["executor-1"],
    },
    {
      id: "executor-1",
      name: "Stage Executor",
      type: "executor",
      status: "success",
      startTime: new Date(now.getTime() - 3000).toISOString(),
      endTime: new Date(now.getTime() - 1500).toISOString(),
      duration: 1500,
      position: { x: 350, y: 200 },
      connections: ["validator-1"],
    },
    {
      id: "validator-1",
      name: "Validator",
      type: "validator",
      status: "success",
      startTime: new Date(now.getTime() - 1500).toISOString(),
      endTime: new Date(now.getTime() - 500).toISOString(),
      duration: 1000,
      position: { x: 600, y: 200 },
      connections: ["renderer-1"],
    },
    {
      id: "renderer-1",
      name: "Output Renderer",
      type: "renderer",
      status: "success",
      startTime: new Date(now.getTime() - 500).toISOString(),
      endTime: now.toISOString(),
      duration: 500,
      position: { x: 850, y: 200 },
      connections: [],
    },
  ];
};

export default function InspectorStagePipeline({
  className,
  traceId,
  stages,
  onStageSelect,
  autoPlay = false,
}: StagePipelineProps) {
  const [pipelineStages, setPipelineStages] = useState<StageNode[]>(stages || generateMockStages());
  const [selectedStage, setSelectedStage] = useState<StageNode | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentAnimationIndex, setCurrentAnimationIndex] = useState(0);

  useEffect(() => {
    if (autoPlay && pipelineStages.length > 0) {
      const interval = setInterval(() => {
        setCurrentAnimationIndex((prev) => {
          const next = prev + 1;
          if (next >= pipelineStages.length) {
            clearInterval(interval);
            setIsPlaying(false);
            return pipelineStages.length - 1;
          }

          // Update stage status to running
          setPipelineStages((stages) =>
            stages.map((stage, index) =>
              index === next
                ? { ...stage, status: "running" as const }
                : index < next
                ? { ...stage, status: "success" as const }
                : stage
            )
          );

          return next;
        });
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [autoPlay, pipelineStages.length]);

  const handleStageClick = (stage: StageNode) => {
    setSelectedStage(stage);
    onStageSelect?.(stage);
  };

  const resetPipeline = () => {
    setPipelineStages((stages) =>
      stages.map((stage, index) => ({
        ...stage,
        status: index === 0 ? "pending" : "pending",
        startTime: undefined,
        endTime: undefined,
        duration: undefined,
      }))
    );
    setCurrentAnimationIndex(0);
    setIsPlaying(false);
  };

  const playPipeline = () => {
    if (isPlaying) return;
    setIsPlaying(true);
    setCurrentAnimationIndex(0);
  };

  const getStageConfig = (type: StageNode["type"]) => STAGE_CONFIGS[type];
  const getStatusConfig = (status: StageNode["status"]) => STATUS_CONFIGS[status];

  return (
    <div className={cn("flex flex-col h-full rounded-2xl border border-slate-800 bg-slate-950/60", className)}>
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              Stage Pipeline
            </h2>
            {traceId && (
              <p className="text-xs text-slate-400 mt-1">
                Trace ID: {traceId.slice(0, 8)}...
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={resetPipeline}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-slate-800 text-slate-400 border border-slate-700 transition hover:bg-slate-700"
            >
              <RotateCcw className="h-3 w-3" />
              Reset
            </button>
            <button
              onClick={playPipeline}
              disabled={isPlaying}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-400/30 transition hover:bg-emerald-500/20 disabled:opacity-50"
            >
              {isPlaying ? <PauseCircle className="h-3 w-3" /> : <PlayCircle className="h-3 w-3" />}
              Play
            </button>
          </div>
        </div>
      </div>

      {/* Pipeline Visualization */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="relative min-h-[400px]">
          {/* Connection Lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
            {pipelineStages.map((stage) => {
              const stageConfig = getStageConfig(stage.type);
              const stageElement = document.getElementById(`stage-${stage.id}`);
              if (!stageElement || !stage.connections.length) return null;

              const stageRect = stageElement.getBoundingClientRect();
              const containerRect = stageElement.parentElement?.getBoundingClientRect();

              return stage.connections.map((nextId) => {
                const nextStage = pipelineStages.find(s => s.id === nextId);
                if (!nextStage) return null;

                const nextElement = document.getElementById(`stage-${nextId}`);
                if (!nextElement) return null;

                const nextRect = nextElement.getBoundingClientRect();

                // Calculate line coordinates
                const x1 = stageRect.right - containerRect!.left;
                const y1 = stageRect.top + stageRect.height / 2 - containerRect!.top;
                const x2 = nextRect.left - containerRect!.left;
                const y2 = nextRect.top + nextRect.height / 2 - containerRect!.top;

                return (
                  <line
                    key={`${stage.id}-${nextId}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={stage.status === "success" ? "#10b981" : "#475569"}
                    strokeWidth={2}
                    strokeDasharray={stage.status === "success" ? "0" : "4,4"}
                  />
                );
              });
            })}
          </svg>

          {/* Stage Nodes */}
          <div className="relative" style={{ zIndex: 1 }}>
            {pipelineStages.map((stage, index) => {
              const stageConfig = getStageConfig(stage.type);
              const statusConfig = getStatusConfig(stage.status);
              const isActive = index === currentAnimationIndex;

              return (
                <div
                  key={stage.id}
                  id={`stage-${stage.id}`}
                  onClick={() => handleStageClick(stage)}
                  className={cn(
                    "absolute cursor-pointer transition-all duration-300 transform hover:scale-105",
                    stageConfig.bgColor,
                    statusConfig.bgColor,
                    stageConfig.borderColor,
                    selectedStage?.id === stage.id && "ring-2 ring-white",
                    isActive && "animate-pulse"
                  )}
                  style={{
                    left: stage.position.x,
                    top: stage.position.y,
                    width: 160,
                    height: 80,
                  }}
                >
                  <div className="p-3 h-full flex flex-col">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {stageConfig.icon}
                        <span className="text-xs font-semibold text-white">
                          {stageConfig.label}
                        </span>
                      </div>
                      <div className={cn("px-2 py-0.5 rounded-full text-xs", statusConfig.bgColor)}>
                        {statusConfig.icon}
                      </div>
                    </div>

                    {/* Name */}
                    <p className="text-sm font-medium text-white mb-1">
                      {stage.name}
                    </p>

                    {/* Status */}
                    <div className="flex items-center justify-between text-xs">
                      <span className={statusConfig.textColor}>
                        {stage.status}
                      </span>
                      {stage.duration && (
                        <span className="text-slate-400 font-mono">
                          {stage.duration}ms
                        </span>
                      )}
                    </div>

                    {/* Progress indicator */}
                    {isActive && (
                      <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div className="h-full w-3/4 bg-emerald-400 animate-pulse" />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Stage Details */}
      {selectedStage && (
        <div className="p-4 border-t border-slate-800 bg-slate-900/30">
          <h3 className="text-sm font-semibold text-white mb-3">
            {getStageConfig(selectedStage.type).label} Details
          </h3>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-slate-400">Status</p>
              <p className={cn("font-medium", getStatusConfig(selectedStage.status).textColor)}>
                {selectedStage.status}
              </p>
            </div>
            <div>
              <p className="text-slate-400">Duration</p>
              <p className="font-mono text-slate-300">
                {selectedStage.duration ? `${selectedStage.duration}ms` : "N/A"}
              </p>
            </div>
            {selectedStage.startTime && (
              <div>
                <p className="text-slate-400">Started</p>
                <p className="font-mono text-slate-300">
                  {new Date(selectedStage.startTime).toLocaleTimeString()}
                </p>
              </div>
            )}
            {selectedStage.endTime && (
              <div>
                <p className="text-slate-400">Ended</p>
                <p className="font-mono text-slate-300">
                  {new Date(selectedStage.endTime).toLocaleTimeString()}
                </p>
              </div>
            )}
          </div>
          {selectedStage.error && (
            <div className="mt-3 p-3 rounded-lg border border-rose-400/30 bg-rose-400/5">
              <p className="text-sm text-rose-400 font-medium">Error</p>
              <p className="text-xs text-rose-300 mt-1">{selectedStage.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}