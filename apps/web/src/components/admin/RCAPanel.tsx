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
  traceId?: string;
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
      <div className="rounded-2xl border border-variant bg-surface-overlay p-4 text-sm text-muted-foreground animate-pulse">
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
      <div className="rounded-2xl border border-variant bg-surface-overlay p-4 text-sm text-muted-foreground">
        No root causes identified.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Root Cause Analysis</h3>

      {hypotheses.map((hyp, idx) => {
        const confidenceColor =
          hyp.confidence === "high"
            ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-200"
            : hyp.confidence === "medium"
              ? "bg-amber-500/20 border-amber-500/50 text-amber-200"
              : "bg-surface-elevated border-variant text-foreground-secondary";

        return (
          <article
            key={idx}
            className="rounded-xl border border-variant bg-surface-overlay p-4 space-y-3"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-foreground">{hyp.title}</h4>
              <span
                className={`rounded-full border px-2 py-1 text-xs font-medium ${confidenceColor}`}
              >
                {hyp.confidence.toUpperCase()} confidence
              </span>
            </div>

            {/* Description */}
            {hyp.description && (
              <p className="text-sm text-muted-foreground">{hyp.description}</p>
            )}

            {/* Evidence */}
            {hyp.evidence.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm uppercase tracking-wider text-muted-foreground">
                  Evidence
                </p>
                <ul className="space-y-1">
                  {hyp.evidence.map((ev, eidx) => (
                    <li key={eidx} className="text-xs text-muted-foreground flex items-start gap-2">
                      <span className="flex-shrink-0 text-muted-foreground">•</span>
                      <span className="flex-grow">
                        {ev.display || ev.path}
                        {ev.snippet && (
                          <span className="block text-tiny mt-1 text-muted-foreground">
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
                <p className="text-sm uppercase tracking-wider text-muted-foreground">
                  Verification Checklist
                </p>
                <ul className="space-y-1">
                  {hyp.checks.map((check, cidx) => (
                    <li key={cidx} className="text-xs text-muted-foreground flex items-start gap-2">
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
                <p className="text-sm uppercase tracking-wider text-muted-foreground">
                  Recommended Actions
                </p>
                <ul className="space-y-1">
                  {hyp.recommended_actions.map((action, aidx) => (
                    <li key={aidx} className="text-xs text-muted-foreground flex items-start gap-2">
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
