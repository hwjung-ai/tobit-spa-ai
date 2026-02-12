"use client";

import { useEffect, useState } from "react";
import { fetchApi } from "../../../lib/adminUtils";
import ToolTable from "../../../components/admin/ToolTable";
import CreateToolModal from "../../../components/admin/CreateToolModal";
import ToolTestPanel from "../../../components/admin/ToolTestPanel";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

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
type ToolType = "all" | "database_query" | "http_api" | "graph_query" | "python_script";

export default function ToolsPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [statusFilter, setStatusFilter] = useState<ToolStatus>("all");
    const [toolTypeFilter, setToolTypeFilter] = useState<ToolType>("all");
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [selectedTool, setSelectedTool] = useState<ToolAsset | null>(null);
    const [isInitialized, setIsInitialized] = useState(false);

    // Initialize filters from URL query parameters
    useEffect(() => {
        const statusParam = searchParams.get("status") as ToolStatus | null;
        const typeParam = searchParams.get("tool_type") as ToolType | null;

        if (statusParam && ["all", "draft", "published"].includes(statusParam)) {
            setStatusFilter(statusParam);
        }

        if (typeParam && ["all", "database_query", "http_api", "graph_query", "python_script"].includes(typeParam)) {
            setToolTypeFilter(typeParam);
        }

        setIsInitialized(true);
    }, [searchParams]);

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

    const { data: tools = [], isLoading, error, refetch } = useQuery({
        queryKey: ["tools", statusFilter, toolTypeFilter],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (statusFilter !== "all") params.append("status", statusFilter);
            if (toolTypeFilter !== "all") params.append("tool_type", toolTypeFilter);

            const queryString = params.toString();
            const endpoint = `/asset-registry/tools${queryString ? `?${queryString}` : ""}`;
            try {
                // Tool API returns ResponseEnvelope with data = { assets, total, page, page_size }
                const response = await fetchApi<{ assets: ToolAsset[]; total: number; page: number; page_size: number }>(endpoint);
                console.log("[Tools] API Response:", response);
                return response.data.assets || [];
            } catch (err) {
                console.error("Failed to fetch tools:", err);
                throw err;
            }
        }
    });

    const handleToolSelect = (tool: ToolAsset) => {
        setSelectedTool(tool);
    };

    const handleCloseTestPanel = () => {
        setSelectedTool(null);
    };

    return (
        <div className="space-y-6">
            {/* Control Bar */}
            <div className="flex justify-between items-center  rounded-2xl border  p-4 backdrop-blur-sm" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                <div className="flex gap-6">
                    <div className="min-w-[160px]">
                        <label className="block text-[10px] font-bold  uppercase tracking-widest mb-1.5 ml-1" style={{color: "var(--muted-foreground)"}}>Tool Type</label>
                        <select
                            value={toolTypeFilter}
                            onChange={(e) => handleToolTypeFilterChange(e.target.value as ToolType)}
                            className="w-full px-3 py-2  border  rounded-lg  text-xs focus:outline-none focus:border-sky-500/50 transition-all cursor-pointer" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-base)"}}
                        >
                            <option value="all">All Types</option>
                            <option value="database_query">Database Query</option>
                            <option value="http_api">HTTP API</option>
                            <option value="graph_query">Graph Query</option>
                            <option value="python_script">Python Script</option>
                        </select>
                    </div>

                    <div className="min-w-[160px]">
                        <label className="block text-[10px] font-bold  uppercase tracking-widest mb-1.5 ml-1" style={{color: "var(--muted-foreground)"}}>Status</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => handleStatusFilterChange(e.target.value as ToolStatus)}
                            className="w-full px-3 py-2  border  rounded-lg  text-xs focus:outline-none focus:border-sky-500/50 transition-all cursor-pointer" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-base)"}}
                        >
                            <option value="all">Any Status</option>
                            <option value="draft">Draft Only</option>
                            <option value="published">Published Only</option>
                        </select>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={() => refetch()}
                        className=" hover: transition-colors text-[10px] font-bold uppercase tracking-widest px-2" style={{color: "var(--foreground-secondary)"}}
                    >
                        Refresh
                    </button>
                    <div className="w-px h-6 " style={{backgroundColor: "var(--surface-elevated)"}} />
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="px-5 py-2.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl transition-all font-bold text-[10px] uppercase tracking-[0.2em] shadow-lg shadow-sky-900/20 active:scale-95"
                    >
                        + New Tool
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex gap-6">
                {/* Tool List */}
                <div className={`bg-[var(--surface-base)]/40 rounded-2xl border border-[var(--border)] overflow-hidden shadow-2xl transition-all ${selectedTool ? "flex-1" : "w-full"}`}>
                    {!isInitialized || isLoading ? (
                        <div className="flex flex-col items-center justify-center py-24 gap-4">
                            <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                            <p className=" text-xs font-bold uppercase tracking-widest" style={{color: "var(--muted-foreground)"}}>Loading Tools...</p>
                        </div>
                    ) : error ? (
                        <div className="text-center py-20">
                            <p className="text-red-400 mb-4 text-sm font-medium">{error instanceof Error ? error.message : "Failed to load tools"}</p>
                            <button
                                onClick={() => refetch()}
                                className="px-6 py-2  hover:  rounded-lg text-xs font-bold uppercase tracking-widest transition-all" style={{color: "var(--foreground-secondary)", backgroundColor: "var(--surface-elevated)"}}
                            >
                                Try Again
                            </button>
                        </div>
                    ) : tools.length === 0 ? (
                        <div className="text-center py-20">
                            <div className="w-12 h-12  rounded-full flex items-center justify-center mx-auto mb-4 border /50" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                                <svg className="w-6 h-6 " style={{color: "var(--muted-foreground)"}} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
                                </svg>
                            </div>
                            <p className=" text-sm font-medium italic" style={{color: "var(--muted-foreground)"}}>No tools found matching the selected criteria.</p>
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="mt-4 px-4 py-2 bg-sky-600/20 hover:bg-sky-600/30 text-sky-400 rounded-lg text-xs font-bold uppercase tracking-widest transition-all border border-sky-500/30"
                            >
                                Create First Tool
                            </button>
                        </div>
                    ) : (
                        <div className="animate-in fade-in duration-500">
                            <ToolTable
                                tools={tools}
                                statusFilter={statusFilter}
                                onStatusFilterChange={handleStatusFilterChange}
                                onToolSelect={handleToolSelect}
                                selectedToolId={selectedTool?.asset_id}
                                onRefresh={refetch}
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
                            onRefresh={refetch}
                        />
                    </div>
                )}
            </div>

            {showCreateModal && (
                <CreateToolModal
                    onClose={() => setShowCreateModal(false)}
                    onSuccess={(assetId) => {
                        refetch();
                        setShowCreateModal(false);
                    }}
                />
            )}
        </div>
    );
}
