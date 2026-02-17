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

interface SourceAssetItem {
    asset_id: string;
    name: string;
    source_type?: string;
}

interface CatalogAssetItem {
    asset_id: string;
    name: string;
    catalog?: {
        source_ref?: string;
        tables?: unknown[];
    };
}

interface AssetListResponse<T> {
    assets?: T[];
}

interface McpDiscoverResponse {
    tools?: McpDiscoveredTool[];
    total?: number;
}

interface McpImportResponse {
    imported?: { asset_id: string; name: string }[];
    errors?: { name?: string; error?: string }[];
    total_imported?: number;
    total_errors?: number;
}

const TOOL_TYPES = [
    { value: "database_query", label: "Database Query", description: "Execute SQL queries against data sources" },
    { value: "http_api", label: "HTTP API", description: "Call external REST APIs" },
    { value: "graph_query", label: "Graph Query", description: "Query graph databases (Neo4j, etc.)" },
    { value: "mcp", label: "MCP Server", description: "Call tools on MCP (Model Context Protocol) servers" },
    { value: "python_script", label: "Python Script", description: "Execute custom Python scripts" },
] as const;

// Available capabilities for tool selection
const AVAILABLE_CAPABILITIES = [
    { value: "ci_lookup", label: "CI Lookup", description: "Retrieve single CI details" },
    { value: "ci_search", label: "CI Search", description: "Search multiple CIs" },
    { value: "ci_list", label: "CI List", description: "List CIs with pagination" },
    { value: "ci_aggregate", label: "CI Aggregate", description: "Aggregate CI data" },
    { value: "document_search", label: "Document Search", description: "Search documents" },
    { value: "metric_query", label: "Metric Query", description: "Query metric data" },
    { value: "metric_aggregate", label: "Metric Aggregate", description: "Aggregate metrics" },
    { value: "history_search", label: "History Search", description: "Search event history" },
    { value: "event_search", label: "Event Search", description: "Search events" },
    { value: "graph_expand", label: "Graph Expand", description: "Expand CI relationships" },
    { value: "graph_path", label: "Graph Path", description: "Find paths between CIs" },
    { value: "graph_topology", label: "Graph Topology", description: "Get network topology" },
] as const;

