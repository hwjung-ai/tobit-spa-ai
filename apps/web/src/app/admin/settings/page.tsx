"use client";

import { useEffect, useState } from "react";
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
            const response = await fetchApi<{ settings: OperationSetting[] }>("/settings/operations");
            return response.data.settings;
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
        <div className="p-6">
            <div className="max-w-7xl mx-auto">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Operation Settings</h1>
                    <p className="text-slate-400 text-sm max-w-2xl leading-relaxed">
                        Manage global parameters and operational behavior. Priority order: <span className="text-blue-400 font-bold">Published</span> &gt; <span className="text-yellow-400 font-bold">Env</span> &gt; <span className="text-slate-400 font-bold">Default</span>.
                    </p>
                </div>

                {/* Global Warning for Restart */}
                <div className="bg-orange-500/5 border border-orange-500/20 rounded-xl p-4 mb-8 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-orange-500/10 flex items-center justify-center text-orange-500 shrink-0">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <div>
                        <p className="text-orange-200 text-sm font-bold">Attention Required</p>
                        <p className="text-orange-300/70 text-xs">Settings marked with 🔄 will not take effect until the application service is restarted.</p>
                    </div>
                </div>

                {/* Settings Table Board */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-sm">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-32 gap-4">
                            <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                            <p className="text-slate-500 text-sm font-medium">Synchronizing settings stack...</p>
                        </div>
                    ) : error ? (
                        <div className="text-center py-24">
                            <p className="text-red-400 font-medium mb-4">{(error as any)?.message || "Unable to load settings"}</p>
                            <button
                                onClick={() => refetch()}
                                className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-all"
                            >
                                Reconnect to API
                            </button>
                        </div>
                    ) : (
                        <div className="animate-in fade-in duration-500">
                            <SettingsTable settings={settings} onEdit={setSelectedSetting} />

                            <div className="p-4 bg-slate-950/30 border-t border-slate-800/50 flex justify-between items-center">
                                <p className="text-[10px] text-slate-500 italic">Total {settings.length} parameters managed by OperationSettingsService</p>
                                <button
                                    onClick={() => refetch()}
                                    className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1 transition-colors font-bold uppercase tracking-widest"
                                >
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                    </svg>
                                    Sync Now
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Edit Overlay */}
            {selectedSetting && (
                <SettingEditModal
                    setting={selectedSetting}
                    onClose={() => setSelectedSetting(null)}
                    onSuccess={handleEditSuccess}
                />
            )}

            {/* Instant Notification */}
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
