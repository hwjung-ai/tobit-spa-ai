"use client";

import { useEffect, useState } from "react";
import { Asset, fetchApi } from "../../../lib/adminUtils";
import AssetTable from "../../../components/admin/AssetTable";

export default function AssetsPage() {
    const [assets, setAssets] = useState<Asset[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [typeFilter, setTypeFilter] = useState<"all" | "prompt" | "mapping" | "policy">("all");
    const [statusFilter, setStatusFilter] = useState<"all" | "draft" | "published">("all");

    const loadAssets = async () => {
        setIsLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams();
            if (typeFilter !== "all") params.append("asset_type", typeFilter);
            if (statusFilter !== "all") params.append("status", statusFilter);

            const queryString = params.toString();
            const endpoint = `/asset-registry/assets${queryString ? `?${queryString}` : ""}`;

            const response = await fetchApi<{ assets: Asset[] }>(endpoint);
            setAssets(response.data.assets);
        } catch (err: any) {
            setError(err.message || "Failed to load assets");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        loadAssets();
    }, [typeFilter, statusFilter]);

    return (
        <div className="p-6">
            <div className="max-w-7xl mx-auto">
                <div className="mb-6 flex justify-between items-end">
                    <div>
                        <h1 className="text-2xl font-semibold text-white mb-2">Assets Admin</h1>
                        <p className="text-slate-400 text-sm">
                            Manage operational assets including prompts, data mappings, and system policies.
                        </p>
                    </div>
                    <button
                        onClick={() => alert("Asset creation feature is coming in the next update.")}
                        className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg transition-colors font-medium text-sm shadow-lg shadow-sky-900/20"
                    >
                        + New Asset
                    </button>
                </div>

                {/* Filters Panel */}
                <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 mb-6 flex gap-4">
                    <div className="flex-1 max-w-xs">
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Asset Type</label>
                        <select
                            value={typeFilter}
                            onChange={(e) => setTypeFilter(e.target.value as any)}
                            className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
                        >
                            <option value="all">All Types</option>
                            <option value="prompt">Prompts</option>
                            <option value="mapping">Mappings</option>
                            <option value="policy">Policies</option>
                        </select>
                    </div>

                    <div className="flex-1 max-w-xs">
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Status</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value as any)}
                            className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-sky-500 transition-colors cursor-pointer"
                        >
                            <option value="all">Any Status</option>
                            <option value="draft">Draft Only</option>
                            <option value="published">Published Only</option>
                        </select>
                    </div>

                    <div className="flex-1 flex items-end">
                        <button
                            onClick={loadAssets}
                            className="px-4 py-2 text-slate-400 hover:text-slate-200 transition-colors text-sm"
                        >
                            Refresh List
                        </button>
                    </div>
                </div>

                {/* Content Table */}
                <div className="bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-4">
                            <div className="w-8 h-8 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                            <p className="text-slate-500 text-sm font-medium">Loading assets...</p>
                        </div>
                    ) : error ? (
                        <div className="text-center py-20">
                            <p className="text-red-400 mb-4">{error}</p>
                            <button
                                onClick={loadAssets}
                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm transition-colors font-medium"
                            >
                                Try Again
                            </button>
                        </div>
                    ) : (
                        <AssetTable assets={assets} />
                    )}
                </div>

                {!isLoading && !error && assets.length === 0 && (
                    <div className="text-center py-12 text-slate-500 italic">
                        No assets found matching the selected filters.
                    </div>
                )}
            </div>
        </div>
    );
}
