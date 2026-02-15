"use client";

import { useEffect, useState, useMemo } from "react";
import { fetchApi } from "../../../lib/adminUtils";
import ToolTable from "../../../components/admin/ToolTable";
import CreateToolModal from "../../../components/admin/CreateToolModal";
import ToolTestPanel from "../../../components/admin/ToolTestPanel";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import StatusFilterButtons from "../../../components/admin/StatusFilterButtons";

// Tool Asset interface
export interface ToolAsset {
    asset_id: string;
    asset_type: string;
    name: string;
    description: string | null;
    version: number;
    status: string;
    tool_type: string;
    tool_catalog_ref?: string | null;
    tool_config: Record<string, unknown>;
    tool_input_schema: Record<string, unknown>;
    tool_output_schema: Record<string, unknown> | null;
    tags: Record<string, unknown> | null;
    created_by: string | null;
    published_by: string | null;
    published_at: string | null;
    created_at: string;
    updated_at: string;
}

type ToolStatus = "all" | "draft" | "published";
type ToolType = "all" | "database_query" | "http_api" | "graph_query" | "mcp" | "python_script";

export default function ToolsPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [selectedTool, setSelectedTool] = useState<ToolAsset | null>(null);
    const [isInitialized, setIsInitialized] = useState(false);
    const [refreshNonce, setRefreshNonce] = useState(0);

    // Initialize filters from URL query parameters
    const statusParam = searchParams.get("status") as ToolStatus | null;
    const typeParam = searchParams.get("tool_type") as ToolType | null;

    const initialStatusFilter = useMemo(() => {
        if (statusParam && ["all", "draft", "published"].includes(statusParam)) {
            return statusParam;
        }
        return "all";
    }, [statusParam]);

    const initialTypeFilter = useMemo(() => {
        if (typeParam && ["all", "database_query", "http_api", "graph_query", "mcp", "python_script"].includes(typeParam)) {
            return typeParam;
        }
        return "all";
    }, [typeParam]);

    const [statusFilter, setStatusFilter] = useState<ToolStatus>(initialStatusFilter);
    const [toolTypeFilter, setToolTypeFilter] = useState<ToolType>(initialTypeFilter);

    useEffect(() => {
        setIsInitialized(true);
    }, []);

    // Update URL when filters change
    const handleStatusFilterChange = (value: ToolStatus) => {
        setStatusFilter(value);
        const params = new URLSearchParams();
        if (value !== "all") params.append("status", value);
        if (toolTypeFilter !== "all") params.append("tool_type", toolTypeFilter);
        router.push(`/admin/tools?${params.toString()}`);
    };

    const handleToolTypeFilterChange = (value: ToolType) => {
        setToolTypeFilter(value);
        const params = new URLSearchParams();
        if (statusFilter !== "all") params.append("status", statusFilter);
        if (value !== "all") params.append("tool_type", value);
        router.push(`/admin/tools?${params.toString()}`);
    };

    const { data: tools = [], isLoading, isFetching, error } = useQuery({
        queryKey: ["tools", statusFilter, toolTypeFilter, refreshNonce],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (statusFilter !== "all") params.append("status", statusFilter);
            if (toolTypeFilter !== "all") params.append("tool_type", toolTypeFilter);

            const queryString = params.toString();
            const endpoint = `/asset-registry/tools${queryString ? `?${queryString}` : ""}`;
            try {
                // Tool API returns ResponseEnvelope with data = { assets, total, page, page_size }
                const response = await fetchApi<{ assets: ToolAsset[]; total: number; page: number; page_size: number }>(endpoint, { cache: "no-store" });
                return response.data.assets || [];
            } catch (err) {
                if (process.env.NODE_ENV === 'development') {
                  console.error("Failed to fetch tools:", err);
                }
                throw err;
            }
        }
    });

    const handleRefresh = () => {
        queryClient.removeQueries({ queryKey: ["tools"] });
        setRefreshNonce((prev) => prev + 1);
    };

    const handleToolSelect = (tool: ToolAsset) => {
        setSelectedTool(tool);
    };

    const handleCloseTestPanel = () => {
        setSelectedTool(null);
    };

    return (
        <div className="space-y-6">
            {/* Control Bar */}
            <div className="flex justify-between items-center rounded-2xl border p-4 backdrop-blur-sm border-border bg-surface-elevated">
                <div className="flex gap-6">
                    <div className="min-w-[260px] flex items-center gap-3">
                        <label className="text-xs font-semibold tracking-wide text-muted-foreground whitespace-nowrap">Tool Type</label>
                        <select
                            value={toolTypeFilter}
                            onChange={(e) => handleToolTypeFilterChange(e.target.value as ToolType)}
                            className="input-container w-full text-xs"
                        >
                            <option value="all">All Types</option>
                            <option value="database_query">Database Query</option>
                            <option value="http_api">HTTP API</option>
                            <option value="graph_query">Graph Query</option>
                            <option value="mcp">MCP Server</option>
                            <option value="python_script">Python Script</option>
                        </select>
                    </div>
                    <StatusFilterButtons value={statusFilter} onChange={handleStatusFilterChange} />

                </div>

                <div className="flex items-center gap-4">
                    <button
                        type="button"
                        onClick={() => {
                            void handleRefresh();
                        }}
                        disabled={isFetching}
                        className="rounded-md border border-variant bg-surface-base px-3 py-2 text-label-sm transition hover:border-sky-500 hover:text-primary"
                    >
                        {isFetching ? "Refreshing..." : "Refresh"}
                    </button>
                    <div className="w-px h-6 bg-border" />
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="btn-primary"
                    >
                        + New Tool
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex gap-6">
                {/* Tool List */}
                <div
                    className={`rounded-2xl border border-variant bg-surface-elevated overflow-hidden shadow-2xl transition-all ${selectedTool ? "flex-1" : "w-full"}`}
                >
                    {error ? (
                        <div className="text-center py-20">
                            <p className="text-rose-400 mb-4 text-sm font-medium">{error instanceof Error ? error.message : "Failed to load tools"}</p>
                            <button
                                onClick={() => {
                                    void handleRefresh();
                                }}
                                className="px-6 py-2 hover:bg-surface-elevated dark:hover:bg-surface-elevated rounded-lg text-xs font-bold uppercase tracking-widest transition-all bg-surface-elevated text-foreground dark:bg-surface-elevated dark:text-muted-foreground"
                            >
                                Try Again
                            </button>
                        </div>
                    ) : (
                        <div>
                            <ToolTable
                                tools={tools}
                                loading={!isInitialized || isLoading}
                                onToolSelect={handleToolSelect}
                                selectedToolId={selectedTool?.asset_id}
                                onRefresh={handleRefresh}
                            />
                        </div>
                    )}
                </div>

                {/* Tool Test Panel */}
                {selectedTool && (
                    <div className="w-[480px] flex-shrink-0 animate-in slide-in-from-right duration-300">
                        <ToolTestPanel
                            tool={selectedTool}
                            onClose={handleCloseTestPanel}
                            onRefresh={handleRefresh}
                        />
                    </div>
                )}
            </div>

            {showCreateModal && (
                <CreateToolModal
                    onClose={() => setShowCreateModal(false)}
                    onSuccess={() => {
                        void handleRefresh();
                        setShowCreateModal(false);
                    }}
                />
            )}
        </div>
    );
}
