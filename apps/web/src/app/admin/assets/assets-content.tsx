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
            <div className="flex justify-between items-center rounded-2xl border bg-surface-elevated border-border p-4 backdrop-blur-sm">
                <div className="flex gap-6">
                    <div className="min-w-[160px]">
                        <label className="form-field-label">Asset Type</label>
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
                            className="input-container"
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
                        <label className="form-field-label">Lifecycle</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => {
                                const value = e.target.value;
                                if (value === "all" || value === "draft" || value === "published") {
                                    handleStatusFilterChange(value as AssetStatus);
                                }
                            }}
                            className="input-container"
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
                        className="text-label-sm font-bold uppercase tracking-widest text-muted-standard hover:text-primary"
                    >
                        Refresh
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
            <div className="insp-section">
                {error ? (
                    <div className="text-center py-20">
                        <p className="text-rose-500 dark:text-rose-400 mb-4 text-sm font-medium">{error instanceof Error ? error.message : "Failed to load assets"}</p>
                        <button
                            onClick={() => refetch()}
                            className="btn-secondary"
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    <div>
                        <AssetTable
                            assets={assets}
                            loading={!isInitialized || isLoading}
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