// Available modes for tool support
const AVAILABLE_MODES = [
    { value: "config", label: "Config", description: "Configuration mode" },
    { value: "metric", label: "Metric", description: "Metric mode" },
    { value: "graph", label: "Graph", description: "Graph/Topology mode" },
    { value: "history", label: "History", description: "History mode" },
    { value: "document", label: "Document", description: "Document search mode" },
    { value: "all", label: "All", description: "Supports all modes" },
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
    const [sourceRef, setSourceRef] = useState<string>("");
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

    // Capabilities and modes state
    const [selectedCapabilities, setSelectedCapabilities] = useState<Set<string>>(new Set());
    const [selectedModes, setSelectedModes] = useState<Set<string>>(new Set(["all"]));

    const apiBaseUrl = useMemo(() => {
        const raw = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        return raw.replace(/\/+$/, "");
    }, []);

    // Fetch available catalogs
    const { data: catalogsData = [] } = useQuery<CatalogAssetItem[]>({
        queryKey: ["admin-catalogs-for-tool"],
        queryFn: async () => {
            const response = await fetchApi<AssetListResponse<CatalogAssetItem>>("/asset-registry/catalogs?status=published");
            const data = response.data as AssetListResponse<CatalogAssetItem> | undefined;
            return data?.assets ?? [];
        },
    });

    const { data: sourcesData = [] } = useQuery<SourceAssetItem[]>({
        queryKey: ["admin-sources-for-tool"],
        queryFn: async () => {
            const response = await fetchApi<AssetListResponse<SourceAssetItem>>("/asset-registry/sources?status=published");
            const data = response.data as AssetListResponse<SourceAssetItem> | undefined;
            return data?.assets ?? [];
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

    const handleSourceSelection = (nextSourceRef: string) => {
        setSourceRef(nextSourceRef);
        try {
            const parsed = JSON.parse(toolConfig) as Record<string, unknown>;
            const nextConfig: Record<string, unknown> = { ...parsed };
            if (nextSourceRef.trim()) {
                nextConfig.source_ref = nextSourceRef.trim();
            } else {
                delete nextConfig.source_ref;
            }
            setToolConfig(JSON.stringify(nextConfig, null, 2));
        } catch {
            // Keep raw JSON as-is. Validation on create will report invalid config JSON.
        }
    };

    const selectedCatalog = useMemo(
        () => catalogsData.find((catalog) => catalog.name === catalogRef),
        [catalogsData, catalogRef]
    );

    const filteredCatalogs = useMemo(() => {
        if (!sourceRef.trim()) {
            return catalogsData;
        }
        return catalogsData.filter(
            (catalog) => (catalog.catalog?.source_ref || "").trim() === sourceRef.trim()
        );
    }, [catalogsData, sourceRef]);

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
            const response = await fetchApi<McpDiscoverResponse>(
                "/asset-registry/tools/discover-mcp-tools",
                {
                    method: "POST",
                    body: JSON.stringify({
                        server_url: mcpServerUrl,
                        transport: mcpTransport,
                    }),
                }
            );

            const data = response.data as McpDiscoverResponse | undefined;
            const tools = data?.tools || [];
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

            const response = await fetchApi<McpImportResponse>("/asset-registry/tools/import-from-mcp", {
                method: "POST",
                body: JSON.stringify({
                    server_url: mcpServerUrl,
                    transport: mcpTransport,
                    tools: toolsToImport,
                }),
            });

            const data = response.data as McpImportResponse | undefined;
            const importErrors = (data?.errors || []).map((e) => `${e.name || "?"}: ${e.error}`);
            const totalImported = data?.total_imported || 0;

            setMcpImportResult({
                imported: totalImported,
                errors: importErrors,
            });

            if (totalImported > 0) {
                // Auto close after successful import
                setTimeout(() => {
                    onSuccess(data?.imported?.[0]?.asset_id || "");
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

        const effectiveConfig: Record<string, unknown> = {
            ...parsedConfig,
        };

        if (toolType === "database_query" || toolType === "graph_query") {
            const sourceFromConfig = typeof effectiveConfig.source_ref === "string" ? effectiveConfig.source_ref : "";
            const effectiveSourceRef = sourceRef.trim() || sourceFromConfig.trim();
            if (!effectiveSourceRef) {
                validationErrors.push("Source is required for database_query / graph_query tools");
            } else {
                effectiveConfig.source_ref = effectiveSourceRef;
            }

            if (catalogRef && selectedCatalog?.catalog?.source_ref && effectiveSourceRef) {
                if (selectedCatalog.catalog.source_ref !== effectiveSourceRef) {
                    validationErrors.push(
                        `Selected catalog source_ref (${selectedCatalog.catalog.source_ref}) does not match tool source_ref (${effectiveSourceRef})`
                    );
                }
            }
        }

        if (validationErrors.length > 0) {
            setErrors(validationErrors);
            return;
        }

        setIsCreating(true);
        setErrors([]);

        try {
            const payload: Record<string, unknown> = {
                name,
                description,
                tool_type: toolType,
                tool_config: effectiveConfig,
                tool_input_schema: parsedInputSchema,
                tool_output_schema: null,
                created_by: "admin",
            };

            // Add catalog reference if selected
            if (catalogRef.trim()) {
                payload.tool_catalog_ref = catalogRef;
            }

            // Add capabilities and supported_modes to tags
            payload.tags = {
                capabilities: Array.from(selectedCapabilities),
                supported_modes: Array.from(selectedModes),
            };

            const response = await fetchApi<{ asset: { asset_id: string } }>("/asset-registry/tools", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            // API returns { data: { asset: { asset_id, ... } } }
            const responseData = response.data as { asset?: { asset_id?: string } } | undefined;
            const assetId = responseData?.asset?.asset_id;
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
                                    {apiManagerApis.map((api: ApiManagerItem) => (
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
                                    MCP 서버에 접속하여 제공하는 tool 목록을 자동으로 가져옵니다. 선택한 tool을 일괄 import하거나, &quot;Fill Form&quot; 버튼으로 개별 등록할 수 있습니다.
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

                                {/* Source Reference (Required for DB/Graph) */}
                                {(toolType === "database_query" || toolType === "graph_query") && (
                                    <div>
                                        <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                            Data Source
                                        </label>
                                        <select
                                            value={sourceRef}
                                            onChange={(e) => handleSourceSelection(e.target.value)}
                                            className="w-full px-4 py-3 border rounded-xl focus:outline-none focus:border-sky-500 transition-all border-variant text-foreground bg-surface-base dark:bg-surface-base/50 dark:text-white dark:focus:border-sky-400"
                                        >
                                            <option value="">-- Select Published Source --</option>
                                            {sourcesData.map((source) => (
                                                <option key={source.asset_id} value={source.name}>
                                                    {source.name}
                                                    {source.source_type ? ` (${source.source_type})` : ""}
                                                </option>
                                            ))}
                                        </select>
                                        <p className="text-xs mt-1 ml-1 text-muted-foreground">
                                            source_ref is managed from this selector and synced into Tool Configuration JSON.
                                        </p>
                                    </div>
                                )}

                                {/* Catalog Reference (Optional) */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Database Catalog (Optional)
                                    </label>
                                    <select
                                        value={catalogRef}
                                        onChange={(e) => {
                                            const nextCatalogRef = e.target.value;
                                            setCatalogRef(nextCatalogRef);
                                            if (!nextCatalogRef) {
                                                return;
                                            }
                                            const matched = catalogsData.find((catalog) => catalog.name === nextCatalogRef);
                                            const catalogSourceRef = matched?.catalog?.source_ref?.trim();
                                            if (catalogSourceRef && !sourceRef.trim()) {
                                                handleSourceSelection(catalogSourceRef);
                                            }
                                        }}
                                        className="w-full px-4 py-3 border rounded-xl focus:outline-none focus:border-sky-500 transition-all border-variant text-foreground bg-surface-base dark:bg-surface-base/50 dark:text-white dark:focus:border-sky-400"
                                    >
                                        <option value="">-- No Catalog Selected --</option>
                                        {filteredCatalogs.map((catalog) => {
                                            const tableCount = catalog.catalog?.tables;
                                            return (
                                                <option key={catalog.asset_id} value={catalog.name}>
                                                    {catalog.name} (Tables: {tableCount?.length || 0})
                                                </option>
                                            );
                                        })}
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

                                {/* Capabilities Selection */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Capabilities
                                        <span className="font-normal text-sky-500 ml-2">(What operations this tool can perform)</span>
                                    </label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {AVAILABLE_CAPABILITIES.map((cap) => (
                                            <button
                                                key={cap.value}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedCapabilities((prev) => {
                                                        const next = new Set(prev);
                                                        if (next.has(cap.value)) {
                                                            next.delete(cap.value);
                                                        } else {
                                                            next.add(cap.value);
                                                        }
                                                        return next;
                                                    });
                                                }}
                                                className={`px-3 py-2 rounded-lg border text-left transition-all text-xs ${
                                                    selectedCapabilities.has(cap.value)
                                                        ? "bg-sky-600/20 border-sky-500 text-sky-400"
                                                        : "bg-surface-base border-variant hover:border-sky-400"
                                                }`}
                                                title={cap.description}
                                            >
                                                {cap.label}
                                            </button>
                                        ))}
                                    </div>
                                    {selectedCapabilities.size === 0 && (
                                        <p className="text-xs text-amber-500 mt-2">
                                            ⚠️ No capabilities selected. System will auto-detect based on tool_type.
                                        </p>
                                    )}
                                </div>

                                {/* Supported Modes Selection */}
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-widest mb-2 ml-1 text-muted-foreground">
                                        Supported Modes
                                        <span className="font-normal text-sky-500 ml-2">(Which query modes this tool supports)</span>
                                    </label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {AVAILABLE_MODES.map((mode) => (
                                            <button
                                                key={mode.value}
                                                type="button"
                                                onClick={() => {
                                                    setSelectedModes((prev) => {
                                                        const next = new Set(prev);
                                                        if (next.has(mode.value)) {
                                                            // Don't allow deselecting all modes
                                                            if (next.size > 1) {
                                                                next.delete(mode.value);
                                                            }
                                                        } else {
                                                            next.add(mode.value);
                                                        }
                                                        return next;
                                                    });
                                                }}
                                                className={`px-3 py-2 rounded-lg border text-left transition-all text-xs ${
                                                    selectedModes.has(mode.value)
                                                        ? "bg-emerald-600/20 border-emerald-500 text-emerald-400"
                                                        : "bg-surface-base border-variant hover:border-emerald-400"
                                                }`}
                                                title={mode.description}
                                            >
                                                {mode.label}
                                            </button>
                                        ))}
                                    </div>
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
