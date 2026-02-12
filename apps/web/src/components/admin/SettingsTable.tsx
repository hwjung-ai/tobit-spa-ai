"use client";

import { OperationSetting } from "../../lib/adminUtils";

interface SettingsTableProps {
    settings: OperationSetting[];
    onEdit: (setting: OperationSetting) => void;
}

export default function SettingsTable({ settings, onEdit }: SettingsTableProps) {
    if (settings.length === 0) {
        return (
            <div className="text-center py-8 text-slate-600 dark:text-slate-400">
                No settings found
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800">
                        <th className="text-left py-3 px-4 text-slate-600 dark:text-slate-400 font-medium">Key</th>
                        <th className="text-left py-3 px-4 text-slate-600 dark:text-slate-400 font-medium">Value</th>
                        <th className="text-left py-3 px-4 text-slate-600 dark:text-slate-400 font-medium">Source</th>
                        <th className="text-left py-3 px-4 text-slate-600 dark:text-slate-400 font-medium text-center">Restart</th>
                        <th className="text-left py-3 px-4 text-slate-600 dark:text-slate-400 font-medium">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {settings.map((setting) => (
                        <tr
                            key={setting.key}
                            className="border-b border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800/40 transition-colors"
                        >
                            <td className="py-3 px-4 text-slate-900 dark:text-slate-50 font-mono text-xs">
                                {setting.key}
                            </td>
                            <td className="py-3 px-4 text-slate-900 dark:text-slate-50">
                                {typeof setting.value === "object"
                                    ? JSON.stringify(setting.value)
                                    : String(setting.value)}
                            </td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${setting.source === "published" ? "bg-blue-950/50 text-blue-300" :
                                        setting.source === "env" ? "bg-yellow-950/50 text-yellow-300" :
                                            "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-50"
                                    }`}>
                                    {setting.source}
                                </span>
                            </td>
                            <td className="py-3 px-4 text-center">
                                {setting.restart_required && (
                                    <span className="text-orange-400" title="Restart required">
                                        🔄
                                    </span>
                                )}
                            </td>
                            <td className="py-3 px-4">
                                <button
                                    onClick={() => onEdit(setting)}
                                    className="text-sky-400 hover:text-sky-300 text-xs transition-colors"
                                >
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