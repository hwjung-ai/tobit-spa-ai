import { useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchApi } from "../../lib/adminUtils";
import {
  computeTraceDiff,
} from "../../lib/traceDiffUtils";

interface TraceDiffViewProps {
  traceA: unknown;
  traceB: unknown;
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
          : "bg-slate-900/40 border-slate-700 text-slate-300";

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
        <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">Queries</span>
            <ChangeIndicator changeType={diff.queries.changeType} />
          </div>
          {diff.queries.before && (
            <div className="text-[11px] text-slate-400">
              Before: {diff.queries.before.length} queries
            </div>
          )}
          {diff.queries.after && (
            <div className="text-[11px] text-slate-400">
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
function AssetComparisonRow({ label, asset }: { label: string; asset: unknown }) {
  if (asset.changeType === "unchanged") {
    return null;
  }

  return (
    <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-slate-300">{label}</span>
        <ChangeIndicator changeType={asset.changeType} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Before */}
        {asset.before && (
          <div className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
            <p className="text-[10px] uppercase text-slate-500 mb-1">Before</p>
            <div className="text-[11px] text-slate-300 space-y-1">
              <div>
                <span className="text-slate-500">Name: </span>
                {asset.before.name}
              </div>
              <div>
                <span className="text-slate-500">Version: </span>
                {asset.before.version}
              </div>
              {asset.before.source && (
                <div>
                  <span className="text-slate-500">Source: </span>
                  {asset.before.source}
                </div>
              )}
            </div>
          </div>
        )}

        {/* After */}
        {asset.after && (
          <div className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
            <p className="text-[10px] uppercase text-slate-500 mb-1">After</p>
            <div className="text-[11px] text-slate-300 space-y-1">
              <div>
                <span className="text-slate-500">Name: </span>
                {asset.after.name}
              </div>
              <div>
                <span className="text-slate-500">Version: </span>
                {asset.after.version}
              </div>
              {asset.after.source && (
                <div>
                  <span className="text-slate-500">Source: </span>
                  {asset.after.source}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Changes */}
      {asset.changes && (
        <div className="bg-slate-900/60 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-amber-600 mb-2">Changes</p>
          <div className="text-[11px] text-slate-400 space-y-1">
            {Object.entries(asset.changes).map(([key, change]: [string, unknown]) => (
              <div key={key}>
                <span className="text-slate-500">{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before)}</span>
                <span className="text-slate-600"> → </span>
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
function PlanDiffSection({ diff, showOnlyChanges }: { diff: unknown; showOnlyChanges: boolean }) {
  if (showOnlyChanges && diff.changeType === "same") {
    return null;
  }

  return (
    <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-slate-300">Plan Comparison</span>
        <ChangeIndicator changeType={diff.changeType} />
      </div>

      {/* Validated Plan Changes */}
      {diff.validated && diff.validated.changeType === "modified" && (
        <div className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-slate-500 mb-2">Validated Plan Changes</p>
          <div className="text-[11px] text-slate-400 space-y-1 max-h-40 overflow-y-auto">
            {Object.entries(diff.validated.changes || {}).map(([key, change]: [string, unknown]) => (
              <div key={key} className="font-mono text-[10px]">
                <span className="text-slate-500">{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before).substring(0, 30)}...</span>
                <span className="text-slate-600"> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after).substring(0, 30)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Raw Plan Changes */}
      {diff.raw && diff.raw.changeType === "modified" && (
        <div className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-slate-500 mb-2">Raw Plan Changes</p>
          <div className="text-[11px] text-slate-400 space-y-1 max-h-40 overflow-y-auto">
            {Object.entries(diff.raw.changes || {}).map(([key, change]: [string, unknown]) => (
              <div key={key} className="font-mono text-[10px]">
                <span className="text-slate-500">{key}: </span>
                <span className="text-rose-300">{JSON.stringify(change.before).substring(0, 30)}...</span>
                <span className="text-slate-600"> → </span>
                <span className="text-emerald-300">{JSON.stringify(change.after).substring(0, 30)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {diff.changeType === "same" && (
        <div className="text-[11px] text-slate-500 italic">No plan changes detected</div>
      )}
    </div>
  );
}

/**
 * Section: Tool Calls Diff
 */
function ToolCallsDiffSection({ diff, showOnlyChanges }: { diff: unknown; showOnlyChanges: boolean }) {
  const hasChanges = diff.added.length > 0 || diff.removed.length > 0 || diff.modified.length > 0;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300">Tool Calls</span>
        <span className="text-[10px] text-slate-500">
          {diff.unchanged} unchanged, {diff.added.length + diff.removed.length + diff.modified.length} changed
        </span>
      </div>

      {/* Added */}
      {diff.added.length > 0 && (
        <div className="bg-blue-900/20 border border-blue-800 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-blue-400 mb-2">Added ({diff.added.length})</p>
          <div className="text-[11px] text-blue-300 space-y-1">
            {diff.added.map((tool: unknown, idx: number) => (
              <div key={idx}>
                <span className="font-mono">{tool.tool_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Removed */}
      {diff.removed.length > 0 && (
        <div className="bg-rose-900/20 border border-rose-800 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-rose-400 mb-2">Removed ({diff.removed.length})</p>
          <div className="text-[11px] text-rose-300 space-y-1">
            {diff.removed.map((tool: unknown, idx: number) => (
              <div key={idx}>
                <span className="font-mono">{tool.tool_name}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modified */}
      {diff.modified.length > 0 && (
        <div className="bg-amber-900/20 border border-amber-800 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-amber-400 mb-2">Modified ({diff.modified.length})</p>
          <div className="text-[11px] text-amber-300 space-y-1">
            {diff.modified.map((tool: unknown, idx: number) => (
              <div key={idx} className="font-mono">
                {tool.tool_name}
                {tool.changes && Object.keys(tool.changes).length > 0 && (
                  <span className="text-slate-500"> ({Object.keys(tool.changes).length} fields)</span>
                )}
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
function ReferencesDiffSection({ diff, showOnlyChanges }: { diff: unknown; showOnlyChanges: boolean }) {
  const hasChanges = Object.values(diff.byType).some((rt: unknown) => rt.added.length > 0 || rt.removed.length > 0);

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300">References</span>
        <span className="text-[10px] text-slate-500">
          {diff.total_before} → {diff.total_after}
        </span>
      </div>

      {Object.entries(diff.byType).map(([type, refs]: [string, unknown]) => (
        <div key={type} className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
          <p className="text-[10px] uppercase text-slate-500 mb-2">
            {type} ({refs.before.length} → {refs.after.length})
          </p>

          <div className="space-y-2">
            {refs.added.length > 0 && (
              <div className="text-[11px] text-emerald-400">
                <span className="text-slate-500">Added: </span>
                {refs.added.join(", ")}
              </div>
            )}
            {refs.removed.length > 0 && (
              <div className="text-[11px] text-rose-400">
                <span className="text-slate-500">Removed: </span>
                {refs.removed.join(", ")}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Section: Answer Blocks Diff
 */
function AnswerBlocksDiffSection({ diff, showOnlyChanges }: { diff: unknown; showOnlyChanges: boolean }) {
  const hasChanges = diff.blocks.some((b: unknown) => b.changeType !== "unchanged");

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300">Answer Blocks</span>
        <span className="text-[10px] text-slate-500">
          {diff.block_count_before} → {diff.block_count_after}
        </span>
      </div>

      <div className="space-y-2">
        {diff.blocks.map((block: unknown, idx: number) => (
          <div key={idx} className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-slate-300">Block {block.index}</span>
              <ChangeIndicator changeType={block.changeType} />
            </div>

            {block.before && (
              <div className="text-[10px] text-rose-300">
                Before: {block.before.type}
                {block.before.title && ` - ${block.before.title}`}
              </div>
            )}
            {block.after && (
              <div className="text-[10px] text-emerald-300">
                After: {block.after.type}
                {block.after.title && ` - ${block.after.title}`}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Section: UI Render Diff
 */
function UIRenderDiffSection({ diff, showOnlyChanges }: { diff: unknown; showOnlyChanges: boolean }) {
  const hasChanges = diff.changes.length > 0 || diff.error_count_before !== diff.error_count_after;

  if (showOnlyChanges && !hasChanges) {
    return null;
  }

  return (
    <div className="bg-slate-950/50 border border-slate-800 rounded-xl px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-300">UI Render</span>
        <span className="text-[10px] text-slate-500">
          {diff.component_count_before} → {diff.component_count_after} components
        </span>
      </div>

      {/* Error count */}
      {diff.error_count_before !== diff.error_count_after && (
        <div
          className={`rounded px-3 py-2 text-[11px] ${
            diff.error_count_after > diff.error_count_before ? "bg-rose-900/20 text-rose-400" : "bg-emerald-900/20 text-emerald-400"
          }`}
        >
          Errors: {diff.error_count_before} → {diff.error_count_after}
        </div>
      )}

      {/* Changes */}
      {diff.changes.map((change: unknown, idx: number) => (
        <div key={idx} className="bg-slate-900/40 border border-slate-800 rounded px-3 py-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-semibold text-slate-300">Component {change.index}</span>
            <ChangeIndicator changeType={change.changeType} />
          </div>

          {change.before && (
            <div className="text-[10px] text-slate-400">
              Before: {change.before.component_name} ({change.before.ok ? "ok" : "error"})
            </div>
          )}
          {change.after && (
            <div className="text-[10px] text-slate-400">
              After: {change.after.component_name} ({change.after.ok ? "ok" : "error"})
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/**
 * Main TraceDiffView Component
 */
export default function TraceDiffView({ traceA, traceB, onClose }: TraceDiffViewProps) {
  const [selectedSection, setSelectedSection] = useState<Section>("assets");
  const [showOnlyChanges, setShowOnlyChanges] = useState(false);
  const [rcaLoading, setRcaLoading] = useState(false);
  const [rcaError, setRcaError] = useState<string | null>(null);
  const router = useRouter();

  const traceDiff = useMemo(() => computeTraceDiff(traceA, traceB), [traceA, traceB]);

  const handleRunRca = useCallback(async () => {
    setRcaLoading(true);
    setRcaError(null);
    try {
      const response = await fetchApi<{ trace_id: string }>("/ops/rca", {
        method: "POST",
        body: JSON.stringify({
          mode: "diff",
          baseline_trace_id: traceA.trace_id,
          candidate_trace_id: traceB.trace_id,
        }),
      });
      router.push(`/admin/inspector?trace_id=${encodeURIComponent(response.data.trace_id)}`);
      onClose(); // Close the diff view after kicking off RCA
    } catch (err: unknown) {
      setRcaError(err.message || "Failed to run RCA analysis.");
    } finally {
      setRcaLoading(false);
    }
  }, [traceA, traceB, router, onClose]);

  const sectionHasChanges = (section: Section): boolean => {
    switch (section) {
      case "assets":
        return traceDiff.applied_assets.prompt.changeType !== "unchanged" ||
          traceDiff.applied_assets.policy.changeType !== "unchanged" ||
          traceDiff.applied_assets.mapping.changeType !== "unchanged" ||
          traceDiff.applied_assets.queries.changeType !== "unchanged";
      case "plan":
        return traceDiff.plan.changeType === "modified";
      case "toolcalls":
        return traceDiff.tool_calls.added.length > 0 ||
          traceDiff.tool_calls.removed.length > 0 ||
          traceDiff.tool_calls.modified.length > 0;
      case "references":
        return Object.values(traceDiff.references.byType).some((rt: unknown) => rt.added.length > 0 || rt.removed.length > 0);
      case "answers":
        return traceDiff.answer_blocks.blocks.some((b: unknown) => b.changeType !== "unchanged");
      case "ui":
        return traceDiff.ui_render.changes.length > 0 || traceDiff.ui_render.error_count_before !== traceDiff.ui_render.error_count_after;
      default:
        return false;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-950 border border-slate-800 rounded-2xl w-[90%] h-[90vh] max-w-6xl flex flex-col">
        {/* Header */}
        <div className="border-b border-slate-800 px-6 py-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Compare Traces</h2>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors text-xl"
            >
              ✕
            </button>
          </div>

          {/* Trace headers */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-900/40 border border-slate-800 rounded-lg px-4 py-3">
              <div className="text-[10px] uppercase text-slate-500 mb-1">Trace A</div>
              <div className="text-sm font-mono text-slate-200">{traceA.trace_id}</div>
              <div className="text-[11px] text-slate-400 mt-1">
                {formatTimestamp(traceA.created_at)} - {traceA.duration_ms}ms
              </div>
              <div className={`inline-block mt-2 px-2 py-1 rounded-full text-[10px] border ${getStatusBadgeClass(traceA.status)}`}>
                {traceA.status}
              </div>
            </div>

            <div className="bg-slate-900/40 border border-slate-800 rounded-lg px-4 py-3">
              <div className="text-[10px] uppercase text-slate-500 mb-1">Trace B</div>
              <div className="text-sm font-mono text-slate-200">{traceB.trace_id}</div>
              <div className="text-[11px] text-slate-400 mt-1">
                {formatTimestamp(traceB.created_at)} - {traceB.duration_ms}ms
              </div>
              <div className={`inline-block mt-2 px-2 py-1 rounded-full text-[10px] border ${getStatusBadgeClass(traceB.status)}`}>
                {traceB.status}
              </div>
            </div>
          </div>

          {/* RCA Button */}
          <div className="flex items-center gap-4">
            <button
              onClick={handleRunRca}
              disabled={rcaLoading}
              className="px-4 py-2 rounded-lg bg-fuchsia-600 hover:bg-fuchsia-700 text-xs uppercase tracking-wider font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {rcaLoading ? "Analyzing..." : "▶︎ Run RCA"}
            </button>
            {rcaError && <div className="text-xs text-rose-400">{rcaError}</div>}
          </div>

          {/* Summary & Toggle */}
          <div className="flex items-center justify-between">
            <div className="text-[11px] text-slate-400">
              <span className="font-semibold text-white">{traceDiff.summary.total_changes}</span> total changes in{" "}
              <span className="font-semibold text-white">{traceDiff.summary.sections_with_changes.length}</span> section(s)
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showOnlyChanges}
                onChange={(e) => setShowOnlyChanges(e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-900"
              />
              <span className="text-[11px] text-slate-400">Show only changes</span>
            </label>
          </div>
        </div>

        {/* Section tabs */}
        <div className="border-b border-slate-800 px-6 py-3 flex gap-2 overflow-x-auto">
          {SECTIONS.map((section) => {
            const hasChanges = sectionHasChanges(section.id);
            const isSelected = selectedSection === section.id;

            return (
              <button
                key={section.id}
                onClick={() => setSelectedSection(section.id)}
                className={`px-3 py-2 rounded-lg text-[11px] font-semibold uppercase tracking-wider transition-colors whitespace-nowrap flex items-center gap-1 ${
                  isSelected
                    ? "bg-blue-600 text-white"
                    : "bg-slate-900/40 text-slate-400 hover:bg-slate-800/40"
                } ${hasChanges ? "ring-1 ring-amber-600/50" : ""}`}
              >
                {section.icon}
                {section.label}
                {hasChanges && <span className="text-amber-400">•</span>}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {selectedSection === "assets" && (
            <AssetsDiffSection diff={traceDiff.applied_assets} showOnlyChanges={showOnlyChanges} />
          )}
          {selectedSection === "plan" && (
            <PlanDiffSection diff={traceDiff.plan} showOnlyChanges={showOnlyChanges} />
          )}
          {selectedSection === "toolcalls" && (
            <ToolCallsDiffSection diff={traceDiff.tool_calls} showOnlyChanges={showOnlyChanges} />
          )}
          {selectedSection === "references" && (
            <ReferencesDiffSection diff={traceDiff.references} showOnlyChanges={showOnlyChanges} />
          )}
          {selectedSection === "answers" && (
            <AnswerBlocksDiffSection diff={traceDiff.answer_blocks} showOnlyChanges={showOnlyChanges} />
          )}
          {selectedSection === "ui" && (
            <UIRenderDiffSection diff={traceDiff.ui_render} showOnlyChanges={showOnlyChanges} />
          )}
        </div>
      </div>
    </div>
  );
}
