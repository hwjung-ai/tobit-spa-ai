"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";

interface CreateToolModalProps {
    onClose: () => void;
    onSuccess: (assetId: string) => void;
}

interface ApiManagerItem {
    id: string;
    name: string;
    method: string;
    path: string;
    description?: string | null;
    scope?: string | null;
    mode?: string | null;
    is_enabled?: boolean;
}

const TOOL_TYPES = [
    { value: "database_query", label: "Database Query", description: "Execute SQL queries against data sources" },
    { value: "http_api", label: "HTTP API", description: "Call external REST APIs" },
    { value: "graph_query", label: "Graph Query", description: "Query graph databases (Neo4j, etc.)" },
    { value: "python_script", label: "Python Script", description: "Execute custom Python scripts" },
] as const;

const DEFAULT_INPUT_SCHEMA = {
    type: "object",
    properties: {
        query: { type: "string", description: "Search query or input" }
    },
    required: ["query"]
};

const DEFAULT_TOOL_CONFIG = {
    timeout_ms: 30000,
    max_retries: 3
};

export default function CreateToolModal({ onClose, onSuccess }: CreateToolModalProps) {
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [toolType, setToolType] = useState<string>("database_query");
    const [catalogRef, setCatalogRef] = useState<string>("");
    const [toolConfig, setToolConfig] = useState(JSON.stringify(DEFAULT_TOOL_CONFIG, null, 2));
    const [inputSchema, setInputSchema] = useState(JSON.stringify(DEFAULT_INPUT_SCHEMA, null, 2));
    const [selectedApiId, setSelectedApiId] = useState<string>("");
    const [isCreating, setIsCreating] = useState(false);
    const [errors, setErrors] = useState<string[]>([]);

    const apiBaseUrl = useMemo(() => {
        const raw = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        return raw.replace(/\/+$/, "");
    }, []);

    // Fetch available catalogs
    const { data: catalogsData } = useQuery({
        queryKey: ["admin-catalogs-for-tool"],
        queryFn: async () => {
            const response = await fetchApi("/asset-registry/catalogs?status=published");
            return response.data?.assets || [];
        },
    });

    const { data: apiManagerApis = [] } = useQuery({
        queryKey: ["api-manager-apis"],
        queryFn: async () => {
            const response = await fetchApi<{ apis: ApiManagerItem[] }>("/api-manager/apis");
            return (response.data as { apis?: ApiManagerItem[] })?.apis || [];
        },
    });

    const handleApiSelection = (apiId: string) => {
        setSelectedApiId(apiId);
        const selected = apiManagerApis.find((api) => api.id === apiId);
        if (!selected) {
            return;
        }

        const executeUrl = `${apiBaseUrl}/api-manager/apis/${selected.id}/execute`;
        const apiToolConfig = {
            url: executeUrl,
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body_template: {
                params: "params",
            },
        };

        const apiInputSchema = {
            type: "object",
            properties: {
                params: {
                    type: "object",
                    description: `Parameters for API Manager execute: ${selected.name} (${selected.method} ${selected.path})`,
                },
            },
            required: ["params"],
        };

        setToolType("http_api");
        setToolConfig(JSON.stringify(apiToolConfig, null, 2));
        setInputSchema(JSON.stringify(apiInputSchema, null, 2));
    };

    const handleCreate = async () => {
        const validationErrors: string[] = [];

        if (!name.trim()) {
            validationErrors.push("Tool name is required");
        }

        if (!description.trim()) {
            validationErrors.push("Description is required (LLM uses this for tool selection)");
        }

        let parsedConfig: Record<string, unknown>;
        let parsedInputSchema: Record<string, unknown>;

        try {
            parsedConfig = JSON.parse(toolConfig);
        } catch {
            validationErrors.push("Tool Config must be valid JSON");
        }

        try {
            parsedInputSchema = JSON.parse(inputSchema);
        } catch {
            validationErrors.push("Input Schema must be valid JSON");
        }

        if (validationErrors.length > 0) {
            setErrors(validationErrors);
            return;
        }

        setIsCreating(true);
        setErrors([]);

        try {
            const payload: any = {
                name,
                description,
                tool_type: toolType,
                tool_config: parsedConfig!,
                tool_input_schema: parsedInputSchema!,
                tool_output_schema: null,
                created_by: "admin",
            };

            // Add catalog reference if selected
            if (catalogRef.trim()) {
                payload.tool_catalog_ref = catalogRef;
            }

            const response = await fetchApi<{ asset: { asset_id: string } }>("/asset-registry/tools", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            // API returns { data: { asset: { asset_id, ... } } }
            const assetId = (response.data as any)?.asset?.asset_id;
            if (!assetId) {
                throw new Error("No asset_id in response");
            }
            onSuccess(assetId);
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to create tool"]);
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
            <div className=" rounded-2xl border  max-w-2xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                <div className="flex items-center justify-between p-6 border-b " style={{ borderColor: "var(--border)" }}>
                    <div>
                        <h2 className="text-xl font-bold text-white">Create New Tool</h2>
                        <p className=" text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>Define a new orchestration tool asset</p>
                    </div>
                    <button
                        onClick={onClose}
                        className=" hover:text-white transition-colors" style={{ color: "var(--muted-foreground)" }}
                    >
                        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-6 overflow-y-auto flex-1">
                    {errors.length > 0 && (
                        <ValidationAlert errors={errors} onClose={() => setErrors([])} />
                    )}

                    <div className="space-y-6">
                        {/* Tool Name */}
                        <div>
                            <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                Tool Name
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. equipment_search, inventory_list"
                                className="w-full px-4 py-3  border  rounded-xl  placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all font-mono" style={{ borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
                                autoFocus
                            />
                            <p className=" text-xs mt-1 ml-1" style={{ color: "var(--muted-foreground)" }}>Use snake_case for tool names</p>
                        </div>

                        {/* Tool Type */}
                        <div>
                            <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                Tool Type
                            </label>
                            <div className="grid grid-cols-2 gap-3">
                                {TOOL_TYPES.map((type) => (
                                    <button
                                        key={type.value}
                                        onClick={() => setToolType(type.value)}
                                        className={`px-4 py-3 rounded-xl border text-left transition-all ${
                                            toolType === type.value
                                                ? "bg-sky-600/20 border-sky-500 shadow-lg shadow-sky-900/10"
                                                : "  hover:"
                                        }`} style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                                    >
                                        <span className={`block font-bold text-sm ${
                                            toolType === type.value ? "text-sky-400" : ""
                                        }`} style={{ color: "var(--foreground-secondary)" }}>
                                            {type.label}
                                        </span>
                                        <span className="block  text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                                            {type.description}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* API Manager Selection (HTTP API Tools) */}
                        {toolType === "http_api" && (
                            <div>
                                <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                    API Manager API (Optional)
                                </label>
                                <select
                                    value={selectedApiId}
                                    onChange={(e) => handleApiSelection(e.target.value)}
                                    className="w-full px-4 py-3  border  rounded-xl  focus:outline-none focus:border-sky-500 transition-all" style={{ borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
                                >
                                    <option value="">-- Select API Manager API --</option>
                                    {apiManagerApis.map((api) => (
                                        <option key={api.id} value={api.id}>
                                            {api.name} ({api.method} {api.path})
                                        </option>
                                    ))}
                                </select>
                                <p className=" text-xs mt-1 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                    선택 시 Tool Config/Input Schema가 API 실행용으로 자동 채워집니다.
                                </p>
                            </div>
                        )}

                        {/* Description */}
                        <div>
                            <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                Description
                                <span className="text-amber-500 ml-2 normal-case tracking-normal">
                                    (Important for LLM tool selection)
                                </span>
                            </label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Describe what this tool does and include keywords that help LLM select it. E.g., 'Search equipment inventory. Keywords: equipment, 장비, machine, 설비'"
                                rows={3}
                                className="w-full px-4 py-3  border  rounded-xl  placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all resize-none" style={{ borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
                            />
                        </div>

                        {/* Catalog Reference (Optional) */}
                        <div>
                            <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                Database Catalog (Optional)
                            </label>
                            <select
                                value={catalogRef}
                                onChange={(e) => setCatalogRef(e.target.value)}
                                className="w-full px-4 py-3  border  rounded-xl  focus:outline-none focus:border-sky-500 transition-all" style={{ borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
                            >
                                <option value="">-- No Catalog Selected --</option>
                                {catalogsData?.map((catalog: any) => (
                                    <option key={catalog.asset_id} value={catalog.name}>
                                        {catalog.name} (Tables: {catalog.content?.catalog?.tables?.length || 0})
                                    </option>
                                ))}
                            </select>
                            <p className=" text-xs mt-1 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                💡 Select a catalog to provide database schema information to LLM for accurate SQL generation
                            </p>
                        </div>

                        {/* Tool Config */}
                        <div>
                            <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                Tool Configuration (JSON)
                            </label>
                            <textarea
                                value={toolConfig}
                                onChange={(e) => setToolConfig(e.target.value)}
                                rows={5}
                                className="w-full px-4 py-3  border  rounded-xl  font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none" style={{ borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
                            />
                        </div>

                        {/* Input Schema */}
                        <div>
                            <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{ color: "var(--muted-foreground)" }}>
                                Input Schema (JSON Schema)
                            </label>
                            <textarea
                                value={inputSchema}
                                onChange={(e) => setInputSchema(e.target.value)}
                                rows={6}
                                className="w-full px-4 py-3  border  rounded-xl  font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none" style={{ borderColor: "var(--border)" ,  color: "var(--foreground)" ,  backgroundColor: "var(--surface-base)" }}
                            />
                        </div>
                    </div>
                </div>

                <div className="p-6 border-t  flex gap-3" style={{ borderColor: "var(--border)" }}>
                    <button
                        onClick={onClose}
                        className="flex-1 py-3  hover:text-white transition-colors font-bold uppercase tracking-widest text-xs" style={{ color: "var(--muted-foreground)" }}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={isCreating}
                        className="flex-[2] py-3 bg-sky-600 hover:bg-sky-500 disabled: disabled: text-white rounded-xl transition-all font-bold shadow-lg shadow-sky-900/20 active:scale-95" style={{ color: "var(--muted-foreground)" ,  backgroundColor: "var(--surface-elevated)" }}
                    >
                        {isCreating ? "Creating..." : "Create Tool Draft"}
                    </button>
                </div>
            </div>
        </div>
    );
}
