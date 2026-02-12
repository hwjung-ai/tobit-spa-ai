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
    const [activeTab, setActiveTab] = useState<"all" | "llm" | "auth">("all");
    const [policyDrafts, setPolicyDrafts] = useState<
        Record<string, { auth_mode: string; required_scopes: string }>
    >({});
    const [savingPolicyId, setSavingPolicyId] = useState<string | null>(null);

    const { data: settings = [], isLoading, error, refetch } = useQuery({
        queryKey: ["settings"],
        queryFn: async () => {
            try {
                const response = await fetchApi<{ settings: Record<string, Omit<OperationSetting, "key">> }>("/api/settings/operations");
                // ResponseEnvelope.success(data={settings: {...}})
                const settingsData = response.data?.settings;
                if (!settingsData || typeof settingsData !== "object") {
                    console.warn("[Settings] Invalid response data:", response);
                    return [];
                }
                return Object.entries(settingsData).map(([key, setting]) => ({
                    key,
                    ...setting,
                })) as OperationSetting[];
            } catch (err) {
                console.error("[Settings] Failed to fetch:", err);
                throw err;
            }
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

    const llmSettings = settings.filter((setting) => setting.key.startsWith("llm_"));
    const authSettings = settings.filter((setting) => setting.key.startsWith("api_auth_"));
    const visibleSettings =
        activeTab === "llm" ? llmSettings : activeTab === "auth" ? authSettings : settings;
    const llmProvider = String(
        llmSettings.find((setting) => setting.key === "llm_provider")?.value ?? "openai"
    );
    const llmModel = String(
        llmSettings.find((setting) => setting.key === "llm_default_model")?.value ?? "-"
    );
    const llmFallbackEnabled = Boolean(
        llmSettings.find((setting) => setting.key === "llm_enable_fallback")?.value
    );
    const { data: apiPolicies = [], isLoading: isPolicyLoading, refetch: refetchPolicies } = useQuery({
        queryKey: ["settings", "api-auth-policies"],
        enabled: activeTab === "auth",
        queryFn: async () => {
            const response = await fetchApi<{ apis: Array<Record<string, unknown>> }>("/api/api-manager/apis");
            const rows = Array.isArray(response.data?.apis) ? response.data.apis : [];
            return rows.map((item) => ({
                id: String(item.id || ""),
                name: String(item.name || ""),
                method: String(item.method || "GET"),
                path: String(item.path || ""),
                auth_mode: String(item.auth_mode || "jwt_only"),
                required_scopes: Array.isArray(item.required_scopes)
                    ? (item.required_scopes as string[])
                    : [],
                is_enabled: Boolean(item.is_enabled),
            }));
        },
    });

    const handlePolicyFieldChange = (apiId: string, field: "auth_mode" | "required_scopes", value: string) => {
        setPolicyDrafts((prev) => ({
            ...prev,
            [apiId]: {
                auth_mode: prev[apiId]?.auth_mode ?? "jwt_only",
                required_scopes: prev[apiId]?.required_scopes ?? "",
                [field]: value,
            },
        }));
    };

    const handleSavePolicy = async (apiId: string, fallbackMode: string, fallbackScopes: string[]) => {
        const draft = policyDrafts[apiId];
        const authMode = draft?.auth_mode ?? fallbackMode;
        const scopeText = draft?.required_scopes ?? fallbackScopes.join(", ");
        const requiredScopes = scopeText
            .split(",")
            .map((v) => v.trim())
            .filter(Boolean);
        try {
            setSavingPolicyId(apiId);
            await fetchApi(`/api/api-manager/apis/${apiId}/auth-policy`, {
                method: "PUT",
                body: JSON.stringify({
                    auth_mode: authMode,
                    required_scopes: requiredScopes,
                }),
            });
            setToast({
                message: "API auth policy updated successfully.",
                type: "success",
            });
            await refetchPolicies();
        } catch (err) {
            setToast({
                message: err instanceof Error ? err.message : "Failed to update API auth policy",
                type: "error",
            });
        } finally {
            setSavingPolicyId(null);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Informational Banner */}
            <div className="bg-orange-50 dark:bg-orange-500/5 border border-orange-200 dark:border-orange-500/20 rounded-2xl p-5 flex items-center gap-5 backdrop-blur-sm">
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

            <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/40 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="inline-flex rounded-xl border border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-950/70 p-1">
                        <button
                            onClick={() => setActiveTab("all")}
                            className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.15em] transition ${
                                activeTab === "all"
                                    ? "rounded-lg bg-sky-600 text-white"
                                    : "bg-slate-200 text-slate-700 hover:bg-slate-300 hover:text-white dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
                            }`}
                        >
                            All Settings
                        </button>
                        <button
                            onClick={() => setActiveTab("llm")}
                            className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.15em] transition ${
                                activeTab === "llm"
                                    ? "rounded-lg bg-sky-600 text-white"
                                    : "bg-slate-200 text-slate-700 hover:bg-slate-300 hover:text-white dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
                            }`}
                        >
                            LLM
                        </button>
                        <button
                            onClick={() => setActiveTab("auth")}
                            className={`px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.15em] transition ${
                                activeTab === "auth"
                                    ? "rounded-lg bg-sky-600 text-white"
                                    : "bg-slate-200 text-slate-700 hover:bg-slate-300 hover:text-white dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
                            }`}
                        >
                            Auth
                        </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-700 dark:text-slate-300">
                        <span className="rounded-full border border-slate-700 bg-slate-950/60 px-3 py-1 text-slate-300">
                            Provider: <span className="font-semibold text-white">{llmProvider}</span>
                        </span>
                        <span className="rounded-full border border-slate-700 bg-slate-950/60 px-3 py-1 text-slate-300">
                            Model: <span className="font-semibold text-white">{llmModel}</span>
                        </span>
                        <span className="rounded-full border border-slate-700 bg-slate-950/60 px-3 py-1 text-slate-300">
                            Fallback: <span className="font-semibold text-white">{llmFallbackEnabled ? "ON" : "OFF"}</span>
                        </span>
                    </div>
                </div>
                {activeTab === "llm" ? (
                    <p className="mt-3 text-xs text-slate-400">
                        LLM 운영 설정은 여기서 관리합니다. Provider, Base URL, Default/Fallback model, Timeout, Retry 정책을 수정할 수 있습니다.
                    </p>
                ) : null}
                {activeTab === "auth" ? (
                    <p className="mt-3 text-xs text-slate-400">
                        Runtime API 인증정책을 설정합니다. `jwt_only`, `jwt_or_api_key`, `api_key_only` 모드를 선택하고 필요한 scope를 관리할 수 있습니다.
                    </p>
                ) : null}
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
                        <SettingsTable settings={visibleSettings} onEdit={setSelectedSetting} />
                        <div className="p-4 bg-slate-950/20 border-t border-slate-800/50 flex justify-between items-center text-[10px]">
                            <span className="text-slate-500 font-medium italic opacity-50 uppercase tracking-widest">OperationSettingsProvider v1.0</span>
                            <span className="text-slate-400 font-bold px-3 py-1 bg-slate-800/40 rounded-full border border-slate-700/30">
                                {visibleSettings.length} ACTIVE PARAMETERS
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {activeTab === "auth" ? (
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                    <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                        <h3 className="text-xs uppercase tracking-[0.2em] text-slate-300 font-semibold">Runtime API Auth Policy</h3>
                        <button
                            onClick={() => refetchPolicies()}
                            className="px-3 py-1.5 text-[10px] uppercase tracking-[0.2em] rounded-lg border border-slate-700 text-slate-300 hover:text-white"
                        >
                            Refresh
                        </button>
                    </div>
                    {isPolicyLoading ? (
                        <div className="py-10 text-center text-slate-400 text-sm">Loading API policies...</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-slate-950/40 text-slate-400">
                                    <tr>
                                        <th className="text-left px-4 py-2">API</th>
                                        <th className="text-left px-4 py-2">Mode</th>
                                        <th className="text-left px-4 py-2">Required Scopes</th>
                                        <th className="text-right px-4 py-2">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {apiPolicies.map((api) => {
                                        const draft = policyDrafts[api.id];
                                        const mode = draft?.auth_mode ?? api.auth_mode;
                                        const scopesText = draft?.required_scopes ?? api.required_scopes.join(", ");
                                        return (
                                            <tr key={api.id} className="border-t border-slate-800/70">
                                                <td className="px-4 py-3 text-slate-200">
                                                    <div className="font-medium">{api.name}</div>
                                                    <div className="text-xs text-slate-400">{api.method} {api.path}</div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <select
                                                        value={mode}
                                                        onChange={(e) =>
                                                            handlePolicyFieldChange(api.id, "auth_mode", e.target.value)
                                                        }
                                                        className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-100"
                                                    >
                                                        <option value="jwt_only">jwt_only</option>
                                                        <option value="jwt_or_api_key">jwt_or_api_key</option>
                                                        <option value="api_key_only">api_key_only</option>
                                                    </select>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <input
                                                        value={scopesText}
                                                        onChange={(e) =>
                                                            handlePolicyFieldChange(api.id, "required_scopes", e.target.value)
                                                        }
                                                        placeholder="api:execute, api:read"
                                                        className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-slate-100"
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() =>
                                                            handleSavePolicy(api.id, api.auth_mode, api.required_scopes)
                                                        }
                                                        disabled={savingPolicyId === api.id}
                                                        className="px-3 py-1.5 text-xs rounded-md bg-sky-600 text-white disabled:opacity-50"
                                                    >
                                                        {savingPolicyId === api.id ? "Saving..." : "Save"}
                                                    </button>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            ) : null}

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
                    onDismiss={() => setToast(null)}
                />
            )}
        </div>
    );
}
