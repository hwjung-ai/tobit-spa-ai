"use client";

import { useState, useEffect, useCallback } from "react";
import { OperationSetting, fetchApi, AuditLog } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";
import AuditLogTable from "./AuditLogTable";

interface SettingEditModalProps {
    setting: OperationSetting;
    onClose: () => void;
    onSuccess: () => void;
}

export default function SettingEditModal({ setting, onClose, onSuccess }: SettingEditModalProps) {
    const [value, setValue] = useState(
        typeof setting.value === "object"
            ? JSON.stringify(setting.value, null, 2)
            : String(setting.value)
    );
    const [isSaving, setIsSaving] = useState(false);
    const [errors, setErrors] = useState<string[]>([]);
    const [history, setHistory] = useState<AuditLog[]>([]);
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    const loadHistory = useCallback(async () => {
        setIsLoadingHistory(true);
        try {
            const response = await fetchApi<{ audit_logs: AuditLog[] }>(
                `/audit-log?resource_type=operation_setting&resource_id=${setting.key}&limit=10`
            );
            setHistory(response.data.audit_logs);
        } catch (err) {
            console.error("Failed to load setting history", err);
        } finally {
            setIsLoadingHistory(false);
        }
    }, [setting.key]);

    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    const handleSave = async () => {
        setErrors([]);
        setIsSaving(true);

        try {
            // Parse value if it looks like JSON
            let parsedValue: unknown = value;
            if (value.trim().startsWith("{") || value.trim().startsWith("[")) {
                try {
                    parsedValue = JSON.parse(value);
                } catch {
                    // Keep as string if JSON parse fails
                }
            } else if (!isNaN(Number(value)) && value.trim() !== "") {
                parsedValue = Number(value);
            } else if (value === "true" || value === "false") {
                parsedValue = value === "true";
            }

            await fetchApi(`/settings/operations/${setting.key}?updated_by=admin`, {
                method: "PUT",
                body: JSON.stringify({ value: parsedValue }),
            });

            onSuccess();
            onClose();
        } catch (err: unknown) {
            setErrors([err.message || "Failed to update setting"]);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
            <div className="bg-slate-900 rounded-lg border border-slate-800 max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-slate-800">
                    <h2 className="text-lg font-semibold text-white">Edit Setting: {setting.key}</h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors"
                    >
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-4 overflow-y-auto custom-scrollbar flex-1">
                    {errors.length > 0 && (
                        <ValidationAlert errors={errors} onClose={() => setErrors([])} />
                    )}

                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Key</label>
                            <p className="text-slate-300 font-mono text-sm mt-1">{setting.key}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Description</label>
                            <p className="text-slate-400 text-sm mt-1">{setting.description}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Default</label>
                            <p className="text-slate-400 text-sm mt-1 font-mono">
                                {typeof setting.default === "object"
                                    ? JSON.stringify(setting.default)
                                    : String(setting.default)}
                            </p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Current Source</label>
                            <p className="text-slate-300 text-sm mt-1">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${setting.source === "published" ? "bg-blue-950/50 text-blue-300" :
                                    setting.source === "env" ? "bg-yellow-950/50 text-yellow-300" :
                                        "bg-slate-800 text-slate-300"
                                    }`}>
                                    {setting.source}
                                </span>
                            </p>
                        </div>

                        {setting.allowed_values && setting.allowed_values.length > 0 && (
                            <div>
                                <label className="text-xs text-slate-500 uppercase tracking-wider">Allowed Values</label>
                                <p className="text-slate-400 text-sm mt-1">
                                    {setting.allowed_values.join(", ")}
                                </p>
                            </div>
                        )}

                        {setting.restart_required && (
                            <div className="flex items-center gap-2 p-3 bg-orange-950/30 border border-orange-800 rounded-lg">
                                <span className="text-orange-400">🔄</span>
                                <p className="text-orange-300 text-sm">
                                    Restart Required: This change will require a system restart to take effect
                                </p>
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                New Value
                            </label>
                            {setting.allowed_values && setting.allowed_values.length > 0 ? (
                                <select
                                    value={value}
                                    onChange={(e) => setValue(e.target.value)}
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-sky-500 transition-colors"
                                >
                                    {setting.allowed_values.map((val) => (
                                        <option key={String(val)} value={String(val)}>
                                            {String(val)}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <textarea
                                    value={value}
                                    onChange={(e) => setValue(e.target.value)}
                                    rows={4}
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            )}
                        </div>

                        <div className="pt-6 border-t border-slate-800">
                            <label className="text-xs text-slate-500 uppercase tracking-wider mb-4 block">Change History (Recent 10)</label>
                            {isLoadingHistory ? (
                                <div className="text-center py-4 text-slate-500 text-xs">Loading history...</div>
                            ) : (
                                <div className="bg-slate-950 rounded border border-slate-800 overflow-hidden">
                                    <AuditLogTable logs={history} />
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-800">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-6 py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors font-medium"
                    >
                        {isSaving ? "Saving..." : "Save"}
                    </button>
                </div>
            </div>
        </div>
    );
}
