"use client";

export default function DiffControls() {
  return (
    <div className="px-4 py-3 border-b border-slate-800 bg-slate-950">
      <div className="flex items-center gap-4">
        <div className="text-sm font-medium text-slate-300">Compare Mode:</div>
        <div className="flex items-center gap-2">
          <span className="text-sm px-3 py-1.5 rounded bg-slate-800 text-slate-300 font-medium border border-slate-700">
            Draft vs Published
          </span>
        </div>
        <div className="text-xs text-slate-500 ml-auto">
          Showing differences between current draft and last published version
        </div>
      </div>
    </div>
  );
}
