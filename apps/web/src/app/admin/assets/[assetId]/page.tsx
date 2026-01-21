"use client";

import { useState } from "react";
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

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this draft asset? This action cannot be undone.")) return;

        try {
            await fetchApi(`/asset-registry/assets/${assetId}`, { method: "DELETE" });
            router.push("/admin/assets");
        } catch (err: unknown) {
            alert((err as Error).message || "Failed to delete asset");
        }
    };

    const handleUnpublish = async () => {
        if (!confirm("Are you sure you want to rollback this asset to draft? It will no longer be active until re-published.")) return;

        try {
            await fetchApi(`/asset-registry/assets/${assetId}/unpublish`, { method: "POST" });
            refetch();
        } catch (err: unknown) {
            alert((err as Error).message || "Failed to rollback asset");
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen px-6 py-10">
                <div className="flex h-full flex-col items-center justify-center gap-4 rounded-3xl border border-slate-800 bg-slate-900/40 p-12">
                    <div className="w-12 h-12 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                    <p className="text-slate-500 font-medium">Loading asset details...</p>
                </div>
            </div>
        );
    }

    if (error || !asset) {
        return (
            <div className="min-h-screen px-6 py-10">
                <div className="flex h-full flex-col items-center justify-center rounded-3xl border border-slate-800 bg-slate-900/40 p-12">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-950/30 text-red-500 mb-4">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">Error Loading Asset</h2>
                    <p className="text-slate-400 mb-8 max-w-xl text-center">{(error as Error)?.message || "The requested asset could not be found or retrieved from the server."}</p>
                    <Link
                        href="/admin/assets"
                        className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-all font-medium inline-block"
                    >
                        ← Return to Asset List
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen px-6 py-10 space-y-10">
            <div className="flex flex-col gap-8 xl:flex-row xl:items-start xl:justify-between">
                <div className="flex-1 space-y-4">
                    <Link
                        href="/admin/assets"
                        className="text-sky-500 hover:text-sky-400 font-medium text-sm flex items-center gap-1 transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Assets List
                    </Link>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-6">
                        <h1 className="text-3xl font-bold text-white tracking-tight leading-none">
                            {asset.name}
                        </h1>
                        <span className={`inline-flex px-3 py-1 rounded-full text-[10px] uppercase font-bold tracking-widest ${asset.status === "published" ? "bg-green-500/10 text-green-500 border border-green-500/20" : "bg-slate-800 text-slate-400 border border-slate-700"
                            }`}>
                            {asset.status}
                        </span>
                    </div>
                    <p className="text-slate-400 text-sm leading-relaxed">
                        Asset ID: <span className="font-mono text-slate-500">{asset.asset_id}</span>
                        <span className="mx-2 text-slate-700">|</span>
                        Type: <span className="capitalize">{asset.asset_type}</span>
                        <span className="mx-2 text-slate-700">|</span>
                        Version: <span className="font-mono">v{asset.version}</span>
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    {asset.status === "draft" && (
                        <button
                            onClick={handleDelete}
                            className="px-5 py-2.5 bg-rose-950/20 hover:bg-rose-900/40 text-rose-400 border border-rose-800/50 rounded-xl transition-all font-bold text-[10px] uppercase tracking-widest hover:border-rose-700"
                        >
                            <div className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                Delete Draft
                            </div>
                        </button>
                    )}
                    {asset.status === "published" && (
                        <button
                            onClick={handleUnpublish}
                            className="px-5 py-2.5 bg-amber-950/20 hover:bg-amber-900/40 text-amber-400 border border-amber-800/50 rounded-xl transition-all font-bold text-[10px] uppercase tracking-widest hover:border-amber-700"
                        >
                            <div className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 15l-3-3m0 0l3-3m-3 3h8M3 12a9 9 0 1118 0 9 9 0 01-18 0z" />
                                </svg>
                                Rollback to Draft
                            </div>
                        </button>
                    )}
                </div>
            </div>

            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <AssetForm asset={asset} onSave={() => refetch()} />
            </div>
        </div>
    );
}
