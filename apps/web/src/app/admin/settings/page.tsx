"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
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
            <header className="admin-page-header">
                <div className="admin-page-header-content">
                    <div className="admin-header-status">
                        <div className="inline-flex rounded-xl border p-1 bg-surface-elevated border-border">
                            <button
                                onClick={() => setActiveTab("all")}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
                                    activeTab === "all"
                                        ? "bg-sky-600 text-white"
                                        : "bg-transparent text-primary hover:bg-surface-elevated"
                                )}
                            >
                                All Settings
                            </button>
                            <button
                                onClick={() => setActiveTab("llm")}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
                                    activeTab === "llm"
                                        ? "bg-sky-600 text-white"
                                        : "bg-transparent text-primary hover:bg-surface-elevated"
                                )}
                            >
                                LLM
                            </button>
                            <button
                                onClick={() => setActiveTab("auth")}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
                                    activeTab === "auth"
                                        ? "bg-sky-600 text-white"
                                        : "bg-transparent text-primary hover:bg-surface-elevated"
                                )}
                            >
                                Auth
                            </button>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-primary">
                            <span className="badge-primary">
                                Provider: <span className="font-semibold text-primary">{llmProvider}</span>
                            </span>
                            <span className="badge-primary">
                                Model: <span className="font-semibold text-primary">{llmModel}</span>
                            </span>
                            <span className="badge-primary">
                                Fallback: <span className="font-semibold text-primary">{llmFallbackEnabled ? "ON" : "OFF"}</span>
                            </span>
                        </div>
                    </div>
                </div>

                {/* Informational Banner */}
                <div className="admin-page-banner admin-page-banner--warning">
                    <div className="flex items-center gap-5">
                        <div className="w-12 h-12 rounded-full flex items-center justify-center shrink-0 shadow-lg bg-amber-500/20 text-amber-700 dark:text-amber-400">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <p className="mb-0.5 text-sm font-bold tracking-tight text-amber-900 dark:text-amber-300">Runtime Constraints Warning</p>
                            <p className="text-xs leading-relaxed text-slate-700 dark:text-amber-200">
                                Settings marked with 🔄 require a service restart. Changes to <span className="ml-1 text-sky-700 dark:text-sky-400">Published</span> values override
                                <span className="ml-1 text-amber-700 dark:text-amber-400">Environment</span> and <span className="ml-1 text-muted-standard">Default</span> configurations.
                            </p>
                        </div>
                        <button
                            onClick={() => refetch()}
                            className="px-4 py-2 transition-colors text-label-sm flex items-center gap-2 text-muted-standard hover:text-primary"
                        >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Sync
                        </button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="admin-header-tabs">
                    {activeTab === "llm" ? (
                        <p className="text-xs text-muted-standard">
                            LLM 운영 설정은 여기서 관리합니다. Provider, Base URL, Default/Fallback model, Timeout, Retry 정책을 수정할 수 있습니다.
                        </p>
                    ) : null}
                    {activeTab === "auth" ? (
                        <p className="text-xs text-muted-standard">
                            Runtime API 인증정책을 설정합니다. `jwt_only`, `jwt_or_api_key`, `api_key_only` 모드를 선택하고 필요한 scope를 관리할 수 있습니다.
                        </p>
                    ) : null}
                </div>
            </header>

            {/* Settings Grid Board */}
            <div className="insp-section overflow-hidden shadow-2xl">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-32 gap-4">
                        <div className="w-10 h-10 border-2 rounded-full animate-spin border-sky-500/20 border-t-sky-500"></div>
                        <p className="text-label-sm text-muted-standard">Synchronizing Master Config...</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-24">
                        <p className="font-medium mb-4 text-sm text-rose-600 dark:text-rose-400">{(error as Error)?.message || "Unable to load settings"}</p>
                        <button
                            onClick={() => refetch()}
                            className="px-8 py-2.5 text-white rounded-xl transition-all font-bold text-xs uppercase tracking-widest bg-surface-elevated hover:bg-surface-base"
                        >
                            Retry Connection
                        </button>
                    </div>
                ) : (
                    <div>
                        <SettingsTable settings={visibleSettings} onEdit={setSelectedSetting} />
                        <div className="p-4 flex justify-between items-center text-label-sm bg-surface-overlay/20 border-t border-border">
                            <span className="font-medium italic opacity-50 uppercase tracking-widest text-muted-standard">OperationSettingsProvider v1.0</span>
                            <span className="font-bold px-3 py-1 rounded-full border text-muted-standard bg-surface-overlay/40 border-border/30">
                                {visibleSettings.length} ACTIVE PARAMETERS
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {activeTab === "auth" ? (
                <div className="insp-section overflow-hidden shadow-2xl">
                    <div className="px-4 py-3 flex items-center justify-between border-b border-border">
                        <h3 className="text-label text-primary">Runtime API Auth Policy</h3>
                        <button
                            onClick={() => refetchPolicies()}
                            className="px-3 py-1.5 text-label-sm rounded-lg border transition border-border-muted text-primary hover:text-primary-foreground"
                        >
                            Refresh
                        </button>
                    </div>
                    {isPolicyLoading ? (
                        <div className="py-10 text-center text-sm text-muted-standard">Loading API policies...</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm bg-surface-overlay/40 text-muted-standard">
                                <thead>
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
                                            <tr key={api.id} className="border-t border-border">
                                                <td className="px-4 py-3 text-primary">
                                                    <div className="font-medium">{api.name}</div>
                                                    <div className="text-xs text-muted-standard">{api.method} {api.path}</div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <select
                                                        value={mode}
                                                        onChange={(e) =>
                                                            handlePolicyFieldChange(api.id, "auth_mode", e.target.value)
                                                        }
                                                        className="input-container"
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
                                                        className="input-container"
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() =>
                                                            handleSavePolicy(api.id, api.auth_mode, api.required_scopes)
                                                        }
                                                        disabled={savingPolicyId === api.id}
                                                        className="px-3 py-1.5 text-xs rounded-md disabled:opacity-50 bg-sky-600 text-white"
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
