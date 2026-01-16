"use client";

import { useState } from "react";
import { Asset, fetchApi } from "../../../lib/adminUtils";
import AssetTable from "../../../components/admin/AssetTable";
import CreateAssetModal from "../../../components/admin/CreateAssetModal";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

export default function AssetsPage() {
    const router = useRouter();
    const [typeFilter, setTypeFilter] = useState<"all" | "prompt" | "mapping" | "policy">("all");
    const [statusFilter, setStatusFilter] = useState<"all" | "draft" | "published">("all");
    const [showCreateModal, setShowCreateModal] = useState(false);

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
            <div className="flex justify-between items-center bg-slate-900/50 rounded-2xl border border-slate-800 p-4 backdrop-blur-sm">
                <div className="flex gap-6">
                    <div className="min-w-[160px]">
                        <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Asset Type</label>
                        <select
                            value={typeFilter}
                            onChange={(e) => setTypeFilter(e.target.value as any)}
                            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-sky-500/50 transition-all cursor-pointer"
                        >
                            <option value="all">All Categories</option>
                            <option value="prompt">Prompts</option>
                            <option value="mapping">Mappings</option>
                            <option value="policy">Policies</option>
                        </select>
                    </div>

                    <div className="min-w-[160px]">
                        <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Lifecycle</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value as any)}
                            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-sky-500/50 transition-all cursor-pointer"
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
                        className="text-slate-500 hover:text-slate-300 transition-colors text-[10px] font-bold uppercase tracking-widest px-2"
                    >
                        Refresh
                    </button>
                    <div className="w-px h-6 bg-slate-800" />
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="px-5 py-2.5 bg-sky-600 hover:bg-sky-500 text-white rounded-xl transition-all font-bold text-[10px] uppercase tracking-[0.2em] shadow-lg shadow-sky-900/20 active:scale-95"
                    >
                        + New Asset
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="bg-slate-900/40 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-24 gap-4">
                        <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                        <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">Loading Registry...</p>
                    </div>
                ) : error ? (
                    <div className="text-center py-20">
                        <p className="text-red-400 mb-4 text-sm font-medium">{(error as any)?.message || "Failed to load assets"}</p>
                        <button
                            onClick={() => refetch()}
                            className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-bold uppercase tracking-widest transition-all"
                        >
                            Try Again
                        </button>
                    </div>
                ) : assets.length === 0 ? (
                    <div className="text-center py-20">
                        <div className="w-12 h-12 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-700/50">
                            <svg className="w-6 h-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                            </svg>
                        </div>
                        <p className="text-slate-500 text-sm font-medium italic">No assets found matching the selected criteria.</p>
                    </div>
                ) : (
                    <div className="animate-in fade-in duration-500">
                        <AssetTable assets={assets} />
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
