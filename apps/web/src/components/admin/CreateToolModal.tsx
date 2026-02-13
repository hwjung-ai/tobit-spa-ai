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

interface McpDiscoveredTool {
    name: string;
    description: string;
    inputSchema: Record<string, unknown>;
}

const TOOL_TYPES = [
    { value: "database_query", label: "Database Query", description: "Execute SQL queries against data sources" },
    { value: "http_api", label: "HTTP API", description: "Call external REST APIs" },
    { value: "graph_query", label: "Graph Query", description: "Query graph databases (Neo4j, etc.)" },
    { value: "mcp", label: "MCP Server", description: "Call tools on MCP (Model Context Protocol) servers" },
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

    // MCP Discovery state
    const [mcpServerUrl, setMcpServerUrl] = useState("");
    const [mcpTransport, setMcpTransport] = useState<"sse" | "streamable_http">("sse");
    const [mcpDiscoveredTools, setMcpDiscoveredTools] = useState<McpDiscoveredTool[]>([]);
    const [mcpSelectedTools, setMcpSelectedTools] = useState<Set<string>>(new Set());
    const [mcpIsDiscovering, setMcpIsDiscovering] = useState(false);
    const [mcpIsImporting, setMcpIsImporting] = useState(false);
    const [mcpDiscoveryError, setMcpDiscoveryError] = useState<string | null>(null);
    const [mcpImportResult, setMcpImportResult] = useState<{ imported: number; errors: string[] } | null>(null);

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

    // MCP Discovery
    const handleMcpDiscover = async () => {
        if (!mcpServerUrl.trim()) {
            setMcpDiscoveryError("Server URL is required");
            return;
        }

        setMcpIsDiscovering(true);
        setMcpDiscoveryError(null);
        setMcpDiscoveredTools([]);
        setMcpSelectedTools(new Set());
        setMcpImportResult(null);

        try {
            const response = await fetchApi<{ tools: McpDiscoveredTool[]; total: number }>(
                "/asset-registry/tools/discover-mcp-tools",
                {
                    method: "POST",
                    body: JSON.stringify({
                        server_url: mcpServerUrl,
                        transport: mcpTransport,
                    }),
                }
            );

            const tools = (response.data as any)?.tools || [];
            setMcpDiscoveredTools(tools);

            if (tools.length === 0) {
                setMcpDiscoveryError("MCP server returned no tools");
            }
        } catch (err: unknown) {
            console.error("[MCP Discovery] Error:", err);
            const errorMsg = err instanceof Error ? err.message : "Failed to discover MCP tools";
            setMcpDiscoveryError(errorMsg);
        } finally {
            setMcpIsDiscovering(false);
        }
    };

    const handleMcpToggleTool = (toolName: string) => {
        setMcpSelectedTools((prev) => {
            const next = new Set(prev);
            if (next.has(toolName)) {
                next.delete(toolName);
            } else {
                next.add(toolName);
            }
            return next;
        });
    };

    const handleMcpSelectAll = () => {
        if (mcpSelectedTools.size === mcpDiscoveredTools.length) {
            setMcpSelectedTools(new Set());
        } else {
            setMcpSelectedTools(new Set(mcpDiscoveredTools.map((t) => t.name)));
        }
    };

    // MCP: select single tool to fill form (manual create mode)
    const handleMcpSelectSingle = (tool: McpDiscoveredTool) => {
        setName(`mcp_${tool.name}`);
        setDescription(tool.description || `MCP tool: ${tool.name}`);
        setToolConfig(JSON.stringify({
            server_url: mcpServerUrl,
            transport: mcpTransport,
            tool_name: tool.name,
            timeout_ms: 30000,
        }, null, 2));
        setInputSchema(JSON.stringify(tool.inputSchema || DEFAULT_INPUT_SCHEMA, null, 2));
    };

    // MCP: batch import selected tools
    const handleMcpImportSelected = async () => {
        if (mcpSelectedTools.size === 0) return;

        setMcpIsImporting(true);
        setMcpImportResult(null);
        setErrors([]);

        try {
            const toolsToImport = mcpDiscoveredTools
                .filter((t) => mcpSelectedTools.has(t.name))
                .map((t) => ({
                    name: t.name,
                    description: t.description,
                    inputSchema: t.inputSchema,
                }));

            const response = await fetchApi<{
                imported: { asset_id: string; name: string }[];
                errors: { name: string; error: string }[];
                total_imported: number;
                total_errors: number;
            }>("/asset-registry/tools/import-from-mcp", {
                method: "POST",
                body: JSON.stringify({
                    server_url: mcpServerUrl,
                    transport: mcpTransport,
                    tools: toolsToImport,
                }),
            });

            const data = response.data as any;
            const importErrors = (data?.errors || []).map((e: any) => `${e.name || "?"}: ${e.error}`);

            setMcpImportResult({
                imported: data?.total_imported || 0,
                errors: importErrors,
            });

            if (data?.total_imported > 0) {
                // Auto close after successful import
                setTimeout(() => {
                    onSuccess(data.imported?.[0]?.asset_id || "");
                }, 1500);
            }
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to import MCP tools"]);
        } finally {
            setMcpIsImporting(false);
        }
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

    // Check if MCP mode is in "batch import" state (tools discovered, some selected)
    const isMcpBatchMode = toolType === "mcp" && mcpDiscoveredTools.length > 0;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
            <div className="container-panel max-w-2xl w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh] bg-surface-base dark:bg-surface-base text-foreground dark:text-slate-50">
                <div className="flex items-center justify-between p-6 border-b border-variant">
                    <div>
                        <h2 className="text-xl font-bold text-foreground">Create New Tool</h2>
                        <p className="text-xs mt-1 text-muted-foreground">Define a new orchestration tool asset</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="hover:text-foreground transition-colors text-muted-foreground dark:text-muted-foreground"
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
                        {/* Tool Type (always shown) */}
                        <div>
                            <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                Tool Type
                            </label>
                            <div className="grid grid-cols-2 gap-3">
                                {TOOL_TYPES.map((type) => (
                                    <button
                                        key={type.value}
                                        onClick={() => {
                                            setToolType(type.value);
                                            if (type.value === "mcp") {
                                                setToolConfig(JSON.stringify({ server_url: "", transport: "sse", tool_name: "", timeout_ms: 30000 }, null, 2));
                                                // Reset MCP discovery state
                                                setMcpDiscoveredTools([]);
                                                setMcpSelectedTools(new Set());
                                                setMcpDiscoveryError(null);
                                                setMcpImportResult(null);
                                            } else {
                                                setToolConfig(JSON.stringify(DEFAULT_TOOL_CONFIG, null, 2));
                                            }
                                        }}
                                        className={`px-4 py-3 rounded-xl border text-left transition-all ${
                                            toolType === type.value
                                                ? "bg-sky-600/20 border-sky-500 shadow-lg shadow-sky-900/10"
                                                : "hover:"
                                        } bg-surface-base border-variant`}
                                    >
                                        <span className={`block font-bold text-sm ${
                                            toolType === type.value ? "text-sky-400" : ""
                                        } text-foreground`}>
                                            {type.label}
                                        </span>
                                        <span className="block text-xs mt-0.5 text-muted-foreground">
                                            {type.description}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* API Manager Selection (HTTP API Tools) */}
                        {toolType === "http_api" && (
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                    API Manager API (Optional)
                                </label>
                                <select
                                    value={selectedApiId}
                                    onChange={(e) => handleApiSelection(e.target.value)}
                                    className="w-full px-4 py-3 border rounded-xl focus:outline-none focus:border-sky-500 transition-all border-variant text-foreground bg-surface-base dark:bg-surface-base/50 dark:text-white dark:focus:border-sky-400"
                                >
                                    <option value="">-- Select API Manager API --</option>
                                    {apiManagerApis.map((api) => (
                                        <option key={api.id} value={api.id}>
                                            {api.name} ({api.method} {api.path})
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs mt-1 ml-1 text-muted-foreground">
                                    선택 시 Tool Config/Input Schema가 API 실행용으로 자동 채워집니다.
                                </p>
                            </div>
                        )}

                        {/* ============ MCP Server Discovery Section ============ */}
                        {toolType === "mcp" && (
                            <div className="space-y-4 p-4 rounded-xl border border-variant bg-surface-elevated">
                                <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                                    MCP Server Discovery
                                </p>

                                {/* Server URL + Transport */}
                                <div className="flex gap-3">
                                    <div className="flex-1">
                                        <label className="block text-xs font-medium mb-1 ml-1 text-muted-foreground">Server URL</label>
                                        <input
                                            type="text"
                                            value={mcpServerUrl}
                                            onChange={(e) => setMcpServerUrl(e.target.value)}
                                            placeholder="e.g. http://localhost:3100/sse"
                                            className="w-full px-3 py-3 border rounded-lg font-mono text-xs focus:outline-none focus:border-sky-500 transition-all border-variant text-foreground bg-surface-base dark:bg-surface-base/50 dark:text-white dark:focus:border-sky-400"
                                        />
                                    </div>
                                    <div className="w-[180px]">
                                        <label className="block text-xs font-medium mb-1 ml-1 text-muted-foreground">Transport</label>
                                        <select
                                            value={mcpTransport}
                                            onChange={(e) => setMcpTransport(e.target.value as "sse" | "streamable_http")}
                                            className="w-full px-3 py-3 border rounded-lg text-xs focus:outline-none focus:border-sky-500 transition-all border-variant text-foreground bg-surface-base"
                                        >
                                            <option value="sse">SSE</option>
                                            <option value="streamable_http">Streamable HTTP</option>
                                        </select>
                                    </div>
                                </div>

                                {/* Discover Button */}
                                <button
                                    onClick={handleMcpDiscover}
                                    disabled={mcpIsDiscovering || !mcpServerUrl.trim()}
                                    className="w-full py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg transition-all font-bold text-xs uppercase tracking-wider dark:bg-sky-700 dark:hover:bg-sky-600"
                                >
                                    {mcpIsDiscovering ? "Discovering..." : "Discover Tools"}
                                </button>

                                {/* Discovery Error */}
                                {mcpDiscoveryError && (
                                    <div className="px-3 py-2 rounded-lg text-xs border border-rose-500/30 bg-rose-500/10 text-rose-400">
                                        {mcpDiscoveryError}
                                    </div>
                                )}

                                {/* Discovered Tools List */}
                                {mcpDiscoveredTools.length > 0 && (
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <p className="text-xs font-bold text-foreground">
                                                {mcpDiscoveredTools.length} tool{mcpDiscoveredTools.length !== 1 ? "s" : ""} found
                                            </p>
                                            <button
                                                onClick={handleMcpSelectAll}
                                                className="text-xs font-medium text-cyan-400 hover:text-cyan-300 transition-colors"
                                            >
                                                {mcpSelectedTools.size === mcpDiscoveredTools.length ? "Deselect All" : "Select All"}
                                            </button>
                                        </div>

                                        <div className="max-h-[240px] overflow-y-auto space-y-2 pr-1">
                                            {mcpDiscoveredTools.map((tool) => {
                                                const isSelected = mcpSelectedTools.has(tool.name);
                                                return (
                                                    <div
                                                        key={tool.name}
                                                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                                                            isSelected
                                                                ? "border-cyan-500/50 bg-cyan-500/10"
                                                                : "hover:border-cyan-500/20"
                                                        } ${isSelected ? "" : "border-variant bg-surface-base"}`}
                                                        onClick={() => handleMcpToggleTool(tool.name)}
                                                    >
                                                        {/* Checkbox */}
                                                        <div className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                                                            isSelected ? "bg-cyan-500 border-cyan-500" : "border-slate-500"
                                                        }`}>
                                                            {isSelected && (
                                                                <svg className="w-3 h-3 text-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                                                </svg>
                                                            )}
                                                        </div>

                                                        {/* Tool Info */}
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center gap-2">
                                                                <span className="font-mono text-xs font-bold text-cyan-400">{tool.name}</span>
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleMcpSelectSingle(tool);
                                                                    }}
                                                                    className="text-xs px-3 py-0.5 rounded border border-variant hover:border-cyan-500 hover:text-cyan-400 transition-colors text-muted-foreground"
                                                                    title="Fill form with this tool's data"
                                                                >
                                                                    Fill Form
                                                                </button>
                                                            </div>
                                                            {tool.description && (
                                                                <p className="text-xs mt-0.5 line-clamp-2 text-muted-foreground">
                                                                    {tool.description}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        {/* Batch Import Button */}
                                        {mcpSelectedTools.size > 0 && (
                                            <button
                                                onClick={handleMcpImportSelected}
                                                disabled={mcpIsImporting}
                                                className="w-full py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg transition-all font-bold text-xs uppercase tracking-wider dark:bg-sky-700 dark:hover:bg-sky-600"
                                            >
                                                {mcpIsImporting
                                                    ? "Importing..."
                                                    : `Import ${mcpSelectedTools.size} Tool${mcpSelectedTools.size !== 1 ? "s" : ""} as Draft`}
                                            </button>
                                        )}

                                        {/* Import Result */}
                                        {mcpImportResult && (
                                            <div className={`px-3 py-2 rounded-lg text-xs border ${
                                                mcpImportResult.imported > 0
                                                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                                                    : "border-rose-500/30 bg-rose-500/10 text-rose-400"
                                            }`}>
                                                {mcpImportResult.imported > 0 && (
                                                    <p>{mcpImportResult.imported} tool{mcpImportResult.imported !== 1 ? "s" : ""} imported as draft</p>
                                                )}
                                                {mcpImportResult.errors.map((e, i) => (
                                                    <p key={i}>{e}</p>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                <p className="text-xs">
                                    MCP 서버에 접속하여 제공하는 tool 목록을 자동으로 가져옵니다. 선택한 tool을 일괄 import하거나, "Fill Form" 버튼으로 개별 등록할 수 있습니다.
                                </p>
                            </div>
                        )}

                        {/* ============ Non-MCP or Manual MCP Fields ============ */}
                        {/* Tool Name (hidden during MCP batch import) */}
                        {!isMcpBatchMode && (
                            <>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Tool Name
                                    </label>
                                    <input
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        placeholder="e.g. equipment_search, inventory_list"
                                        className="w-full px-4 py-3 border rounded-xl placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all font-mono border-variant text-foreground bg-surface-base"
                                        autoFocus={toolType !== "mcp"}
                                    />
                                    <p className="text-xs mt-1 ml-1 text-muted-foreground">Use snake_case for tool names</p>
                                </div>

                                {/* Description */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
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
                                        className="w-full px-4 py-3 border rounded-xl placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all resize-none border-variant text-foreground bg-surface-base dark:bg-surface-base/50 dark:text-white dark:focus:border-sky-400"
                                    />
                                </div>

                                {/* Catalog Reference (Optional) */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Database Catalog (Optional)
                                    </label>
                                    <select
                                        value={catalogRef}
                                        onChange={(e) => setCatalogRef(e.target.value)}
                                        className="w-full px-4 py-3 border rounded-xl focus:outline-none focus:border-sky-500 transition-all border-variant text-foreground bg-surface-base dark:bg-surface-base/50 dark:text-white dark:focus:border-sky-400"
                                    >
                                        <option value="">-- No Catalog Selected --</option>
                                        {catalogsData?.map((catalog: any) => (
                                            <option key={catalog.asset_id} value={catalog.name}>
                                                {catalog.name} (Tables: {catalog.content?.catalog?.tables?.length || 0})
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs mt-1 ml-1 text-muted-foreground">
                                        Select a catalog to provide database schema information to LLM for accurate SQL generation
                                    </p>
                                </div>

                                {/* Tool Config */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Tool Configuration (JSON)
                                    </label>
                                    <textarea
                                        value={toolConfig}
                                        onChange={(e) => setToolConfig(e.target.value)}
                                        rows={5}
                                        className="w-full px-4 py-3 border rounded-xl font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none border-variant text-foreground bg-surface-base"
                                    />
                                </div>

                                {/* Input Schema */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Input Schema (JSON Schema)
                                    </label>
                                    <textarea
                                        value={inputSchema}
                                        onChange={(e) => setInputSchema(e.target.value)}
                                        rows={6}
                                        className="w-full px-4 py-3 border rounded-xl font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none border-variant text-foreground bg-surface-base"
                                    />
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Footer: show Create button only for non-batch mode */}
                {!isMcpBatchMode && (
                    <div className="p-6 border-t flex gap-3 border-variant">
                        <button
                            onClick={onClose}
                            className="flex-1 py-3 border border-variant text-foreground hover:bg-slate-100 dark:border-variant dark:text-muted-foreground dark:hover:bg-surface-elevated transition-colors font-bold uppercase tracking-widest text-xs"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleCreate}
                            disabled={isCreating}
                            className="flex-[2] py-3 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg transition-all font-bold shadow-lg shadow-sky-900/20 active:scale-95 dark:bg-sky-700 dark:hover:bg-sky-600"
                        >
                            {isCreating ? "Creating..." : "Create Tool Draft"}
                        </button>
                    </div>
                )}

                {/* Footer: MCP batch mode - just close */}
                {isMcpBatchMode && (
                    <div className="p-6 border-t flex gap-3 border-variant">
                        <button
                            onClick={onClose}
                            className="flex-1 py-3 border border-variant text-foreground hover:bg-slate-100 dark:border-variant dark:text-muted-foreground dark:hover:bg-surface-elevated transition-colors font-bold uppercase tracking-widest text-xs"
                        >
                            Close
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
