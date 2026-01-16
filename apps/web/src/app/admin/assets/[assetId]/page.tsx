"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Asset, fetchApi } from "../../../../lib/adminUtils";
import AssetForm from "../../../../components/admin/AssetForm";
import Link from "next/link";

import { useQuery } from "@tanstack/react-query";

export default function AssetDetailPage() {
    const params = useParams();
    const router = useRouter();
    const assetId = params.assetId as string;

    const { data: asset, isLoading, error, refetch } = useQuery({
        queryKey: ["asset", assetId],
        queryFn: async () => {
            const response = await fetchApi<{ asset: Asset }>(`/asset-registry/assets/${assetId}`);
            return response.data.asset;
        },
        enabled: !!assetId
    });

    if (isLoading) {
        return (
            <div className="p-6">
                <div className="max-w-5xl mx-auto flex flex-col items-center justify-center py-40">
                    <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin mb-4"></div>
                    <p className="text-slate-500 font-medium">Loading asset details...</p>
                </div>
            </div>
        );
    }

    if (error || !asset) {
        return (
            <div className="p-6">
                <div className="max-w-5xl mx-auto">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-950/30 text-red-500 mb-4">
                            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <h2 className="text-xl font-bold text-white mb-2">Error Loading Asset</h2>
                        <p className="text-slate-400 mb-8 max-w-md mx-auto">{(error as any)?.message || "The requested asset could not be found or retrieved from the server."}</p>
                        <Link
                            href="/admin/assets"
                            className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-all font-medium inline-block"
                        >
                            ← Return to Asset List
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="max-w-5xl mx-auto">
                {/* Header with Navigation */}
                <div className="mb-8 flex items-start justify-between">
                    <div className="flex-1">
                        <Link
                            href="/admin/assets"
                            className="text-sky-500 hover:text-sky-400 font-medium text-sm flex items-center gap-1 mb-4 transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Assets List
                        </Link>
                        <div className="flex items-center gap-3">
                            <h1 className="text-3xl font-bold text-white tracking-tight leading-none">
                                {asset.name}
                            </h1>
                            <span className={`inline-flex px-2 py-1 rounded text-[10px] uppercase font-bold tracking-widest ${asset.status === "published" ? "bg-green-500/10 text-green-500 border border-green-500/20" : "bg-slate-800 text-slate-400 border border-slate-700"
                                }`}>
                                {asset.status}
                            </span>
                        </div>
                        <p className="text-slate-400 mt-2 text-sm max-w-2xl leading-relaxed">
                            Asset ID: <span className="font-mono text-slate-500">{asset.asset_id}</span>
                            <span className="mx-2 text-slate-700">|</span>
                            Type: <span className="capitalize">{asset.asset_type}</span>
                            <span className="mx-2 text-slate-700">|</span>
                            Version: <span className="font-mono">v{asset.version}</span>
                        </p>
                    </div>

                    <div className="flex gap-2">
                        {/* Optional: Add History/Audit button here */}
                    </div>
                </div>

                {/* Content Section */}
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <AssetForm asset={asset} onSave={() => refetch()} />
                </div>
            </div>
        </div>
    );
}
