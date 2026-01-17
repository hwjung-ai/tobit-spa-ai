"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface EvidenceItem {
  path: string;
  snippet: string;
  display: string;
  inspector_link: string;
}

interface RCAHypothesis {
  rank: number;
  title: string;
  confidence: "high" | "medium" | "low";
  evidence: EvidenceItem[];
  checks: string[];
  recommended_actions: string[];
  description: string;
}

interface RCAPanelProps {
  traceId: string;
  baselineTraceId?: string;
  candidateTraceId?: string;
}

export default function RCAPanel({
  traceId,
  baselineTraceId,
  candidateTraceId,
}: RCAPanelProps) {
  const [hypotheses, setHypotheses] = useState<RCAHypothesis[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRCA() {
      setLoading(true);
      setError(null);
      try {
        // Determine which endpoint to call
        const isRegression = baselineTraceId && candidateTraceId;
        const endpoint = isRegression
          ? `/ops/rca/analyze-regression?baseline_trace_id=${baselineTraceId}&candidate_trace_id=${candidateTraceId}`
          : `/ops/rca/analyze-trace?trace_id=${traceId}`;

        const response = await fetch(endpoint, { method: "POST" });
        if (!response.ok) {
          throw new Error(`Failed to load RCA: ${response.status}`);
        }

        const data = await response.json();
        if (data.code === 0 && data.data?.hypotheses) {
          setHypotheses(data.data.hypotheses);
        } else {
          setError(data.message || "Failed to load RCA");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    loadRCA();
  }, [traceId, baselineTraceId, candidateTraceId]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-4 text-sm text-slate-300 animate-pulse">
        Loading RCA analysis...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-500/40 bg-rose-500/5 p-4 text-sm text-rose-200">
        <p className="font-semibold">RCA Analysis Error</p>
        <p className="text-xs text-rose-300">{error}</p>
      </div>
    );
  }

  if (!hypotheses || hypotheses.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-700 bg-slate-900/40 p-4 text-sm text-slate-400">
        No root causes identified.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Root Cause Analysis</h3>

      {hypotheses.map((hyp, idx) => {
        const confidenceColor =
          hyp.confidence === "high"
            ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-200"
            : hyp.confidence === "medium"
              ? "bg-amber-500/20 border-amber-500/50 text-amber-200"
              : "bg-slate-500/20 border-slate-500/50 text-slate-200";

        return (
          <article
            key={idx}
            className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-white">{hyp.title}</h4>
              <span
                className={`rounded-full border px-2 py-1 text-xs font-medium ${confidenceColor}`}
              >
                {hyp.confidence.toUpperCase()} confidence
              </span>
            </div>

            {/* Description */}
            {hyp.description && (
              <p className="text-sm text-slate-300">{hyp.description}</p>
            )}

            {/* Evidence */}
            {hyp.evidence.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.1em] text-slate-400">
                  Evidence
                </p>
                <ul className="space-y-1">
                  {hyp.evidence.map((ev, eidx) => (
                    <li key={eidx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-slate-500 flex-shrink-0">•</span>
                      <span className="flex-grow">
                        {ev.display || ev.path}
                        {ev.snippet && (
                          <span className="block text-slate-400 text-[10px] mt-1">
                            Value: {ev.snippet}
                          </span>
                        )}
                      </span>
                      {/* Inspector Jump Link */}
                      <Link
                        href={ev.inspector_link}
                        className="text-sky-400 hover:text-sky-300 flex-shrink-0 font-medium"
                      >
                        →
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Checks (Verification Steps) */}
            {hyp.checks.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.1em] text-slate-400">
                  Verification Checklist
                </p>
                <ul className="space-y-1">
                  {hyp.checks.map((check, cidx) => (
                    <li key={cidx} className="text-xs text-slate-300 flex items-start gap-2">
                      <input
                        type="checkbox"
                        className="mt-0.5 cursor-pointer"
                        defaultChecked={false}
                      />
                      <span>{check}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommended Actions */}
            {hyp.recommended_actions.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.1em] text-slate-400">
                  Recommended Actions
                </p>
                <ul className="space-y-1">
                  {hyp.recommended_actions.map((action, aidx) => (
                    <li key={aidx} className="text-xs text-slate-300 flex items-start gap-2">
                      <span className="text-emerald-400 flex-shrink-0">→</span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}
