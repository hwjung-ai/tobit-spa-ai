import { useState, useMemo, useCallback } from "react";
import { fetchApi } from "../../lib/adminUtils";
import { cn } from "../../lib/utils";
import {
  computeTraceDiff,
  type AssetsDiff,
  type AssetInfo,
  type DiffItem,
  type PlanDiff,
  type ToolCallsDiff,
  type ReferencesDiff,
  type AnswerBlocksDiff,
  type UIRenderDiff,
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
      ? "bg-sky-900/40 border-sky-700 text-sky-200"
      : changeType === "removed"
        ? "bg-rose-900/40 border-rose-700 text-rose-200"
        : changeType === "modified"
          ? "bg-amber-900/40 border-amber-700 text-amber-200"
          : "border-variant";
  const label = changeType === "added" ? "+" : changeType === "removed" ? "−" : changeType === "modified" ? "~" : "=";
  return <span className={cn("inline-flex items-center px-2 py-1 rounded-full text-tiny border", indicatorClass)}>{label}</span>;
}

function getReferencesChangeSummary(diff: ReferencesDiff) {
  const totals = Object.values(diff.byType).reduce(
    (acc, entry) => {
      acc.added += entry.added.length;
      acc.removed += entry.removed.length;
      return acc;
    },
    { added: 0, removed: 0 }
  );
  const changed = totals.added + totals.removed;
  const changeType = changed === 0 ? "unchanged" : "modified";
  return { ...totals, changed, changeType };
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
        <div className="rounded-xl px-4 py-3 space-y-2 bg-surface-overlay border border-variant">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-muted-foreground">Queries</span>
            <ChangeIndicator changeType={diff.queries.changeType} />
          </div>
          {diff.queries.before && (
            <div className="text-xs text-muted-foreground">
              Before: {diff.queries.before.length} queries
            </div>
          )}
          {diff.queries.after && (
            <div className="text-xs text-muted-foreground">
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
    <div className="rounded-xl px-4 py-3 space-y-2 bg-surface-overlay border border-variant">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-muted-foreground">{label}</span>
        <ChangeIndicator changeType={asset.changeType} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {/* Before */}
        {asset.before && (
          <div className="rounded px-3 py-2 bg-surface-overlay border border-variant">
            <p className="text-tiny uppercase mb-1 text-muted-foreground">Before</p>
            <div className="text-xs space-y-1 text-muted-foreground">
              <span className="text-muted-foreground">Name: </span>
              {asset.before.name}
            </div>
            <div>
              <span className="text-muted-foreground">Version: </span>
              {asset.before.version}
            </div>
            {asset.before.source && (
              <div>
                <span className="text-muted-foreground">Source: </span>
                {asset.before.source}
              </div>
            )}
          </div>
        )}
        {/* After */}
        {asset.after && (
          <div className="rounded px-3 py-2 bg-surface-overlay border border-variant">
            <p className="text-tiny uppercase mb-1 text-muted-foreground">After</p>
            <div className="text-xs space-y-1 text-muted-foreground">
              <span className="text-muted-foreground">Name: </span>
              {asset.after.name}
            </div>
            <div>
              <span className="text-muted-foreground">Version: </span>
              {asset.after.version}
            </div>
            {asset.after.source && (
              <div>
                <span className="text-muted-foreground">Source: </span>
                {asset.after.source}
              </div>
            )}
          </div>
        )}
      </div>
      {/* Changes */}
      {asset.changes && (
        <div className="rounded px-3 py-2 bg-surface-overlay">
          <p className="text-tiny uppercase text-amber-600 mb-2">Changes</p>
          <div className="text-xs space-y-1 text-muted-foreground">
            {Object.entries(asset.changes).map(([key, change]) => (
              <div key={key}>
                <span className="text-muted-foreground">{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before)}</span>
                <span className="text-muted-foreground"> → </span>
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
    <div className="rounded-xl px-4 py-3 space-y-3 bg-surface-overlay border border-variant">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-muted-foreground">Plan Comparison</span>
        <ChangeIndicator changeType={diff.changeType} />
      </div>
      {/* Validated Plan Changes */}
      {diff.validated && diff.validated.changeType === "modified" && (
        <div className="rounded px-3 py-2 bg-surface-overlay border border-variant">
          <p className="text-tiny uppercase mb-2 text-muted-foreground">Validated Plan Changes</p>
          <div className="text-xs space-y-1 max-h-40 overflow-y-auto text-muted-foreground">
            {Object.entries(diff.validated.changes || {}).map(([key, change]: [string, { before: unknown; after: unknown }]) => (
              <div key={key} className="font-mono text-tiny">
                <span className="text-muted-foreground">{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before).substring(0, 30)}...</span>
                <span className="text-muted-foreground"> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after).substring(0, 30)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* Raw Plan Changes */}
      {diff.raw && diff.raw.changeType === "modified" && (
        <div className="rounded px-3 py-2 bg-surface-overlay border border-variant">
          <p className="text-tiny uppercase mb-2 text-muted-foreground">Raw Plan Changes</p>
          <div className="text-xs space-y-1 max-h-40 overflow-y-auto text-muted-foreground">
            {Object.entries(diff.raw.changes || {}).map(([key, change]: [string, { before: unknown; after: unknown }]) => (
              <div key={key} className="font-mono text-tiny">
                <span className="text-muted-foreground">{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before).substring(0, 30)}...</span>
                <span className="text-muted-foreground"> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after).substring(0, 30)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {diff.changeType === "same" && (
        <div className="text-xs italic text-muted-foreground">No plan changes detected</div>
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
    <div className="rounded-xl px-4 py-3 space-y-3 bg-surface-overlay border border-variant">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-muted-foreground">Tool Calls</span>
        <span className="text-tiny text-muted-foreground">
          {diff.unchanged} unchanged, {diff.added.length + diff.removed.length + diff.modified.length} changed
        </span>
      </div>
      {/* Added */}
      {diff.added.length > 0 && (
        <div className="rounded px-3 py-2 bg-sky-900/20 border border-sky-700/50">
          <p className="text-tiny uppercase text-sky-400 mb-2">Added ({diff.added.length})</p>
          <div className="text-xs space-y-1 text-sky-200">
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
  const summary = getReferencesChangeSummary(diff);
  const hasChanges = summary.changed > 0;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3 bg-surface-overlay border border-variant">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-muted-foreground">References</span>
        <ChangeIndicator changeType={summary.changeType} />
      </div>
      <div className="text-xs space-y-1 text-muted-foreground">
        <div>
          Before: {diff.total_before} / After: {diff.total_after}
        </div>
        {summary.added > 0 && (
          <div>
            <span className="text-emerald-400">+ Added {summary.added} references</span>
          </div>
        )}
        {summary.removed > 0 && (
          <div>
            <span className="text-rose-400">- Removed {summary.removed} references</span>
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
  const added = diff.blocks.filter((b) => b.changeType === "added");
  const removed = diff.blocks.filter((b) => b.changeType === "removed");
  const modified = diff.blocks.filter((b) => b.changeType === "modified");
  const unchanged = diff.blocks.filter((b) => b.changeType === "unchanged");
  const hasChanges = added.length > 0 || removed.length > 0 || modified.length > 0;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3 bg-surface-overlay border border-variant">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-muted-foreground">Answer Blocks</span>
        <ChangeIndicator changeType={hasChanges ? "modified" : "unchanged"} />
      </div>
      <div className="text-xs space-y-1 text-muted-foreground">
        <div>
          Before: {diff.block_count_before} / After: {diff.block_count_after}
        </div>
        {hasChanges && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-mono text-tiny mb-2 text-rose-300">Removed</div>
              {removed.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.before?.type ?? "unknown"}</div>
              ))}
            </div>
            <div>
              <div className="font-mono text-tiny mb-2 text-emerald-300">Added</div>
              {added.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.after?.type ?? "unknown"}</div>
              ))}
            </div>
          </div>
        )}
        {modified.length > 0 && (
          <div className="font-mono text-tiny text-muted-foreground">
            Modified: {modified.length}
          </div>
        )}
        {!hasChanges && (
          <div className="text-xs italic text-muted-foreground">No block changes detected</div>
        )}
        <div className="text-tiny">Unchanged: {unchanged.length}</div>
      </div>
    </div>
  );
}

/**
 * Section: UI Render Diff
 */
function UIRenderDiffSection({ diff, showOnlyChanges }: { diff: UIRenderDiff; showOnlyChanges: boolean }) {
  const added = diff.changes.filter((c) => c.changeType === "added");
  const removed = diff.changes.filter((c) => c.changeType === "removed");
  const modified = diff.changes.filter((c) => c.changeType === "modified");
  const hasChanges = added.length > 0 || removed.length > 0 || modified.length > 0 || diff.error_count_before !== diff.error_count_after;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="rounded-xl px-4 py-3 space-y-3 bg-surface-overlay border border-variant">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-muted-foreground">UI Render</span>
        <ChangeIndicator changeType={hasChanges ? "modified" : "unchanged"} />
      </div>
      <div className="text-xs space-y-1 text-muted-foreground">
        <div>
          Components: {diff.component_count_before} {"->"} {diff.component_count_after}
        </div>
        <div>
          Errors: {diff.error_count_before} {"->"} {diff.error_count_after}
        </div>
        {hasChanges && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="font-mono text-tiny mb-2 text-rose-300">Removed</div>
              {removed.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.before?.component_name ?? "unknown"}</div>
              ))}
            </div>
            <div>
              <div className="font-mono text-tiny mb-2 text-emerald-300">Added</div>
              {added.map((block, idx) => (
                <div key={idx} className="text-sm mb-1">{block.after?.component_name ?? "unknown"}</div>
              ))}
            </div>
          </div>
        )}
        {modified.length > 0 && (
          <div className="font-mono text-tiny text-muted-foreground">
            Modified: {modified.length}
          </div>
        )}
        {!hasChanges && (
          <div className="text-xs italic text-muted-foreground">No UI render changes detected</div>
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
    return diff.summary.total_changes > 0;
  }, [diff]);

  const handleCompare = useCallback(async () => {
    if (!traceA.trace_id || !traceB.trace_id) {
      return;
    }

    try {
      const response = await fetchApi<{ diff?: unknown }>("/traces/compare", {
        method: "POST",
        body: JSON.stringify({
          trace_a_id: traceA.trace_id,
          trace_b_id: traceB.trace_id,
        }),
      });

      if (response.data?.diff) {
        // Refresh the page to show comparison
        window.location.reload();
      }
    } catch (error) {
      console.error("Failed to compare traces:", error);
    }
  }, [traceA.trace_id, traceB.trace_id]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80">
      <div className="rounded-2xl shadow-2xl w-full max-w-7xl flex overflow-hidden bg-surface-base">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-variant px-6 py-4">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-foreground">Trace Comparison</h2>
            <button
              onClick={onClose}
              className="rounded p-2 text-sm transition-colors bg-surface-elevated text-foreground hover:bg-surface-overlay"
            >
              Close
            </button>
          </div>
          <button
            onClick={handleCompare}
            className="rounded px-4 py-2 text-sm font-semibold bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={!hasChanges}
          >
            Compare Traces
          </button>
        </div>

        {/* Trace Info Header */}
        <div className="grid grid-cols-2 gap-4 px-6 py-4 bg-surface-elevated">
          <div>
            <p className="text-sm uppercase tracking-wider text-muted-foreground">Trace A</p>
            <p className="text-sm font-semibold text-muted-foreground">{traceA.trace_id}</p>
            <p className="text-xs text-muted-foreground">
              {formatTimestamp(traceA.created_at)} • {traceA.status}
            </p>
            <p className="text-tiny text-muted-foreground">
              Duration: {traceA.duration_ms}ms
            </p>
          </div>
          <div>
            <p className="text-sm uppercase tracking-wider text-muted-foreground">Trace B</p>
            <p className="text-sm font-semibold text-muted-foreground">{traceB.trace_id}</p>
            <p className="text-xs text-muted-foreground">
              {formatTimestamp(traceB.created_at)} • {traceB.status}
            </p>
            <p className="text-tiny text-muted-foreground">
              Duration: {traceB.duration_ms}ms
            </p>
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="flex items-center gap-2 px-6 py-2 bg-surface-base">
          <label className="flex items-center gap-2 text-sm cursor-pointer text-muted-foreground">
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
          {activeSection === "assets" && <AssetsDiffSection diff={diff.applied_assets} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "plan" && <PlanDiffSection diff={diff.plan} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "toolcalls" && <ToolCallsDiffSection diff={diff.tool_calls} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "references" && <ReferencesDiffSection diff={diff.references} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "answers" && <AnswerBlocksDiffSection diff={diff.answer_blocks} showOnlyChanges={showOnlyChanges} />}
          {activeSection === "ui" && <UIRenderDiffSection diff={diff.ui_render} showOnlyChanges={showOnlyChanges} />}
        </div>

        {/* Section Tabs */}
        <div className="flex border-t border-variant px-6 py-2">
          <div className="flex gap-1 overflow-x-auto">
            {SECTIONS.map((section) => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  "px-4 py-2 rounded-t-lg text-sm font-medium whitespace-nowrap transition-colors",
                  activeSection === section.id
                    ? "bg-surface-elevated text-foreground"
                    : "text-muted-foreground hover:bg-surface-overlay"
                )}
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