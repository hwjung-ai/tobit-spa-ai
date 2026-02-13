"use client";

export default function DiffControls() {
  return (
    <div className="px-4 py-3 border-b border-variant bg-surface-base">
      <div className="flex items-center gap-4">
        <div className="text-sm font-medium text-foreground-secondary">Compare Mode:</div>
        <div className="flex items-center gap-2">
          <span className="text-sm px-3 py-2 rounded bg-surface-elevated text-foreground-secondary font-medium border border-variant">
            Draft vs Published
          </span>
        </div>
        <div className="text-xs text-foreground0 ml-auto">
          Showing differences between current draft and last published version
        </div>
      </div>
    </div>
  );
}
