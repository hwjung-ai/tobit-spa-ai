"use client";

import { useEffect, useState } from "react";
import { OperationSetting, fetchApi } from "../../../lib/adminUtils";
import SettingsTable from "../../../components/admin/SettingsTable";
import SettingEditModal from "../../../components/admin/SettingEditModal";
import Toast from "../../../components/admin/Toast";

export default function SettingsPage() {
    const [settings, setSettings] = useState<OperationSetting[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedSetting, setSelectedSetting] = useState<OperationSetting | null>(null);
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" } | null>(null);

    const loadSettings = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await fetchApi<{ settings: OperationSetting[] }>("/settings/operations");
            setSettings(response.data.settings);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load settings");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadSettings();
    }, []);

    const handleEditSuccess = () => {
        loadSettings();

        const setting = selectedSetting;
        if (setting?.restart_required) {
            setToast({
                message: "✅ Setting updated successfully\n🔄 Restart required for this change to take effect",
                type: "warning",
            });
        } else {
            setToast({
                message: "Setting updated successfully",
                type: "success",
            });
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
            <div className="max-w-7xl mx-auto">
                <div className="mb-6">
                    <h1 className="text-2xl font-semibold text-white mb-2">Operation Settings</h1>
                    <p className="text-slate-400 text-sm">
                        Manage system operation settings
                    </p>
                </div>

                {/* Warning Banner */}
                <div className="mb-6 p-4 bg-orange-950/30 border border-orange-800 rounded-lg">
                    <div className="flex items-center gap-2">
                        <svg className="h-5 w-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <p className="text-orange-300 text-sm">
                            Some settings require a system restart (shown with 🔄 icon)
                        </p>
                    </div>
                </div>

                {/* Settings Table */}
                <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                    {isLoading ? (
                        <div className="text-center py-8 text-slate-400">Loading settings...</div>
                    ) : error ? (
                        <div className="text-center py-8 text-red-400">{error}</div>
                    ) : (
                        <SettingsTable settings={settings} onEdit={setSelectedSetting} />
                    )}
                </div>
            </div>

            {/* Edit Modal */}
            {selectedSetting && (
                <SettingEditModal
                    setting={selectedSetting}
                    onClose={() => setSelectedSetting(null)}
                    onSuccess={handleEditSuccess}
                />
            )}

            {/* Toast */}
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onDismiss={() => setToast(null)}
                />
            )}
        </div>
    );
}
