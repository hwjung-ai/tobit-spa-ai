"use client";

import { useState } from "react";
import { OperationSetting, fetchApi } from "../../../lib/adminUtils";
import SettingsTable from "../../../components/admin/SettingsTable";
import SettingEditModal from "../../../components/admin/SettingEditModal";
import Toast from "../../../components/admin/Toast";
import { useQuery } from "@tanstack/react-query";

export default function SettingsPage() {
    const [selectedSetting, setSelectedSetting] = useState<OperationSetting | null>(null);
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" } | null>(null);

    const { data: settings = [], isLoading, error, refetch } = useQuery({
        queryKey: ["settings"],
        queryFn: async () => {
            const response = await fetchApi<{ settings: Record<string, Omit<OperationSetting, "key">> }>("/settings/operations");
            const settingsData = response.data.settings;
            return Object.entries(settingsData).map(([key, setting]) => ({
                key,
                ...setting,
            })) as OperationSetting[];
        }
    });

    const handleEditSuccess = () => {
        refetch();

        if (selectedSetting?.restart_required) {
            setToast({
                message: "Setting updated. System restart is REQUIRED for changes to take effect.",
                type: "warning",
            });
        } else {
            setToast({
                message: "Setting has been successfully updated.",
                type: "success",
            });
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Informational Banner */}
            <div className="bg-orange-500/5 border border-orange-500/20 rounded-2xl p-5 flex items-center gap-5 backdrop-blur-sm">
                <div className="w-12 h-12 rounded-full bg-orange-500/10 flex items-center justify-center text-orange-500 shrink-0 shadow-lg shadow-orange-900/10">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <div className="flex-1">
                    <p className="text-orange-200 text-sm font-bold tracking-tight mb-0.5">Runtime Constraints Warning</p>
                    <p className="text-orange-300/60 text-xs leading-relaxed">
                        Settings marked with 🔄 require a service restart. Changes to <span className="text-blue-400 font-bold">Published</span> values override
                        <span className="text-yellow-400 font-bold ml-1">Environment</span> and <span className="text-slate-400 font-bold ml-1">Default</span> configurations.
                    </p>
                </div>
                <button
                    onClick={() => refetch()}
                    className="px-4 py-2 text-slate-400 hover:text-white transition-colors text-[10px] font-bold uppercase tracking-[0.2em] flex items-center gap-2"
                >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Sync
                </button>
            </div>

            {/* Settings Grid Board */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-32 gap-4">
                        <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                        <p className="text-slate-500 text-[10px] font-bold uppercase tracking-[0.25em]">Synchronizing Master Config...</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-24">
                        <p className="text-red-400 font-medium mb-4 text-sm">{(error as Error)?.message || "Unable to load settings"}</p>
                        <button
                            onClick={() => refetch()}
                            className="px-8 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all font-bold text-xs uppercase tracking-widest"
                        >
                            Retry Connection
                        </button>
                    </div>
                ) : (
                    <div>
                        <SettingsTable settings={settings} onEdit={setSelectedSetting} />
                        <div className="p-4 bg-slate-950/20 border-t border-slate-800/50 flex justify-between items-center text-[10px]">
                            <span className="text-slate-500 font-medium italic opacity-50 uppercase tracking-widest">OperationSettingsProvider v1.0</span>
                            <span className="text-slate-400 font-bold px-3 py-1 bg-slate-800/40 rounded-full border border-slate-700/30">
                                {settings.length} ACTIVE PARAMETERS
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Overlays */}
            {selectedSetting && (
                <SettingEditModal
                    setting={selectedSetting}
                    onClose={() => setSelectedSetting(null)}
                    onSuccess={handleEditSuccess}
                />
            )}

            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
        </div>
    );
}
