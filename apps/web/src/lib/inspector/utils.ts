import type { AnswerBlock, StageOutput, TraceSummaryRow } from "../apiClient/index";
import type { StageStatus } from "../../components/ops/InspectorStagePipeline";

export const getStatusBadgeClass = (status: string) =>
  status === "success" ? "bg-emerald-900/60 text-emerald-200" : "bg-rose-900/60 text-rose-200";

export const formatDuration = (ms: number) => `${ms}ms`;

export const formatAppliedAssetSummary = (trace: TraceSummaryRow) => {
  if (!trace.applied_asset_versions.length) {
    return "Assets: none";
  }
  const preview = trace.applied_asset_versions.slice(0, 3).join(" / ");
  const extra = trace.applied_asset_versions.length - 3;
  return extra > 0 ? `${preview} / +${extra} more` : preview;
};

export const summarizeStepPayload = (payload: Record<string, unknown> | null) => {
  if (!payload) {
    return "";
  }
  try {
    const text = JSON.stringify(payload, null, 2);
    return text.length > 120 ? `${text.slice(0, 120)}…` : text;
  } catch {
    return String(payload);
  }
};

export const summarizeBlockPayload = (block: AnswerBlock) => {
  const candidate = block.payload_summary ?? block.title ?? block.type;
  if (typeof candidate === "string") {
    return candidate.length > 120 ? `${candidate.slice(0, 120)}…` : candidate;
  }
  try {
    const text = JSON.stringify(candidate);
    return text.length > 120 ? `${text.slice(0, 120)}…` : text;
  } catch {
    return String(candidate);
  }
};

export const normalizeStageStatus = (stageOutput?: StageOutput | null): StageStatus => {
  if (!stageOutput) return "pending";
  if ((stageOutput.result as Record<string, unknown> | null)?.skipped) return "skipped";
  const status = stageOutput.diagnostics?.status;
  if (status === "warning" || status === "error" || status === "ok") return status as StageStatus;
  return "ok";
};
