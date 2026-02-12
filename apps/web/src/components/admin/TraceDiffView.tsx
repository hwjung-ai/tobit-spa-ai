import { useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchApi } from "../../lib/adminUtils";
import {
  computeTraceDiff,
  type AssetsDiff,
  type AssetInfo,
  type DiffItem,
  type PlanDiff,
  type ToolCallsDiff,
  type ReferencesDiff,
  type AnswerBlocksDiff,
} from "../../lib/traceDiffUtils";

interface TraceInfo {
  trace_id: string;
  created_at: string;
  duration_ms: number;
  status: string;
}

interface TraceDiffViewProps {
  traceA: TraceInfo;
  traceB: TraceInfo;
  onClose: () => void;
}

type Section = "assets" | "plan" | "toolcalls" | "references" | "answers" | "ui";

interface SectionConfig {
  id: Section;
  label: string;
  icon: string;
}

const SECTIONS: SectionConfig[] = [
  { id: "assets", label: "Applied Assets", icon: "📦" },
  { id: "plan", label: "Plan", icon: "📋" },
  { id: "toolcalls", label: "Tool Calls", icon: "🔧" },
  { id: "references", label: "References", icon: "🔗" },
  { id: "answers", label: "Answer Blocks", icon: "📝" },
  { id: "ui", label: "UI Render", icon: "🎨" },
];

