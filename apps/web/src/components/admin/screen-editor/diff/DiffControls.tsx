"use client";

export default function DiffControls() {
  return (
    <div className="px-4 py-3 border-b border-slate-200 bg-white">
      <div className="flex items-center gap-4">
        <div className="text-sm font-medium text-slate-700">Compare Mode:</div>
        <div className="flex items-center gap-2">
          <span className="text-sm px-3 py-1.5 rounded bg-slate-100 text-slate-700 font-medium">
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
