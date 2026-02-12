"use client";

import { ScreenDiff } from "@/lib/ui-screen/screen-diff-utils";

interface DiffSummaryProps {
  diff: ScreenDiff;
}

export default function DiffSummary({ diff }: DiffSummaryProps) {
  const { added, removed, modified, unchanged } = diff.summary;

  return (
    <div className="px-4 py-3 bg-[var(--surface-base)] border-b border-[var(--border)]">
      <div className="flex items-center justify-between">
        <div className="text-sm text-[var(--foreground-secondary)]">
          <span className="font-medium">Changes:</span>
          {added > 0 && <span className="ml-3 text-green-400">+{added} added</span>}
          {removed > 0 && <span className="ml-3 text-red-400">-{removed} removed</span>}
          {modified > 0 && <span className="ml-3 text-amber-400">~{modified} modified</span>}
          {unchanged > 0 && <span className="ml-3 text-[var(--foreground)]0">{unchanged} unchanged</span>}
        </div>
        {added === 0 && removed === 0 && modified === 0 && (
          <div className="text-xs text-[var(--foreground)]0">No changes detected</div>
        )}
      </div>
    </div>
  );
}