function formatTimestamp(isoString: string | undefined): string {
  if (!isoString) return "unknown";
  const date = new Date(isoString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function getStatusBadgeClass(status: string): string {
  return status === "success"
    ? "bg-emerald-900/40 text-emerald-200 border-emerald-700"
    : "bg-rose-900/40 text-rose-200 border-rose-700";
}

interface ChangeIndicatorProps {
  changeType: string;
}

function ChangeIndicator({ changeType }: ChangeIndicatorProps) {
  const indicatorClass =
    changeType === "added"
      ? "bg-blue-900/40 border-blue-700 text-blue-200"
      : changeType === "removed"
        ? "bg-rose-900/40 border-rose-700 text-rose-200"
        : changeType === "modified"
          ? "bg-amber-900/40 border-amber-700 text-amber-200"
          : "border";
  const label = changeType === "added" ? "+" : changeType === "removed" ? "−" : changeType === "modified" ? "~" : "=";
  return <span className={`inline-flex items-center px-2 py-1 rounded-full text-[10px] border ${indicatorClass}`}>{label}</span>;
}

/**
 * Section: Applied Assets Diff
 */
function AssetsDiffSection({ diff, showOnlyChanges }: { diff: AssetsDiff; showOnlyChanges: boolean }) {
  const assetChanged =
    diff.prompt.changeType !== "unchanged" ||
    diff.policy.changeType !== "unchanged" ||
    diff.mapping.changeType !== "unchanged" ||
    diff.queries.changeType !== "unchanged";

  if (showOnlyChanges && !assetChanged) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Prompt */}
      <AssetComparisonRow label="Prompt" asset={diff.prompt} />
      {/* Policy */}
      <AssetComparisonRow label="Policy" asset={diff.policy} />
      {/* Mapping */}
      <AssetComparisonRow label="Mapping" asset={diff.mapping} />
      {/* Queries */}
      {diff.queries.changeType !== "unchanged" && (
        <div className="rounded-xl px-4 py-3 space-y-2" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>Queries</span>
            <ChangeIndicator changeType={diff.queries.changeType} />
          </div>
          {diff.queries.before && (
            <div className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
              Before: {diff.queries.before.length} queries
            </div>
          )}
          {diff.queries.after && (
            <div className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
              After: {diff.queries.after.length} queries
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Asset comparison row (prompt/policy/mapping)
 */
function AssetComparisonRow({ label, asset }: { label: string; asset: DiffItem<AssetInfo> }) {
  if (asset.changeType === "unchanged") {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-2" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>{label}</span>
        <ChangeIndicator changeType={asset.changeType} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {/* Before */}
        {asset.before && (
          <div className="rounded px-3 py-2" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
            <p className="text-[10px] uppercase mb-1" style={{ color: "var(--muted-foreground)" }}>Before</p>
            <div className="text-[11px] space-y-1" style={{ color: "var(--foreground-secondary)" }}>
              <span style={{ color: "var(--muted-foreground)" }}>Name: </span>
              {asset.before.name}
            </div>
            <div>
              <span style={{ color: "var(--muted-foreground)" }}>Version: </span>
              {asset.before.version}
            </div>
            {asset.before.source && (
              <div>
                <span style={{ color: "var(--muted-foreground)" }}>Source: </span>
                {asset.before.source}
              </div>
            )}
          </div>
        )}
        {/* After */}
        {asset.after && (
          <div className="rounded px-3 py-2" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
            <p className="text-[10px] uppercase mb-1" style={{ color: "var(--muted-foreground)" }}>After</p>
            <div className="text-[11px] space-y-1" style={{ color: "var(--foreground-secondary)" }}>
              <span style={{ color: "var(--muted-foreground)" }}>Name: </span>
              {asset.after.name}
            </div>
            <div>
              <span style={{ color: "var(--muted-foreground)" }}>Version: </span>
              {asset.after.version}
            </div>
            {asset.after.source && (
              <div>
                <span style={{ color: "var(--muted-foreground)" }}>Source: </span>
                {asset.after.source}
              </div>
            )}
          </div>
        )}
      </div>
      {/* Changes */}
      {asset.changes && (
        <div className="rounded px-3 py-2" style={{ backgroundColor: "var(--surface-overlay)" }}>
          <p className="text-[10px] uppercase text-amber-600 mb-2">Changes</p>
          <div className="text-[11px] space-y-1" style={{ color: "var(--muted-foreground)" }}>
            {Object.entries(asset.changes).map(([key, change]) => (
              <div key={key}>
                <span style={{ color: "var(--muted-foreground)" }}>{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before)}</span>
                <span style={{ color: "var(--muted-foreground)" }}> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Section: Plan Diff
 */
function PlanDiffSection({ diff, showOnlyChanges }: { diff: PlanDiff; showOnlyChanges: boolean }) {
  if (showOnlyChanges && diff.changeType === "same") {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>Plan Comparison</span>
        <ChangeIndicator changeType={diff.changeType} />
      </div>
      {/* Validated Plan Changes */}
      {diff.validated && diff.validated.changeType === "modified" && (
        <div className="rounded px-3 py-2" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] uppercase mb-2" style={{ color: "var(--muted-foreground)" }}>Validated Plan Changes</p>
          <div className="text-[11px] space-y-1 max-h-40 overflow-y-auto" style={{ color: "var(--muted-foreground)" }}>
            {Object.entries(diff.validated.changes || {}).map(([key, change]: [string, { before: unknown; after: unknown }]) => (
              <div key={key} className="font-mono text-[10px]">
                <span style={{ color: "var(--muted-foreground)" }}>{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before).substring(0, 30)}...</span>
                <span style={{ color: "var(--muted-foreground)" }}> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after).substring(0, 30)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* Raw Plan Changes */}
      {diff.raw && diff.raw.changeType === "modified" && (
        <div className="rounded px-3 py-2" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] uppercase mb-2" style={{ color: "var(--muted-foreground)" }}>Raw Plan Changes</p>
          <div className="text-[11px] space-y-1 max-h-40 overflow-y-auto" style={{ color: "var(--muted-foreground)" }}>
            {Object.entries(diff.raw.changes || {}).map(([key, change]: [string, { before: unknown; after: unknown }]) => (
              <div key={key} className="font-mono text-[10px]">
                <span style={{ color: "var(--muted-foreground)" }}>{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before).substring(0, 30)}...</span>
                <span style={{ color: "var(--muted-foreground)" }}> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after).substring(0, 30)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {diff.changeType === "same" && (
        <div className="text-[11px] italic" style={{ color: "var(--muted-foreground)" }}>No plan changes detected</div>
      )}
    </div>
  );
}

/**
 * Section: Tool Calls Diff
 */
function ToolCallsDiffSection({ diff, showOnlyChanges }: { diff: ToolCallsDiff; showOnlyChanges: boolean }) {
  const hasChanges = diff.added.length > 0 || diff.removed.length > 0 || diff.modified.length > 0;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>Tool Calls</span>
        <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>
          {diff.unchanged} unchanged, {diff.added.length + diff.removed.length + diff.modified.length} changed
        </span>
      </div>
      {/* Added */}
      {diff.added.length > 0 && (
        <div className="rounded px-3 py-2" style={{ backgroundColor: "rgba(30, 58, 138, 0.2)", borderColor: "rgba(29, 78, 216, 0.5)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] uppercase text-blue-400 mb-2">Added ({diff.added.length})</p>
          <div className="text-[11px] space-y-1" style={{ color: "#bae6fd" }}>
            {diff.added.map((tool, idx) => (
              <div key={idx}>
                <span className="font-mono">{tool.tool_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Section: References Diff
 */
function ReferencesDiffSection({ diff, showOnlyChanges }: { diff: ReferencesDiff; showOnlyChanges: boolean }) {
  const hasChanges = diff.added.length > 0 || diff.removed.length > 0 || diff.modified.length > 0;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>References</span>
        <ChangeIndicator changeType={diff.changeType} />
      </div>
      <div className="text-[11px] space-y-1" style={{ color: "var(--muted-foreground)" }}>
        {diff.added.length > 0 && (
          <div>
            <span className="text-emerald-400">+ Added {diff.added.length} references</span>
          </div>
        )}
        {diff.removed.length > 0 && (
          <div>
            <span className="text-rose-400">- Removed {diff.removed.length} references</span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Section: Answer Blocks Diff
 */
function AnswerBlocksDiffSection({ diff, showOnlyChanges }: { diff: AnswerBlocksDiff; showOnlyChanges: boolean }) {
  if (showOnlyChanges && diff.changeType === "same") {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>Answer Blocks</span>
        <ChangeIndicator changeType={diff.changeType} />
      </div>
      <div className="text-[11px] space-y-1" style={{ color: "var(--muted-foreground)" }}>
        {diff.changeType === "added" && (
          <div className="font-mono text-[10px]" style={{ color: "#86efac" }}>
            {diff.added.map((block, idx) => (
              <div key={idx}>{block.type}</div>
            ))}
          </div>
        )}
        {diff.changeType === "removed" && (
          <div className="font-mono text-[10px]" style={{ color: "#fca5a5" }}>
            {diff.removed.map((block, idx) => (
              <div key={idx}>{block.type}</div>
            ))}
          </div>
        )}
        {diff.changeType === "modified" && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-mono text-[10px] mb-2" style={{ color: "#fca5a5" }}>Removed</div>
              {diff.removed.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.type}</div>
              ))}
            </div>
            <div>
              <div className="font-mono text-[10px] mb-2" style={{ color: "#86efac" }}>Added</div>
              {diff.added.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.type}</div>
              ))}
            </div>
          </div>
        )}
        {diff.changeType === "same" && (
          <div className="text-[11px] italic" style={{ color: "var(--muted-foreground)" }}>No block changes detected</div>
        )}
      </div>
    </div>
  );
}

/**
 * Section: UI Render Diff
 */
function UIRenderDiffSection({ diff, showOnlyChanges }: { diff: AnswerBlocksDiff; showOnlyChanges: boolean }) {
  if (showOnlyChanges && diff.changeType === "same") {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold" style={{ color: "var(--foreground-secondary)" }}>UI Render</span>
        <ChangeIndicator changeType={diff.changeType} />
      </div>
      <div className="text-[11px] space-y-1" style={{ color: "var(--muted-foreground)" }}>
        {diff.changeType === "added" && (
          <div className="font-mono text-[10px]" style={{ color: "#86efac" }}>
            {diff.added.map((block, idx) => (
              <div key={idx}>{block.type}</div>
            ))}
          </div>
        )}
        {diff.changeType === "removed" && (
          <div className="font-mono text-[10px]" style={{ color: "#fca5a5" }}>
            {diff.removed.map((block, idx) => (
              <div key={idx}>{block.type}</div>
            ))}
          </div>
        )}
        {diff.changeType === "modified" && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-mono text-[10px] mb-2" style={{ color: "#fca5a5" }}>Removed</div>
              {diff.removed.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.type}</div>
              ))}
            </div>
            <div>
              <div className="font-mono text-[10px] mb-2" style={{ color: "#86efac" }}>Added</div>
              {diff.added.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.type}</div>
              ))}
            </div>
          </div>
        )}
        {diff.changeType === "same" && (
          <div className="text-[11px] italic" style={{ color: "var(--muted-foreground)" }}>No UI render changes detected</div>
        )}
      </div>
    </div>
  );
}

export default function TraceDiffView({ traceA, traceB, onClose }: TraceDiffViewProps) {
  const [activeSection, setActiveSection] = useState<Section>("assets");
  const [showOnlyChanges, setShowOnlyChanges] = useState(false);

  const diff = useMemo(() => {
    return computeTraceDiff(traceA, traceB);
  }, [traceA, traceB]);

  const hasChanges = useMemo(() => {
    return (
      diff.assets.changeType !== "unchanged" ||
      diff.plan.changeType !== "same" ||
      diff.toolCalls.changeType !== "unchanged" ||
      diff.references.changeType !== "unchanged" ||
      diff.answers.changeType !== "unchanged" ||
      diff.ui.changeType !== "unchanged"
    );
  }, [diff]);

  const handleCompare = useCallback(async () => {
    if (!traceA.trace_id || !traceB.trace_id) {
      return;
    }

    try {
      const response = await fetchApi("/traces/compare", {
        method: "POST",
        body: {
          trace_a_id: traceA.trace_id,
          trace_b_id: traceB.trace_id,
        },
      });

      if (response.diff) {
        // Refresh the page to show comparison
        window.location.reload();
      }
    } catch (error) {
      console.error("Failed to compare traces:", error);
    }
  }, [traceA.trace_id, traceB.trace_id]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: "rgba(15, 23, 42, 0.8)" }}>
      <div className=" rounded-2xl shadow-2xl w-full max-w-7xl flex overflow-hidden" style={{ backgroundColor: "var(--surface-base)" ,  backgroundColor: "var(--surface-base)", maxHeight: "90vh" }}>
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>Trace Comparison</h2>
            <button
              onClick={onClose}
              className="rounded p-2 text-sm hover: transition-colors" style={{ backgroundColor: "var(--surface-elevated)" ,  backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = "var(--surface-overlay)"}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = "var(--surface-elevated)"}
            >
              Close
            </button>
          </div>
          <button
            onClick={handleCompare}
            className="rounded px-4 py-2 text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={!hasChanges}
          >
            Compare Traces
          </button>
        </div>

        {/* Trace Info Header */}
        <div className="grid grid-cols-2 gap-4 px-6 py-4" style={{ backgroundColor: "var(--surface-elevated)" }}>
          <div>
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Trace A</p>
            <p className="text-sm font-semibold" style={{ color: "var(--foreground-secondary)" }}>{traceA.trace_id}</p>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {formatTimestamp(traceA.created_at)} • {traceA.status}
            </p>
            <p className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>
              Duration: {traceA.duration_ms}ms
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Trace B</p>
            <p className="text-sm font-semibold" style={{ color: "var(--foreground-secondary)" }}>{traceB.trace_id}</p>
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {formatTimestamp(traceB.created_at)} • {traceB.status}
            </p>
            <p className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>
              Duration: {traceB.duration_ms}ms
            </p>
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="flex items-center gap-2 px-6 py-2" style={{ backgroundColor: "var(--surface-base)" }}>
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: "var(--foreground-secondary)" }}>
            <input
              type="checkbox"
              checked={showOnlyChanges}
              onChange={(e) => setShowOnlyChanges(e.target.checked)}
              className="rounded"
            />
            Show only differences
          </label>
        </div>

        {/* Sections */}
        <div className="flex-1 overflow-y-auto px-6 pb-6 space-y-6">
          {activeSection === "assets" && <AssetsDiffSection diff={diff.assets} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "plan" && <PlanDiffSection diff={diff.plan} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "toolcalls" && <ToolCallsDiffSection diff={diff.toolCalls} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "references" && <ReferencesDiffSection diff={diff.references} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "answers" && <AnswerBlocksDiffSection diff={diff.answers} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "ui" && <UIRenderDiffSection diff={diff.ui} showOnlyChanges={showOnlyChanges} />}
        </div>

        {/* Section Tabs */}
        <div className="flex border-t px-6 py-2" style={{ borderColor: "var(--border)" }}>
          <div className="flex gap-1 overflow-x-auto">
            {SECTIONS.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`px-4 py-2 rounded-t-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  activeSection === section.id
                    ? " text-white"
                    : " hover:"
                }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)" }}
                style={activeSection === section.id
                  ? { backgroundColor: "var(--surface-elevated)", color: "var(--background)" }
                  : { color: "var(--muted-foreground)" }}
                onMouseEnter={(e) => { if (activeSection !== section.id) e.currentTarget.style.backgroundColor = "var(--surface-overlay)"; }}
                onMouseLeave={(e) => { if (activeSection !== section.id) e.currentTarget.style.backgroundColor = "var(--surface-base)"; }}
              >
                <span className="mr-2">{section.icon}</span>
                {section.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
