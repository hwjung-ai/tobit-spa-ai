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
            <div className="rounded-2xl border p-5 flex items-center gap-5 backdrop-blur-sm" style={{backgroundColor: "rgba(245, 158, 11, 0.1)", borderColor: "rgba(245, 158, 11, 0.3)"}}>
                <div className="w-12 h-12 rounded-full flex items-center justify-center shrink-0 shadow-lg" style={{backgroundColor: "rgba(245, 158, 11, 0.2)", color: "var(--warning)"}}>
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <div className="flex-1">
                    <p className="text-sm font-bold tracking-tight mb-0.5" style={{color: "var(--warning)"}}>Runtime Constraints Warning</p>
                    <p className="text-xs leading-relaxed" style={{color: "rgb(71, 85, 105)"}}>
                        Settings marked with 🔄 require a service restart. Changes to <span style={{color: "var(--primary)"}}>Published</span> values override
                        <span style={{color: "var(--warning)"}} className="ml-1">Environment</span> and <span style={{color: "rgb(71, 85, 105)"}} className="ml-1">Default</span> configurations.
                    </p>
                </div>
                <button
                    onClick={() => refetch()}
                    className="px-4 py-2 transition-colors text-[10px] font-bold uppercase tracking-[0.2em] flex items-center gap-2"
                    style={{color: "rgb(71, 85, 105)"}}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "var(--foreground)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "var(--muted-foreground)"; }}
                >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Sync
                </button>
            </div>

            <div className="rounded-2xl border p-4" style={{borderColor: "rgb(203, 213, 225)", backgroundColor: "rgb(248, 250, 252)"}}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="inline-flex rounded-xl border p-1" style={{borderColor: "var(--border-muted)", backgroundColor: "var(--muted-background)"}}>
                        <button
                            onClick={() => setActiveTab("all")}
                            className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition"
                            style={{backgroundColor: activeTab === "all" ? "var(--primary)" : "transparent", color: activeTab === "all" ? "var(--primary-foreground)" : "var(--foreground)", borderRadius: "8px"}}
                        >
                            All Settings
                        </button>
                        <button
                            onClick={() => setActiveTab("llm")}
                            className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition"
                            style={{backgroundColor: activeTab === "llm" ? "var(--primary)" : "transparent", color: activeTab === "llm" ? "var(--primary-foreground)" : "var(--foreground)", borderRadius: "8px"}}
                        >
                            LLM
                        </button>
                        <button
                            onClick={() => setActiveTab("auth")}
                            className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition"
                            style={{backgroundColor: activeTab === "auth" ? "var(--primary)" : "transparent", color: activeTab === "auth" ? "var(--primary-foreground)" : "var(--foreground)", borderRadius: "8px"}}
                        >
                            Auth
                        </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs" style={{color: "rgb(15, 23, 42)"}}>
                        <span className="rounded-full border px-3 py-1" style={{borderColor: "var(--border-muted)", backgroundColor: "rgba(2, 6, 23, 0.6)", color: "rgb(71, 85, 105)"}}>
                            Provider: <span className="font-semibold" style={{color: "rgb(15, 23, 42)"}}>{llmProvider}</span>
                        </span>
                        <span className="rounded-full border px-3 py-1" style={{borderColor: "var(--border-muted)", backgroundColor: "rgba(2, 6, 23, 0.6)", color: "rgb(71, 85, 105)"}}>
                            Model: <span className="font-semibold" style={{color: "rgb(15, 23, 42)"}}>{llmModel}</span>
                        </span>
                        <span className="rounded-full border px-3 py-1" style={{borderColor: "var(--border-muted)", backgroundColor: "rgba(2, 6, 23, 0.6)", color: "rgb(71, 85, 105)"}}>
                            Fallback: <span className="font-semibold" style={{color: "rgb(15, 23, 42)"}}>{llmFallbackEnabled ? "ON" : "OFF"}</span>
                        </span>
                    </div>
                </div>
                {activeTab === "llm" ? (
                    <p className="mt-3 text-xs" style={{color: "rgb(71, 85, 105)"}}>
                        LLM 운영 설정은 여기서 관리합니다. Provider, Base URL, Default/Fallback model, Timeout, Retry 정책을 수정할 수 있습니다.
                    </p>
                ) : null}
                {activeTab === "auth" ? (
                    <p className="mt-3 text-xs" style={{color: "rgb(71, 85, 105)"}}>
                        Runtime API 인증정책을 설정합니다. `jwt_only`, `jwt_or_api_key`, `api_key_only` 모드를 선택하고 필요한 scope를 관리할 수 있습니다.
                    </p>
                ) : null}
            </div>

            {/* Settings Grid Board */}
            <div className="rounded-2xl border overflow-hidden shadow-2xl" style={{backgroundColor: "rgba(2, 6, 23, 0.4)", borderColor: "rgb(203, 213, 225)"}}>
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-32 gap-4">
                        <div className="w-10 h-10 border-2 rounded-full animate-spin" style={{borderColor: "rgba(var(--primary-rgb), 0.2)", borderTopColor: "var(--primary)"}}></div>
                        <p className="text-[10px] font-bold uppercase tracking-wider" style={{color: "rgb(71, 85, 105)"}}>Synchronizing Master Config...</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-24">
                        <p className="font-medium mb-4 text-sm" style={{color: "var(--error)"}}>{(error as Error)?.message || "Unable to load settings"}</p>
                        <button
                            onClick={() => refetch()}
                            className="px-8 py-2.5 text-white rounded-xl transition-all font-bold text-xs uppercase tracking-widest"
                            style={{backgroundColor: "rgb(241, 245, 249)"}}
                        >
                            Retry Connection
                        </button>
                    </div>
                ) : (
                    <div>
                        <SettingsTable settings={visibleSettings} onEdit={setSelectedSetting} />
                        <div className="p-4 flex justify-between items-center text-[10px]" style={{backgroundColor: "rgba(2, 6, 23, 0.2)", borderTop: "1px solid var(--border)"}}>
                            <span className="font-medium italic opacity-50 uppercase tracking-widest" style={{color: "rgb(71, 85, 105)"}}>OperationSettingsProvider v1.0</span>
                            <span className="font-bold px-3 py-1 rounded-full border" style={{color: "rgb(71, 85, 105)", backgroundColor: "rgba(2, 6, 23, 0.4)", borderColor: "rgba(51, 65, 85, 0.3)"}}>
                                {visibleSettings.length} ACTIVE PARAMETERS
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {activeTab === "auth" ? (
                <div className="rounded-2xl border overflow-hidden shadow-2xl" style={{backgroundColor: "rgba(2, 6, 23, 0.4)", borderColor: "rgb(203, 213, 225)"}}>
                    <div className="px-4 py-3 flex items-center justify-between" style={{borderBottom: "1px solid var(--border)"}}>
                        <h3 className="text-xs uppercase tracking-[0.2em] font-semibold" style={{color: "rgb(15, 23, 42)"}}>Runtime API Auth Policy</h3>
                        <button
                            onClick={() => refetchPolicies()}
                            className="px-3 py-1.5 text-[10px] uppercase tracking-[0.2em] rounded-lg border transition"
                            style={{borderColor: "var(--border-muted)", color: "rgb(15, 23, 42)"}}
                            onMouseEnter={(e) => { e.currentTarget.style.color = "var(--primary-foreground)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.color = "var(--foreground)"; }}
                        >
                            Refresh
                        </button>
                    </div>
                    {isPolicyLoading ? (
                        <div className="py-10 text-center text-sm" style={{color: "rgb(71, 85, 105)"}}>Loading API policies...</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead style={{backgroundColor: "rgba(2, 6, 23, 0.4)", color: "rgb(71, 85, 105)"}}>
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
                                            <tr key={api.id} style={{borderTop: "1px solid rgba(30, 41, 59, 0.7)"}}>
                                                <td className="px-4 py-3" style={{color: "rgb(15, 23, 42)"}}>
                                                    <div className="font-medium">{api.name}</div>
                                                    <div className="text-xs" style={{color: "rgb(71, 85, 105)"}}>{api.method} {api.path}</div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <select
                                                        value={mode}
                                                        onChange={(e) =>
                                                            handlePolicyFieldChange(api.id, "auth_mode", e.target.value)
                                                        }
                                                        className="w-full rounded-md border px-2 py-1.5"
                                                        style={{borderColor: "var(--border-muted)", backgroundColor: "rgba(2, 6, 23, 0.5)", color: "rgb(15, 23, 42)"}}
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
                                                        className="w-full rounded-md border px-2 py-1.5"
                                                        style={{borderColor: "var(--border-muted)", backgroundColor: "rgba(2, 6, 23, 0.5)", color: "rgb(15, 23, 42)"}}
                                                    />
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    <button
                                                        onClick={() =>
                                                            handleSavePolicy(api.id, api.auth_mode, api.required_scopes)
                                                        }
                                                        disabled={savingPolicyId === api.id}
                                                        className="px-3 py-1.5 text-xs rounded-md disabled:opacity-50"
                                                        style={{backgroundColor: "var(--primary)", color: "var(--primary-foreground)"}}
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
