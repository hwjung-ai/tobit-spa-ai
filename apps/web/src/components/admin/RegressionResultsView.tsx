"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { fetchApi } from "@/lib/adminUtils";
import TraceDiffView from "./TraceDiffView";

interface RegressionRunDetail {
  id: string;
  golden_query_id: string;
  baseline_id: string;
  candidate_trace_id: string;
  baseline_trace_id: string;
  judgment: "PASS" | "WARN" | "FAIL";
  verdict_reason: string | null;
  diff_summary: Record<string, any> | null;
  triggered_by: string;
  execution_duration_ms: number | null;
  created_at: string;
}

interface ExecutionTraceDetail {
  trace_id: string;
  parent_trace_id: string | null;
  feature: string;
  endpoint: string;
  method: string;
  ops_mode: string;
  question: string;
  status: string;
  duration_ms: number;
  request_payload: Record<string, any> | null;
  applied_assets: Record<string, any> | null;
  asset_versions: string[] | null;
  plan_raw: Record<string, any> | null;
  plan_validated: Record<string, any> | null;
  execution_steps: Record<string, any>[] | null;
  references: Record<string, any>[] | null;
  answer: Record<string, any> | null;
  ui_render: Record<string, any> | null;
  flow_spans: Record<string, any>[] | null;
  created_at: string;
}

interface RegressionResultsViewProps {
  runId: string;
  onClose: () => void;
}

export default function RegressionResultsView({
  runId,
  onClose,
}: RegressionResultsViewProps) {
  const [run, setRun] = useState<RegressionRunDetail | null>(null);
  const [baselineTrace, setBaselineTrace] = useState<ExecutionTraceDetail | null>(
    null
  );
  const [candidateTrace, setCandidateTrace] =
    useState<ExecutionTraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        // Load regression run details
        const runResult = await fetchApi(`/ops/regression-runs/${runId}`, {
          method: "GET",
        });
        const runData = runResult.data as RegressionRunDetail;
        setRun(runData);

        // Load baseline trace
        const baselineResult = await fetchApi(
          `/inspector/traces/${runData.baseline_trace_id}`,
          {
            method: "GET",
          }
        );
        setBaselineTrace(baselineResult.data as ExecutionTraceDetail);

        // Load candidate trace
        const candidateResult = await fetchApi(
          `/inspector/traces/${runData.candidate_trace_id}`,
          {
            method: "GET",
          }
        );
        setCandidateTrace(candidateResult.data as ExecutionTraceDetail);

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [runId]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center text-slate-400">Loading regression results...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!run || !baselineTrace || !candidateTrace) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertDescription>Failed to load regression data</AlertDescription>
        </Alert>
      </div>
    );
  }

  const getJudgmentIcon = (judgment: string) => {
    switch (judgment) {
      case "PASS":
        return "✓";
      case "WARN":
        return "⚠";
      case "FAIL":
        return "✗";
      default:
        return "?";
    }
  };

  const getJudgmentColor = (judgment: string) => {
    switch (judgment) {
      case "PASS":
        return "text-green-400 bg-green-950";
      case "WARN":
        return "text-yellow-400 bg-yellow-950";
      case "FAIL":
        return "text-red-400 bg-red-950";
      default:
        return "text-gray-400 bg-gray-950";
    }
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header with Judgment */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white mb-4">Regression Results</h2>
          <div className="flex items-center gap-4">
            <div
              className={`px-6 py-3 rounded-lg font-bold text-2xl ${getJudgmentColor(
                run.judgment
              )}`}
            >
              {getJudgmentIcon(run.judgment)} {run.judgment}
            </div>
            <div className="space-y-1">
              <p className="text-xs text-slate-400">Reason</p>
              <p className="text-sm text-slate-200">
                {run.verdict_reason || "No specific reason"}
              </p>
            </div>
          </div>
        </div>
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>

      {/* Execution Details */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4 space-y-2">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-slate-400">Duration</p>
            <p className="text-lg font-semibold text-white">
              {run.execution_duration_ms}ms
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Triggered By</p>
            <p className="text-sm text-slate-200 capitalize">
              {run.triggered_by}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Timestamp</p>
            <p className="text-sm text-slate-200">
              {new Date(run.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Diff Summary */}
      {run.diff_summary && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-white mb-4">
            Diff Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(run.diff_summary).map(([key, value]) => {
              let displayValue = value;
              let displayColor = "text-slate-300";

              if (typeof value === "boolean") {
                displayValue = value ? "Yes" : "No";
                displayColor = value ? "text-red-400" : "text-green-400";
              } else if (typeof value === "number") {
                displayColor = value > 0 ? "text-red-400" : "text-green-400";
              }

              return (
                <div key={key} className="space-y-1">
                  <p className="text-xs text-slate-400 capitalize">
                    {key.replace(/_/g, " ")}
                  </p>
                  <p className={`font-semibold ${displayColor}`}>
                    {String(displayValue)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Trace IDs */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-white">Traces</h3>
        <div className="space-y-2">
          <div>
            <p className="text-xs text-slate-400 mb-1">Baseline Trace</p>
            <code className="block text-xs text-blue-400 font-mono bg-slate-950 p-2 rounded break-all">
              {run.baseline_trace_id}
            </code>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1">Candidate Trace</p>
            <code className="block text-xs text-green-400 font-mono bg-slate-950 p-2 rounded break-all">
              {run.candidate_trace_id}
            </code>
          </div>
        </div>
      </div>

      {/* Diff View Button */}
      <div>
        <Button
          onClick={() => setShowDiff(true)}
          className="bg-blue-600 hover:bg-blue-700 w-full"
        >
          View Detailed Diff
        </Button>
      </div>

      {/* Diff View Modal */}
      {showDiff && baselineTrace && candidateTrace && (
        <div className="fixed inset-0 bg-black/80 z-50 overflow-auto">
          <div className="p-4">
            <div className="max-w-7xl mx-auto">
              <div className="mb-4 flex justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowDiff(false)}
                  className="bg-slate-800 border-slate-700"
                >
                  Close Diff
                </Button>
              </div>
              <TraceDiffView
                baseline={baselineTrace}
                candidate={candidateTrace}
                onClose={() => setShowDiff(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Baseline & Candidate Info */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-950/30 border border-blue-800 rounded-lg p-4 space-y-2">
          <h3 className="text-sm font-semibold text-blue-300">Baseline</h3>
          <div className="space-y-1 text-xs">
            <div>
              <span className="text-slate-400">Status:</span>
              <span className="ml-2 text-white">{baselineTrace.status}</span>
            </div>
            <div>
              <span className="text-slate-400">Duration:</span>
              <span className="ml-2 text-white">{baselineTrace.duration_ms}ms</span>
            </div>
            <div>
              <span className="text-slate-400">Created:</span>
              <span className="ml-2 text-white">
                {new Date(baselineTrace.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-green-950/30 border border-green-800 rounded-lg p-4 space-y-2">
          <h3 className="text-sm font-semibold text-green-300">Candidate</h3>
          <div className="space-y-1 text-xs">
            <div>
              <span className="text-slate-400">Status:</span>
              <span className="ml-2 text-white">{candidateTrace.status}</span>
            </div>
            <div>
              <span className="text-slate-400">Duration:</span>
              <span className="ml-2 text-white">{candidateTrace.duration_ms}ms</span>
            </div>
            <div>
              <span className="text-slate-400">Created:</span>
              <span className="ml-2 text-white">
                {new Date(candidateTrace.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
