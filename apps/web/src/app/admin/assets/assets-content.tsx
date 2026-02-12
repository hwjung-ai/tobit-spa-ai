"use client";

import { useEffect, useState } from "react";
import { Asset, fetchApi } from "../../../lib/adminUtils";
import AssetTable from "../../../components/admin/AssetTable";
import CreateAssetModal from "../../../components/admin/CreateAssetModal";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

// Define types for select options
type AssetType = "all" | "prompt" | "mapping" | "policy" | "query" | "source" | "resolver";
type AssetStatus = "all" | "draft" | "published";

export default function AssetsPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [typeFilter, setTypeFilter] = useState<AssetType>("all");
    const [statusFilter, setStatusFilter] = useState<AssetStatus>("all");
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [isInitialized, setIsInitialized] = useState(false);

    // Initialize filters from URL query parameters
    useEffect(() => {
        const typeParam = searchParams.get("type") as AssetType | null;
        const statusParam = searchParams.get("status") as AssetStatus | null;

        if (typeParam && ["all", "prompt", "mapping", "policy", "query", "source", "resolver"].includes(typeParam)) {
            setTypeFilter(typeParam);
        }

        if (statusParam && ["all", "draft", "published"].includes(statusParam)) {
            setStatusFilter(statusParam);
        }

        setIsInitialized(true);
    }, [searchParams]);

    // Update URL when filters change
    const handleTypeFilterChange = (value: AssetType) => {
        setTypeFilter(value);
        const params = new URLSearchParams();
        if (value !== "all") params.append("type", value);
        if (statusFilter !== "all") params.append("status", statusFilter);
        router.push(`/admin/assets?${params.toString()}`);
    };

    const handleStatusFilterChange = (value: AssetStatus) => {
        setStatusFilter(value);
        const params = new URLSearchParams();
        if (typeFilter !== "all") params.append("type", typeFilter);
        if (value !== "all") params.append("status", value);
        router.push(`/admin/assets?${params.toString()}`);
    };

    const { data: assets = [], isLoading, error, refetch } = useQuery({
        queryKey: ["assets", typeFilter, statusFilter],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (typeFilter !== "all") params.append("asset_type", typeFilter);
            if (statusFilter !== "all") params.append("status", statusFilter);

            const queryString = params.toString();
            const endpoint = `/asset-registry/assets${queryString ? `?${queryString}` : ""}`;
            const response = await fetchApi<{ assets: Asset[] }>(endpoint);
            return response.data.assets;
        }
    });

    return (
        <div className="space-y-6">
            {/* Control Bar */}
            <div className="flex justify-between items-center  rounded-2xl border  p-4 backdrop-blur-sm" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                <div className="flex gap-6">
                    <div className="min-w-[160px]">
                        <label className="block text-[10px] font-bold  uppercase tracking-widest mb-1.5 ml-1" style={{color: "var(--muted-foreground)"}}>Asset Type</label>
                        <select
                            value={typeFilter}
                            onChange={(e) => {
                                const value = e.target.value;
                                if (value === "all" || value === "prompt" || value === "mapping" ||
                                    value === "policy" || value === "query" ||
                                    value === "source" || value === "resolver") {
                                    handleTypeFilterChange(value as AssetType);
                                }
                            }}
                            className="w-full px-3 py-2  border  rounded-lg  text-xs focus:outline-none focus:border-sky-500/50 transition-all cursor-pointer" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-base)"}}
                        >
                            <option value="all">All Categories</option>
                            <option value="prompt">Prompts</option>
                            <option value="mapping">Mappings</option>
                            <option value="policy">Policies</option>
                            <option value="query">Queries</option>
                            <option value="source">Sources</option>
                            <option value="resolver">Resolvers</option>
                        </select>
                    </div>

                    <div className="min-w-[160px]">
                        <label className="block text-[10px] font-bold  uppercase tracking-widest mb-1.5 ml-1" style={{color: "var(--muted-foreground)"}}>Lifecycle</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => {
                                const value = e.target.value;
                                if (value === "all" || value === "draft" || value === "published") {
                                    handleStatusFilterChange(value as AssetStatus);
                                }
                            }}
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
                        + New Asset
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className=" rounded-2xl border  overflow-hidden shadow-2xl" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                {!isInitialized || isLoading ? (
                    <div className="flex flex-col items-center justify-center py-24 gap-4">
                        <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                        <p className=" text-xs font-bold uppercase tracking-widest" style={{color: "var(--muted-foreground)"}}>Loading Registry...</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-20">
                        <p className="text-red-400 mb-4 text-sm font-medium">{error instanceof Error ? error.message : "Failed to load assets"}</p>
                        <button
                            onClick={() => refetch()}
                            className="px-6 py-2  hover:  rounded-lg text-xs font-bold uppercase tracking-widest transition-all" style={{color: "var(--foreground-secondary)", backgroundColor: "var(--surface-elevated)"}}
                        >
                            Try Again
                        </button>
                    </div>
                ) : assets.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="w-12 h-12  rounded-full flex items-center justify-center mx-auto mb-4 border /50" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                            <svg className="w-6 h-6 " style={{color: "var(--muted-foreground)"}} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                            </svg>
                        </div>
                        <p className=" text-sm font-medium italic" style={{color: "var(--muted-foreground)"}}>No assets found matching the selected criteria.</p>
                    </div>
                ) : (
                    <div className="animate-in fade-in duration-500">
                        <AssetTable
                            assets={assets}
                            statusFilter={statusFilter}
                            onStatusFilterChange={handleStatusFilterChange}
                        />
                    </div>
                )}
            </div>

            {showCreateModal && (
                <CreateAssetModal
                    onClose={() => setShowCreateModal(false)}
                    onSuccess={(assetId) => {
                        router.push(`/admin/assets/${assetId}`);
                    }}
                />
            )}
        </div>
    );
}
