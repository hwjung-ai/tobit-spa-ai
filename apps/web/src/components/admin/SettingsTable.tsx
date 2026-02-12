"use client";

import { OperationSetting } from "../../lib/adminUtils";

interface SettingsTableProps {
    settings: OperationSetting[];
    onEdit: (setting: OperationSetting) => void;
}

export default function SettingsTable({ settings, onEdit }: SettingsTableProps) {
    if (settings.length === 0) {
        return (
            <div className="text-center py-8  dark:" style={{color: "var(--muted-foreground)"}}>
                No settings found
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b  dark:" style={{borderColor: "var(--border)"}}>
                        <th className="text-left py-3 px-4  dark: font-medium" style={{color: "var(--muted-foreground)"}}>Key</th>
                        <th className="text-left py-3 px-4  dark: font-medium" style={{color: "var(--muted-foreground)"}}>Value</th>
                        <th className="text-left py-3 px-4  dark: font-medium" style={{color: "var(--muted-foreground)"}}>Source</th>
                        <th className="text-left py-3 px-4  dark: font-medium text-center" style={{color: "var(--muted-foreground)"}}>Restart</th>
                        <th className="text-left py-3 px-4  dark: font-medium" style={{color: "var(--muted-foreground)"}}>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {settings.map((setting) => (
                        <tr
                            key={setting.key}
                            className="border-b  dark: hover: dark:hover:/40 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                        >
                            <td className="py-3 px-4 dark: font-mono text-xs" style={{color: "var(--foreground)"}}>
                                {setting.key}
                            </td>
                            <td className="py-3 px-4 dark:" style={{color: "var(--foreground)"}}>
                                {typeof setting.value === "object"
                                    ? JSON.stringify(setting.value)
                                    : String(setting.value)}
                            </td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${setting.source === "published" ? "bg-sky-950/50 text-sky-300" :
                                        setting.source === "env" ? "bg-yellow-950/50 text-yellow-300" :
                                            " dark:  dark:"
                                    }`} style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground)"}}>
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