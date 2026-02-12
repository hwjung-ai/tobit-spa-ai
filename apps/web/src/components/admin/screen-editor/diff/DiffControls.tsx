"use client";

export default function DiffControls() {
  return (
    <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-base)]">
      <div className="flex items-center gap-4">
        <div className="text-sm font-medium text-[var(--foreground-secondary)]">Compare Mode:</div>
        <div className="flex items-center gap-2">
          <span className="text-sm px-3 py-1.5 rounded bg-[var(--surface-elevated)] text-[var(--foreground-secondary)] font-medium border border-[var(--border)]">
            Draft vs Published
          </span>
        </div>
        <div className="text-xs text-[var(--foreground)]0 ml-auto">
          Showing differences between current draft and last published version
        </div>
      </div>
    </div>
  );
}
