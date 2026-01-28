"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";

interface CreateToolModalProps {
    onClose: () => void;
    onSuccess: (assetId: string) => void;
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
    const [isCreating, setIsCreating] = useState(false);
    const [errors, setErrors] = useState<string[]>([]);

    // Fetch available catalogs
    const { data: catalogsData } = useQuery({
        queryKey: ["admin-catalogs-for-tool"],
        queryFn: async () => {
            const response = await fetchApi("/asset-registry/catalogs?status=published");
            return response.data?.assets || [];
        },
    });

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
            <div className="bg-slate-900 rounded-2xl border border-slate-800 max-w-2xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-6 border-b border-slate-800">
                    <div>
                        <h2 className="text-xl font-bold text-white">Create New Tool</h2>
                        <p className="text-slate-500 text-xs mt-1">Define a new orchestration tool asset</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors"
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
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                                Tool Name
                            </label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g. equipment_search, inventory_list"
                                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all font-mono"
                                autoFocus
                            />
                            <p className="text-slate-600 text-xs mt-1 ml-1">Use snake_case for tool names</p>
                        </div>

                        {/* Tool Type */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
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
                                                : "bg-slate-950 border-slate-800 hover:border-slate-700"
                                        }`}
                                    >
                                        <span className={`block font-bold text-sm ${
                                            toolType === type.value ? "text-sky-400" : "text-slate-300"
                                        }`}>
                                            {type.label}
                                        </span>
                                        <span className="block text-slate-500 text-xs mt-0.5">
                                            {type.description}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Description */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
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
                                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all resize-none"
                            />
                        </div>

                        {/* Catalog Reference (Optional) */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                                Database Catalog (Optional)
                            </label>
                            <select
                                value={catalogRef}
                                onChange={(e) => setCatalogRef(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:border-sky-500 transition-all"
                            >
                                <option value="">-- No Catalog Selected --</option>
                                {catalogsData?.map((catalog: any) => (
                                    <option key={catalog.asset_id} value={catalog.name}>
                                        {catalog.name} (Tables: {catalog.content?.catalog?.tables?.length || 0})
                                    </option>
                                ))}
                            </select>
                            <p className="text-slate-600 text-xs mt-1 ml-1">
                                💡 Select a catalog to provide database schema information to LLM for accurate SQL generation
                            </p>
                        </div>

                        {/* Tool Config */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                                Tool Configuration (JSON)
                            </label>
                            <textarea
                                value={toolConfig}
                                onChange={(e) => setToolConfig(e.target.value)}
                                rows={5}
                                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none"
                            />
                        </div>

                        {/* Input Schema */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                                Input Schema (JSON Schema)
                            </label>
                            <textarea
                                value={inputSchema}
                                onChange={(e) => setInputSchema(e.target.value)}
                                rows={6}
                                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none"
                            />
                        </div>
                    </div>
                </div>

                <div className="p-6 border-t border-slate-800 flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 py-3 text-slate-400 hover:text-white transition-colors font-bold uppercase tracking-widest text-xs"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={isCreating}
                        className="flex-[2] py-3 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl transition-all font-bold shadow-lg shadow-sky-900/20 active:scale-95"
                    >
                        {isCreating ? "Creating..." : "Create Tool Draft"}
                    </button>
                </div>
            </div>
        </div>
    );
}
