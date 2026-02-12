"use client";

import { OperationSetting } from "../../lib/adminUtils";

interface SettingsTableProps {
    settings: OperationSetting[];
    onEdit: (setting: OperationSetting) => void;
}

export default function SettingsTable({ settings, onEdit }: SettingsTableProps) {
  if (settings.length === 0) {
    return <div className="py-8 text-center text-sm text-slate-600 dark:text-slate-400">No settings found</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800">
            <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-400">Key</th>
            <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-400">Value</th>
            <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-400">Source</th>
            <th className="px-4 py-3 text-center font-medium text-slate-600 dark:text-slate-400">Restart</th>
            <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-400">Actions</th>
          </tr>
        </thead>
        <tbody>
          {settings.map((setting) => (
            <tr
              key={setting.key}
              className="border-b border-slate-200 bg-white transition-colors hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-950 dark:hover:bg-slate-900/40"
            >
              <td className="px-4 py-3 font-mono text-xs text-slate-900 dark:text-slate-100">{setting.key}</td>
              <td className="px-4 py-3 text-slate-900 dark:text-slate-100">
                {typeof setting.value === "object" ? JSON.stringify(setting.value) : String(setting.value)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex rounded px-2 py-1 text-xs font-medium ${
                    setting.source === "published"
                      ? "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300"
                      : setting.source === "env"
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                        : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                  }`}
                >
                  {setting.source}
                </span>
              </td>
              <td className="px-4 py-3 text-center">
                {setting.restart_required && (
                  <span className="text-orange-500 dark:text-orange-400" title="Restart required">
                    🔄
                  </span>
                )}
              </td>
              <td className="px-4 py-3">
                <button onClick={() => onEdit(setting)} className="text-xs text-sky-600 transition-colors hover:text-sky-500 dark:text-sky-400 dark:hover:text-sky-300">
                  Edit
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
