import { useState, useCallback, useEffect } from "react";
import { fetchApi } from "../../lib/adminUtils";
import { ChevronDown, Clock, AlertTriangle, CheckCircle, XCircle } from "lucide-react";

interface StageDiffViewProps {
  baselineTraceId: string;
  currentTraceId: string;
  onClose: () => void;
}

interface StageComparison {
  stage: string;
  baseline: {
    duration_ms: number;
    status: string;
    counts: Record<string, number>;
    has_references: boolean;
  };
  current: {
    duration_ms: number;
    status: string;
    counts: Record<string, number>;
    has_references: boolean;
  };
  changed: boolean;
  baseline_result?: unknown;
  current_result?: unknown;
  baseline_references?: unknown[];
  current_references?: unknown[];
}

interface ComparisonSummary {
  baseline_trace_id: string;
  current_trace_id: string;
  total_stages: number;
  changed_stages: number;
  regressed_stages: number;
  comparison_results: StageComparison[];
  summary: {
    regression_detected: boolean;
    change_percentage: number;
    performance_change: {
      avg_duration_change: number;
      total_duration_change: number;
    };
  };
}

const STAGE_DISPLAY_NAMES = {
  route_plan: "ROUTE+PLAN",
  validate: "VALIDATE",
  execute: "EXECUTE",
  compose: "COMPOSE",
  present: "PRESENT",
};

const STATUS_ICONS = {
  ok: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
};

const STATUS_COLORS = {
  ok: "text-green-400",
  warning: "text-yellow-400",
  error: "text-red-400",
};

function StatusBadge({ status }: { status: string }) {
  const Icon = STATUS_ICONS[status as keyof typeof STATUS_ICONS] || CheckCircle;
  return (
    <div className={`flex items-center gap-1 ${STATUS_COLORS[status as keyof typeof STATUS_COLORS]}`}>
      <Icon className="h-4 w-4" />
      <span className="text-sm capitalize">{status}</span>
    </div>
  );
}

function DurationChange({ baseline, current }: { baseline: number; current: number }) {
  const change = current - baseline;
  const percentage = baseline > 0 ? (change / baseline) * 100 : 0;

  const isPositive = change > 0;
  const colorClass = isPositive ? "text-red-400" : "text-green-400";
  const sign = isPositive ? "+" : "";

  return (
    <div className={`text-sm font-mono ${colorClass}`}>
      {current}ms ({sign}{change}ms, {sign}{percentage.toFixed(1)}%)
    </div>
  );
}

