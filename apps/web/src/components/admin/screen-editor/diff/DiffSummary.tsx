"use client";

import { ScreenDiff, getDiffSummaryText } from "@/lib/ui-screen/screen-diff-utils";

interface DiffSummaryProps {
  diff: ScreenDiff;
}

export default function DiffSummary({ diff }: DiffSummaryProps) {
  const { added, removed, modified, unchanged } = diff.summary;

  return (
    <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-700">
          <span className="font-medium">Changes:</span>
          {added > 0 && <span className="ml-3 text-green-700">+{added} added</span>}
          {removed > 0 && <span className="ml-3 text-red-700">-{removed} removed</span>}
          {modified > 0 && <span className="ml-3 text-amber-700">~{modified} modified</span>}
          {unchanged > 0 && <span className="ml-3 text-slate-600">{unchanged} unchanged</span>}
        </div>
        {added === 0 && removed === 0 && modified === 0 && (
          <div className="text-xs text-slate-500">No changes detected</div>
        )}
      </div>
    </div>
  );
}
