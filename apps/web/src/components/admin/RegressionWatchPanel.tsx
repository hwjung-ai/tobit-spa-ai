"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { fetchApi } from "@/lib/adminUtils";
import RCAPanel from "./RCAPanel";

interface GoldenQuery {
  id: string;
  name: string;
  query_text: string;
  ops_type: string;
  enabled: boolean;
  created_at: string;
}

interface RegressionRun {
  id: string;
  golden_query_id: string;
  baseline_id: string;
  candidate_trace_id: string;
  baseline_trace_id: string;
  judgment: "PASS" | "WARN" | "FAIL";
  verdict_reason: string | null;
  created_at: string;
}

interface RegressionRunDetail extends RegressionRun {
  diff_summary: Record<string, unknown> | null;
  triggered_by: string;
  execution_duration_ms: number | null;
}

export default function RegressionWatchPanel() {
  const searchParams = useSearchParams();

  const [queries, setQueries] = useState<GoldenQuery[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RegressionRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [contextScreenId, setContextScreenId] = useState<string | null>(null);
  const [contextAssetId, setContextAssetId] = useState<string | null>(null);
  const [contextVersion, setContextVersion] = useState<string | null>(null);

  useEffect(() => {
    setContextScreenId(searchParams.get("screen_id"));
    setContextAssetId(searchParams.get("asset_id"));
    setContextVersion(searchParams.get("version"));
  }, [searchParams]);

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showBaselineDialog, setShowBaselineDialog] = useState(false);
  const [showRunDialog, setShowRunDialog] = useState(false);
  const [selectedQuery, setSelectedQuery] = useState<GoldenQuery | null>(null);
  const [selectedRun, setSelectedRun] = useState<RegressionRunDetail | null>(null);
  const [showRunDetail, setShowRunDetail] = useState(false);

  const [createForm, setCreateForm] = useState({
    name: "",
    query_text: "",
    ops_type: "all",
  });

  const [baselineForm, setBaselineForm] = useState({
    trace_id: "",
  });

  // Load golden queries
  const loadQueries = async () => {
    setLoading(true);
    try {
      const result = await fetchApi<{ queries: GoldenQuery[] }>("/ops/golden-queries", {
        method: "GET",
      });
      setQueries(result.data?.queries ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queries");
    } finally {
      setLoading(false);
    }
  };

  // Load regression runs
  const loadRuns = async (queryId?: string) => {
    setRunsLoading(true);
    try {
      const params = new URLSearchParams();
      if (queryId) params.append("golden_query_id", queryId);
      params.append("limit", "20");

      const result = await fetchApi<{ runs: RegressionRun[] }>(`/ops/regression-runs?${params}`, {
        method: "GET",
      });
      setRuns(result.data?.runs ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runs");
    } finally {
      setRunsLoading(false);
    }
  };

  useEffect(() => {
    loadQueries();
    loadRuns();
  }, []);

  const handleCreateQuery = async () => {
    try {
      await fetchApi("/ops/golden-queries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createForm),
      });
      setShowCreateDialog(false);
      setCreateForm({ name: "", query_text: "", ops_type: "all" });
      loadQueries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create query");
    }
  };

  const handleSetBaseline = async () => {
    if (!selectedQuery) return;
    try {
      await fetchApi(`/ops/golden-queries/${selectedQuery.id}/set-baseline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(baselineForm),
      });
      setShowBaselineDialog(false);
      setBaselineForm({ trace_id: "" });
      setSelectedQuery(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to set baseline");
    }
  };

  const handleRunRegression = async () => {
    if (!selectedQuery) return;
    try {
      await fetchApi(`/ops/golden-queries/${selectedQuery.id}/run-regression`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ triggered_by: "manual" }),
      });
      setShowRunDialog(false);
      setSelectedQuery(null);
      loadRuns(selectedQuery.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run regression");
    }
  };

  const handleToggleQuery = async (query: GoldenQuery) => {
    try {
      await fetchApi(`/ops/golden-queries/${query.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !query.enabled }),
      });
      loadQueries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update query");
    }
  };

  const handleDeleteQuery = async (queryId: string) => {
    if (!confirm("Are you sure?")) return;
    try {
      await fetchApi(`/ops/golden-queries/${queryId}`, {
        method: "DELETE",
      });
      loadQueries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete query");
    }
  };

  const loadRunDetail = async (runId: string) => {
    try {
      const result = await fetchApi(`/ops/regression-runs/${runId}`, {
        method: "GET",
      });
      setSelectedRun(result.data as RegressionRunDetail);
      setShowRunDetail(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run details");
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
        return "text-[var(--muted-foreground)] bg-[var(--surface-base)]";
    }
  };

   return (
    <div className="space-y-6" data-testid="regression-panel">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {contextScreenId && (
        <Alert
          className="rounded-lg border   px-4 py-3 text-sm " style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-overlay)"}}
        >
          <AlertDescription>
            Regression context: screen{" "}
            <span className="font-semibold text-white">{contextScreenId}</span>
            {contextVersion ? ` · v${contextVersion}` : ""}
            {contextAssetId ? ` · asset ${contextAssetId}` : ""}
          </AlertDescription>
        </Alert>
      )}

      {/* Golden Queries Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Golden Queries</h2>
          <Button
            size="sm"
            onClick={() => setShowCreateDialog(true)}
            className="bg-sky-600 hover:bg-sky-700"
          >
            + New Query
          </Button>
        </div>

        {loading ? (
          <div className="text-center " style={{color: "var(--muted-foreground)"}}>Loading...</div>
        ) : queries.length === 0 ? (
          <div className="text-center  py-8" style={{color: "var(--muted-foreground)"}}>
            No golden queries yet
          </div>
        ) : (
          <div className=" border  rounded-lg overflow-hidden" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b  " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                  <th className="px-4 py-3 text-left " style={{color: "var(--foreground-secondary)"}}>Name</th>
                  <th className="px-4 py-3 text-left " style={{color: "var(--foreground-secondary)"}}>Type</th>
                  <th className="px-4 py-3 text-left " style={{color: "var(--foreground-secondary)"}}>Query</th>
                  <th className="px-4 py-3 text-center " style={{color: "var(--foreground-secondary)"}}>Status</th>
                  <th className="px-4 py-3 text-right " style={{color: "var(--foreground-secondary)"}}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queries.map((query) => (
                  <tr key={query.id} className="border-b " style={{borderColor: "var(--border)"}}>
                    <td className="px-4 py-3 text-white font-medium">
                      {query.name}
                    </td>
                    <td className="px-4 py-3  text-xs" style={{color: "var(--foreground-secondary)"}}>
                      <span className=" px-2 py-1 rounded" style={{backgroundColor: "var(--surface-elevated)"}}>
                        {query.ops_type}
                      </span>
                    </td>
                    <td className="px-4 py-3  truncate max-w-xs" style={{color: "var(--foreground-secondary)"}}>
                      {query.query_text}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggleQuery(query)}
                        className={`px-3 py-1 rounded text-xs font-medium ${
                          query.enabled
                            ? "bg-green-900 text-green-300"
                            : " "
                        }`} style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)"}}
                      >
                        {query.enabled ? "Enabled" : "Disabled"}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedQuery(query);
                          setShowBaselineDialog(true);
                        }}
                        className="text-xs h-8 bg-sky-600 hover:bg-sky-700 text-white"
                      >
                        Set Baseline
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedQuery(query);
                          setShowRunDialog(true);
                        }}
                        className="text-xs h-8 bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        Run
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleDeleteQuery(query.id)}
                        className="text-xs h-8 bg-red-600 hover:bg-red-700 text-white"
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Regression Runs Section */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Recent Runs</h2>

        {runsLoading ? (
          <div className="text-center " style={{color: "var(--muted-foreground)"}}>Loading...</div>
        ) : runs.length === 0 ? (
          <div className="text-center  py-8" style={{color: "var(--muted-foreground)"}}>
            No regression runs yet
          </div>
        ) : (
          <div className=" border  rounded-lg overflow-hidden" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b  " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                  <th className="px-4 py-3 text-left " style={{color: "var(--foreground-secondary)"}}>
                    Query
                  </th>
                  <th className="px-4 py-3 text-center " style={{color: "var(--foreground-secondary)"}}>
                    Result
                  </th>
                  <th className="px-4 py-3 text-left " style={{color: "var(--foreground-secondary)"}}>Reason</th>
                  <th className="px-4 py-3 text-left " style={{color: "var(--foreground-secondary)"}}>Time</th>
                  <th className="px-4 py-3 text-right " style={{color: "var(--foreground-secondary)"}}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => {
                  const query = queries.find((q) => q.id === run.golden_query_id);
                  return (
                    <tr key={run.id} className="border-b " style={{borderColor: "var(--border)"}}>
                      <td className="px-4 py-3 text-white font-medium">
                        {query?.name || "Unknown"}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`px-3 py-1 rounded text-xs font-bold ${getJudgmentColor(
                            run.judgment
                          )}`}
                        >
                          {run.judgment}
                        </span>
                      </td>
                      <td className="px-4 py-3  text-xs truncate max-w-xs" style={{color: "var(--foreground-secondary)"}}>
                        {run.verdict_reason || "-"}
                      </td>
                      <td className="px-4 py-3  text-xs" style={{color: "var(--muted-foreground)"}}>
                        {new Date(run.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => loadRunDetail(run.id)}
                          className="text-xs h-8"
                        >
                          Details
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Query Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
          <DialogHeader>
            <DialogTitle className="text-white">Create Golden Query</DialogTitle>
            <DialogDescription>
              Define a new quality baseline question
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label className="" style={{color: "var(--foreground-secondary)"}}>Name</Label>
              <Input
                value={createForm.name}
                onChange={(e) =>
                  setCreateForm({ ...createForm, name: e.target.value })
                }
                placeholder="e.g., Device Health Check"
                className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              />
            </div>

            <div>
              <Label className="" style={{color: "var(--foreground-secondary)"}}>Query Text</Label>
              <Input
                value={createForm.query_text}
                onChange={(e) =>
                  setCreateForm({ ...createForm, query_text: e.target.value })
                }
                placeholder="The actual question..."
                className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              />
            </div>

            <div>
              <Label className="" style={{color: "var(--foreground-secondary)"}}>OPS Type</Label>
              <select
                value={createForm.ops_type}
                onChange={(e) =>
                  setCreateForm({ ...createForm, ops_type: e.target.value })
                }
                className="w-full  border  rounded px-3 py-2 text-white" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              >
                <option>all</option>
                <option>config</option>
                <option>history</option>
                <option>metric</option>
                <option>relation</option>
                <option>graph</option>
                <option>hist</option>
              </select>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleCreateQuery} className="bg-sky-600">
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Set Baseline Dialog */}
      <Dialog open={showBaselineDialog} onOpenChange={setShowBaselineDialog}>
        <DialogContent className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
          <DialogHeader>
            <DialogTitle className="text-white">Set Baseline</DialogTitle>
            <DialogDescription>
              Use a trace as the regression baseline for {selectedQuery?.name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label className="" style={{color: "var(--foreground-secondary)"}}>Trace ID</Label>
              <Input
                value={baselineForm.trace_id}
                onChange={(e) =>
                  setBaselineForm({ ...baselineForm, trace_id: e.target.value })
                }
                placeholder="Paste trace ID..."
                className="  text-xs font-mono" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              onClick={() => setShowBaselineDialog(false)}
              className=" hover: text-white" style={{backgroundColor: "var(--surface-elevated)"}}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSetBaseline}
              className="bg-sky-600 hover:bg-sky-700 text-white"
              disabled={!baselineForm.trace_id}
            >
              Set Baseline
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Run Regression Dialog */}
      <Dialog open={showRunDialog} onOpenChange={setShowRunDialog}>
        <DialogContent className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
          <DialogHeader>
            <DialogTitle className="text-white">Run Regression</DialogTitle>
            <DialogDescription>
              Execute {selectedQuery?.name} and check for regressions
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <Alert className="bg-sky-950 border-sky-800">
              <AlertDescription className="text-sky-200">
                This will execute the golden query and compare against the
                baseline trace using deterministic judgment rules.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter>
            <Button
              onClick={() => setShowRunDialog(false)}
              className=" hover: text-white" style={{backgroundColor: "var(--surface-elevated)"}}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRunRegression}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Run Regression
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Run Detail Dialog */}
      <Dialog open={showRunDetail} onOpenChange={setShowRunDetail}>
        <DialogContent className="  max-w-2xl" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
          <DialogHeader>
            <DialogTitle className="text-white">Regression Run Details</DialogTitle>
          </DialogHeader>

          {selectedRun && (
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs " style={{color: "var(--muted-foreground)"}}>Judgment</p>
                  <p
                    className={`text-lg font-bold ${getJudgmentColor(
                      selectedRun.judgment
                    )}`}
                  >
                    {selectedRun.judgment}
                  </p>
                </div>
                <div>
                  <p className="text-xs " style={{color: "var(--muted-foreground)"}}>Duration</p>
                  <p className="text-lg font-bold text-white">
                    {selectedRun.execution_duration_ms}ms
                  </p>
                </div>
              </div>

              {selectedRun.verdict_reason && (
                <div>
                  <p className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Reason</p>
                  <p className="text-sm " style={{color: "var(--foreground-secondary)"}}>
                    {selectedRun.verdict_reason}
                  </p>
                </div>
              )}

              {/* RCA Panel - Root Cause Analysis */}
              {(selectedRun.judgment === "FAIL" || selectedRun.judgment === "WARN") && (
                <div className="border-t  pt-4" style={{borderColor: "var(--border)"}}>
                  <RCAPanel
                    baselineTraceId={selectedRun.baseline_trace_id}
                    candidateTraceId={selectedRun.candidate_trace_id}
                  />
                </div>
              )}

              {selectedRun.diff_summary && (
                <div>
                  <p className="text-xs  mb-2" style={{color: "var(--muted-foreground)"}}>Diff Summary</p>
                  <div className="space-y-1 text-xs">
                    {Object.entries(selectedRun.diff_summary).map(
                      ([key, value]) => (
                        <div
                          key={key}
                          className="flex justify-between " style={{color: "var(--foreground-secondary)"}}
                        >
                          <span>{key}:</span>
                          <span className="" style={{color: "var(--muted-foreground)"}}>
                            {String(value)}
                          </span>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              <div>
                <p className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Traces</p>
                <div className="space-y-1 text-xs">
                  <div className="flex gap-2">
                    <span className="" style={{color: "var(--muted-foreground)"}}>Baseline:</span>
                    <code className="text-sky-400 font-mono truncate">
                      {selectedRun.baseline_trace_id}
                    </code>
                  </div>
                  <div className="flex gap-2">
                    <span className="" style={{color: "var(--muted-foreground)"}}>Candidate:</span>
                    <code className="text-green-400 font-mono truncate">
                      {selectedRun.candidate_trace_id}
                    </code>
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button onClick={() => setShowRunDetail(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
