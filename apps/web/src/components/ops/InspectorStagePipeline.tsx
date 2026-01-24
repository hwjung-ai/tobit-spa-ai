"use client";

import React, { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StageStatus as StageStatusType, StageSnapshot as StageSnapshotType } from "@/lib/apiClientTypes";

interface StagePipelineProps {
  className?: string;
  traceId?: string;
  stages: StageSnapshotType[];
  onStageSelect?: (stage: StageSnapshotType) => void;
}

const STATUS_STYLES: Record<StageStatusType, { badge: string; icon: React.ReactElement }> = {
  pending: { badge: "bg-slate-800 text-slate-400", icon: <Clock className="h-3 w-3" /> },
  ok: { badge: "bg-emerald-500/10 text-emerald-400", icon: <CheckCircle className="h-3 w-3" /> },
  warning: { badge: "bg-amber-500/10 text-amber-400", icon: <AlertTriangle className="h-3 w-3" /> },
  error: { badge: "bg-rose-500/10 text-rose-400", icon: <AlertTriangle className="h-3 w-3" /> },
  skipped: { badge: "bg-slate-800 text-slate-500", icon: <Clock className="h-3 w-3" /> },
};

const STAGE_STYLES: Record<string, string> = {
  route_plan: "border-blue-400/30 bg-blue-500/5",
  validate: "border-emerald-400/30 bg-emerald-500/5",
  execute: "border-amber-400/30 bg-amber-500/5",
  compose: "border-purple-400/30 bg-purple-500/5",
  present: "border-rose-400/30 bg-rose-500/5",
};

const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

  export default function InspectorStagePipeline({
  className,
  traceId,
  stages,
  onStageSelect,
}: StagePipelineProps) {
  const [selectedStage, setSelectedStage] = useState<StageSnapshotType | null>(null);
  const orderedStages = useMemo(() => (stages as StageSnapshotType[]) ?? [], [stages]);

  const handleStageClick = (stage: StageSnapshotType) => {
    setSelectedStage(stage);
    onStageSelect?.(stage);
  };

  return (
    <div className={cn("flex flex-col rounded-2xl border border-slate-800 bg-slate-950/60", className)}>
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white">Stage Pipeline</h2>
            {traceId && (
              <p className="text-xs text-slate-400 mt-1">Trace ID: {traceId.slice(0, 8)}...</p>
            )}
          </div>
          <div className="text-[10px] text-slate-500 uppercase tracking-[0.3em]">
            {orderedStages.length} stages
          </div>
        </div>
      </div>

      <div className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          {orderedStages.map((stage, index) => {
            const statusStyle = STATUS_STYLES[stage.status];
            const isSelected = selectedStage?.name === stage.name;
            return (
              <div key={stage.name} className="flex items-center gap-3">
                <button
                  onClick={() => handleStageClick(stage)}
                  className={cn(
                    "min-w-[160px] rounded-xl border px-3 py-2 text-left transition-all",
                    STAGE_STYLES[stage.name] || "border-slate-700 bg-slate-900/40",
                    isSelected && "ring-2 ring-white/30"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] uppercase tracking-[0.3em] text-slate-400">
                      {stage.label}
                    </span>
                    <span className={cn("px-2 py-0.5 rounded-full text-[10px] flex items-center gap-1", statusStyle.badge)}>
                      {statusStyle.icon}
                      {stage.status}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                    <span className="font-mono">{stage.name}</span>
                    <span>{stage.duration_ms ? `${stage.duration_ms}ms` : "-"}</span>
                  </div>
                </button>
                {index < orderedStages.length - 1 && (
                  <div className="h-px w-6 bg-slate-700" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {selectedStage && (
        <div className="border-t border-slate-800 bg-slate-900/30 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">{selectedStage.label} Details</h3>
            <div className={cn("text-xs px-2 py-1 rounded-full", STATUS_STYLES[selectedStage.status].badge)}>
              {selectedStage.status}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <details className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
              <summary className="text-[10px] uppercase tracking-[0.3em] text-slate-400 cursor-pointer">
                Stage Input
              </summary>
              <pre className="mt-2 text-[11px] text-slate-200 overflow-auto max-h-56">
                {selectedStage.input ? prettyJson(selectedStage.input) : "No input captured"}
              </pre>
            </details>
            <details className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
              <summary className="text-[10px] uppercase tracking-[0.3em] text-slate-400 cursor-pointer">
                Stage Output
              </summary>
              <pre className="mt-2 text-[11px] text-slate-200 overflow-auto max-h-56">
                {selectedStage.output ? prettyJson(selectedStage.output) : "No output captured"}
              </pre>
            </details>
          </div>
          {(selectedStage.diagnostics?.warnings?.length || selectedStage.diagnostics?.errors?.length) && (
            <div className="grid gap-3 md:grid-cols-2">
              {selectedStage.diagnostics?.warnings?.length ? (
                <div className="bg-amber-500/5 border border-amber-400/30 rounded-xl p-3">
                  <p className="text-xs text-amber-300 font-semibold">Warnings</p>
                  <ul className="mt-2 text-xs text-amber-200 space-y-1">
                    {selectedStage.diagnostics.warnings.map((warning, index) => (
                      <li key={`${warning}-${index}`}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {selectedStage.diagnostics?.errors?.length ? (
                <div className="bg-rose-500/5 border border-rose-400/30 rounded-xl p-3">
                  <p className="text-xs text-rose-300 font-semibold">Errors</p>
                  <ul className="mt-2 text-xs text-rose-200 space-y-1">
                    {selectedStage.diagnostics.errors.map((error, index) => (
                      <li key={`${error}-${index}`}>{error}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