function StageDiffSection({
  stage,
  comparison,
  showDetails
}: {
  stage: string;
  comparison: StageComparison;
  showDetails: boolean;
}) {
  const [expanded, setExpanded] = useState(showDetails);

  const baseline = comparison.baseline;
  const current = comparison.current;

  return (
    <div className={`border rounded-lg ${comparison.changed ? "border-amber-500/50 bg-amber-500/10" : ""} border-variant`}>
      <div
        className="p-4 cursor-pointer hover:bg-surface-elevated transition-colors bg-surface-overlay"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-muted-foreground">
              {STAGE_DISPLAY_NAMES[stage as keyof typeof STAGE_DISPLAY_NAMES] || stage}
            </h3>
            <StatusBadge status={baseline.status} />
            <span className="text-muted-foreground">→</span>
            <StatusBadge status={current.status} />
            {comparison.changed && (
              <span className="text-amber-400 text-xs">CHANGED</span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <DurationChange baseline={baseline.duration_ms} current={current.duration_ms} />
            </div>
            <ChevronDown className={`h-4 w-4 transition-transform text-muted-foreground ${expanded ? "rotate-180" : ""}`} />
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t p-4 space-y-4 border-variant">
          {/* Counts Comparison */}
          <div>
            <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Metrics</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              {Object.entries(baseline.counts).map(([key, value]) => {
                const currentValue = current.counts[key] || 0;
                const changed = value !== currentValue;
                return (
                  <div key={key} className="flex justify-between">
                    <span className="capitalize text-muted-foreground">{key}:</span>
                    <span className={changed ? "text-amber-400" : "text-muted-foreground"}>
                      {currentValue} {changed && `(was: ${value})`}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* References Comparison */}
          <div>
            <h4 className="text-sm font-semibold mb-2 text-muted-foreground">References</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Baseline:</span>
                <div className={`mt-1 text-foreground ${baseline.has_references ? "text-green-400" : ""}`}>
                  {baseline.has_references ? "✓ Has references" : "✗ No references"}
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">Current:</span>
                <div className={`mt-1 text-foreground ${current.has_references ? "text-green-400" : ""}`}>
                  {current.has_references ? "✓ Has references" : "✗ No references"}
                </div>
              </div>
            </div>
          </div>

          {/* Stage Results */}
          <div>
            <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Stage Results</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h5 className="text-xs mb-1 text-muted-foreground">Baseline</h5>
                <pre className="text-xs p-2 rounded overflow-x-auto bg-surface-base">
                  {JSON.stringify(comparison.baseline_result, null, 2)}
                </pre>
              </div>
              <div>
                <h5 className="text-xs mb-1 text-muted-foreground">Current</h5>
                <pre className="text-xs p-2 rounded overflow-x-auto bg-surface-base">
                  {JSON.stringify(comparison.current_result, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function StageDiffView({ baselineTraceId, currentTraceId, onClose }: StageDiffViewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ComparisonSummary | null>(null);

  const fetchComparison = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchApi<ComparisonSummary>(`/ops/stage-compare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          baseline_trace_id: baselineTraceId,
          current_trace_id: currentTraceId,
          stages_to_compare: ["route_plan", "validate", "execute", "compose", "present"],
          comparison_depth: "detailed",
        }),
      });

      setComparison(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [baselineTraceId, currentTraceId]);

  useEffect(() => {
    fetchComparison();
  }, [fetchComparison]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className=" border  rounded-xl p-6">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
            <p className="">Comparing stages...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className=" border  rounded-xl p-6 max-w-md">
          <h2 className="text-xl font-semibold  mb-2">Error</h2>
          <p className=" mb-4">{error}</p>
          <button
            onClick={() => {
              setError(null);
              fetchComparison();
            }}
            className="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!comparison) {
    return null;
  }

  const hasRegression = comparison.summary.regression_detected;
  const changePercentage = comparison.summary.change_percentage;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className=" border  rounded-xl p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold ">Stage Comparison</h2>
          <button
            onClick={onClose}
            className="p-2 hover: rounded-lg transition-colors"
          >
            <XCircle className="h-5 w-5 " />
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className=" border  rounded-lg p-4">
            <div className="text-sm ">Total Stages</div>
            <div className="text-2xl font-bold ">{comparison.total_stages}</div>
          </div>
          <div className=" border  rounded-lg p-4">
            <div className="text-sm ">Changed Stages</div>
            <div className="text-2xl font-bold text-amber-400">{comparison.changed_stages}</div>
          </div>
          <div className=" border  rounded-lg p-4">
            <div className="text-sm ">Regressions</div>
            <div className={`text-2xl font-bold ${hasRegression ? "text-red-400" : "text-green-400"}`}>
              {comparison.regressed_stages}
            </div>
          </div>
          <div className=" border  rounded-lg p-4">
            <div className="text-sm ">Change %</div>
            <div className={`text-2xl font-bold ${changePercentage > 0 ? "text-red-400" : "text-green-400"}`}>
              {changePercentage.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Overall Status */}
        <div className={`mb-6 p-4 rounded-lg border ${hasRegression ? "border-red-500 bg-red-500/10" : "border-green-500 bg-green-500/10"}`}>
          <div className="flex items-center gap-3">
            {hasRegression ? (
              <AlertTriangle className="h-6 w-6 text-red-400" />
            ) : (
              <CheckCircle className="h-6 w-6 text-green-400" />
            )}
            <div>
              <h3 className="font-semibold ">
                {hasRegression ? "Regressions Detected" : "No Regressions Detected"}
              </h3>
              <p className="text-sm ">
                {hasRegression
                  ? "Some stages have shown degradation in performance or functionality."
                  : "All stages are performing as expected."
                }
              </p>
            </div>
          </div>
        </div>

        {/* Stage Comparisons */}
        <div className="space-y-4">
          {comparison.comparison_results.map((stageComparison) => (
            <StageDiffSection
              key={stageComparison.stage}
              stage={stageComparison.stage}
              comparison={stageComparison}
              showDetails={false}
            />
          ))}
        </div>
      </div>
    </div>
  );
}