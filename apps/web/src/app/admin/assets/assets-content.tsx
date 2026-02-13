"use client";

import { useEffect, useState } from "react";
import { Asset, fetchApi } from "../../../lib/adminUtils";
import AssetTable from "../../../components/admin/AssetTable";
import CreateAssetModal from "../../../components/admin/CreateAssetModal";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import StatusFilterButtons from "../../../components/admin/StatusFilterButtons";

// Define types for select options
type AssetType = "all" | "prompt" | "mapping" | "policy" | "query" | "source" | "resolver";
type AssetStatus = "all" | "draft" | "published";

export default function AssetsPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const [typeFilter, setTypeFilter] = useState<AssetType>("all");
    const [statusFilter, setStatusFilter] = useState<AssetStatus>("all");
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [isInitialized, setIsInitialized] = useState(false);
    const [refreshNonce, setRefreshNonce] = useState(0);

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

    const { data: assets = [], isLoading, isFetching, error } = useQuery({
        queryKey: ["assets", typeFilter, statusFilter, refreshNonce],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (typeFilter !== "all") params.append("asset_type", typeFilter);
            if (statusFilter !== "all") params.append("status", statusFilter);

            const queryString = params.toString();
            const endpoint = `/asset-registry/assets${queryString ? `?${queryString}` : ""}`;
            const response = await fetchApi<{ assets: Asset[] }>(endpoint, { cache: "no-store" });
            return response.data.assets;
        }
    });

    const handleRefresh = () => {
        queryClient.removeQueries({ queryKey: ["assets"] });
        setRefreshNonce((prev) => prev + 1);
    };

    return (
        <div className="space-y-6">
            {/* Control Bar */}
            <div className="flex justify-between items-center rounded-2xl border bg-surface-elevated border-border p-4 backdrop-blur-sm">
                <div className="flex gap-6">
                    <div className="min-w-[160px]">
                        <label className="text-xs font-semibold tracking-wide text-muted-foreground">Asset Type</label>
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
                            className="input-container text-xs"
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
                        + New Asset
                    </button>
                </div>
            </div>

            {/* Content Area */}
            {error ? (
                <div className="text-center py-20">
                    <p className="text-rose-500 dark:text-rose-400 mb-4 text-sm font-medium">{error instanceof Error ? error.message : "Failed to load assets"}</p>
                    <button
                        onClick={() => {
                            void handleRefresh();
                        }}
                        className="btn-secondary"
                    >
                        Try Again
                    </button>
                </div>
            ) : (
                <AssetTable
                    assets={assets}
                    loading={!isInitialized || isLoading}
                />
            )}

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
