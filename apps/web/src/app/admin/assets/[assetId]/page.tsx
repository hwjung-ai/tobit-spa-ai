"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";
import { Asset, fetchApi } from "../../../../lib/adminUtils";
import AssetForm from "../../../../components/admin/AssetForm";
import Link from "next/link";
import { useConfirm } from "@/hooks/use-confirm";
import { type TraceSummaryRow } from "@/lib/apiClientTypes";
import { cn } from "@/lib/utils";

import { useQuery } from "@tanstack/react-query";

function AssetDetailPageContent() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const assetId = params.assetId as string;
    const [confirm, ConfirmDialogComponent] = useConfirm();

    // Build back URL with preserved filter parameters
    const backUrl = useMemo(() => {
        const params = new URLSearchParams();
        const type = searchParams?.get("type");
        const status = searchParams?.get("status");

        if (type) params.append("type", type);
        if (status) params.append("status", status);

        const queryString = params.toString();
        return `/admin/assets${queryString ? `?${queryString}` : ""}`;
    }, [searchParams]);

    const { data: asset, isLoading, error, refetch } = useQuery({
        queryKey: ["asset", assetId],
        queryFn: async () => {
            const response = await fetchApi<{ asset: Asset }>(`/asset-registry/assets/${assetId}`);
            return response.data.asset;
        },
        enabled: !!assetId
    });

    const shouldLoadTraces = ["source", "resolver"].includes(asset?.asset_type ?? "");
    const {
        data: traceData,
        isLoading: tracesLoading,
        error: tracesError,
    } = useQuery({
        queryKey: ["asset-traces", assetId],
        queryFn: async () => {
            const response = await fetchApi<{
                traces: TraceSummaryRow[];
                total: number;
                limit: number;
                offset: number;
            }>(`/asset-registry/assets/${assetId}/traces?limit=20`);
            return response.data;
        },
        enabled: !!assetId && shouldLoadTraces,
    });

    const handleDelete = async () => {
        const ok = await confirm({
            title: "Delete Asset",
            description: "Are you sure you want to delete this draft asset? This action cannot be undone.",
            confirmLabel: "Delete",
        });
        if (!ok) return;

        try {
            await fetchApi(`/asset-registry/assets/${assetId}`, { method: "DELETE" });
            router.push("/admin/assets");
        } catch (err: unknown) {
            alert((err as Error).message || "Failed to delete asset");
        }
    };

    const handleUnpublish = async () => {
        const ok = await confirm({
            title: "Rollback to Draft",
            description: "Are you sure you want to rollback this asset to draft? It will no longer be active until re-published.",
            confirmLabel: "Rollback",
        });
        if (!ok) return;

        try {
            await fetchApi(`/asset-registry/assets/${assetId}/unpublish`, { method: "POST" });
            refetch();
        } catch (err: unknown) {
            alert((err as Error).message || "Failed to rollback asset");
        }
    };

    if (isLoading) {
        return (
            <div className="min-h-screen px-4 py-6 md:px-6 md:py-8">
                <div className="flex h-full flex-col items-center justify-center gap-4 rounded-3xl border p-12 bg-surface-base border-border">
                    <div className="w-12 h-12 border-2 rounded-full animate-spin border-border-t-primary"></div>
                    <p className="text-muted-foreground font-medium text-foreground">Loading asset details...</p>
                    <Link
                        href={backUrl}
                        className="mt-6 px-6 py-2 text-white rounded-lg transition-all font-medium inline-block bg-surface-elevated hover:bg-sky-600"
                    >
                        ← Return to Asset List
                    </Link>
                </div>
            </div>
        );
    }

    if (error || !asset) {
        return (
            <div className="min-h-screen px-6 py-10">
                <div className="flex h-full flex-col items-center justify-center rounded-3xl border p-12 bg-surface-base border-border">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 bg-error/15 text-error">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold mb-2 text-foreground">Error Loading Asset</h2>
                    <p className="mb-8 max-w-xl text-center text-muted-foreground">{(error as Error)?.message || "The requested asset could not be found or retrieved from the server."}</p>
                    <Link
                        href={backUrl}
                        className="px-6 py-2 rounded-lg transition-all font-medium inline-block bg-surface-elevated text-foreground hover:bg-primary hover:text-white"
                    >
                        ← Return to Asset List
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen px-4 py-6 md:px-6 md:py-8 space-y-10">
            <div className="flex flex-col gap-8 xl:flex-row xl:items-start xl:justify-between">
                <div className="flex-1 space-y-4">
                    <Link
                        href={backUrl}
                        className="font-medium text-sm flex items-center gap-1 transition-colors text-primary hover:text-primary-foreground"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Assets List
                    </Link>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-6">
                        <h1 className="text-3xl font-bold tracking-tight leading-none text-foreground">
                            {asset.name}
                        </h1>
                        <span className={cn(
                          "inline-flex px-3 py-1 rounded-full text-tiny uppercase font-bold tracking-widest border",
                          asset.status === "published"
                            ? "bg-success/15 text-success border-success/30"
                            : "bg-surface-elevated text-muted-foreground border-border"
                        )}>
                            {asset.status}
                        </span>
                    </div>
                    <p className="text-sm leading-relaxed text-muted-foreground dark:text-muted-foreground">
                        Asset ID: <span className="font-mono text-foreground">{asset.asset_id}</span>
                        <span className="mx-2 text-foreground">|</span>
                        Type: <span className="capitalize text-foreground">{asset.asset_type}</span>
                        <span className="mx-2 text-foreground">|</span>
                        Version: <span className="font-mono text-foreground">v{asset.version}</span>
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    {["source", "resolver"].includes(asset.asset_type) && (
                        <Link
                            href={
                                asset.asset_type === "source"
                                    ? `/data/sources?asset_id=${asset.asset_id}`
                                    : `/data/resolvers?asset_id=${asset.asset_id}`
                            }
                            className="px-5 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest bg-surface-base text-foreground border-variant hover:border-sky-600 hover:bg-sky-600 dark:bg-surface-base dark:text-muted-foreground dark:border-variant dark:hover:border-sky-500 dark:hover:bg-sky-600"
                        >
                            Open in Data
                        </Link>
                    )}
                    {asset.status === "draft" && (
                        <button
                            onClick={handleDelete}
                            className="px-5 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest bg-error/15 text-error border-error/40 hover:bg-error/25 hover:border-error"
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
                            className="px-5 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest bg-warning/15 text-warning border-warning/40 hover:bg-warning/25 hover:border-warning"
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

            {shouldLoadTraces ? (
                <div className="rounded-3xl border p-6 space-y-4 bg-surface-base border-border">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h2 className="text-lg font-semibold text-foreground dark:text-slate-50">Applied Traces</h2>
                            <p className="text-xs text-foreground dark:text-muted-foreground">이 asset이 사용된 trace 목록</p>
                        </div>
                        <Link
                            href={`/admin/inspector?asset_id=${asset.asset_id}`}
                            className="text-tiny uppercase tracking-wider border border-variant rounded-full px-3 py-1 transition hover:border-sky-500 text-foreground dark:border-variant dark:text-muted-foreground"
                        >
                            Open in Inspector
                        </Link>
                    </div>
                    {tracesLoading ? (
                        <p className="text-sm text-foreground dark:text-slate-50">Loading traces...</p>
                    ) : tracesError ? (
                        <p className="text-sm text-rose-600 dark:text-rose-400">
                            {(tracesError as Error)?.message || "Failed to load traces"}
                        </p>
                    ) : traceData?.traces?.length ? (
                        <div className="divide-y border-variant dark:border-variant">
                            {traceData.traces.map((trace) => (
                                <Link
                                    key={trace.trace_id}
                                    href={`/admin/inspector?trace_id=${trace.trace_id}`}
                                    className="block py-3 rounded-xl transition bg-surface-elevated hover:bg-surface-elevated dark:bg-surface-elevated dark:hover:bg-surface-elevated"
                                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "var(--surface-base)"; }}
                                >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="text-sm font-medium text-foreground dark:text-muted-foreground">{trace.question_snippet}</div>
                                        <div className="text-xs font-mono text-foreground dark:text-slate-50">
                                            {new Date(trace.created_at).toLocaleString("ko-KR")}
                                        </div>
                                    </div>
                                    <div className="mt-1 flex items-center gap-3 text-xs text-foreground dark:text-slate-50">
                                        <span className="uppercase tracking-wider">{trace.feature}</span>
                                        <span className={trace.status === "error" ? "text-rose-600 dark:text-rose-400" : "text-emerald-600 dark:text-emerald-400"}>
                                            {trace.status}
                                        </span>
                                        <span>{trace.duration_ms} ms</span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-foreground">No traces found for this asset yet.</p>
                    )}
                </div>
            ) : null}
            <ConfirmDialogComponent />
        </div>
    );
}

// Wrapper component with Suspense boundary for useSearchParams
export default function AssetDetailPage() {
    return (
        <Suspense fallback={<div className="min-h-screen px-4 py-6 md:px-6 md:py-8 flex items-center justify-center text-muted-foreground">Loading asset details...</div>}>
            <AssetDetailPageContent />
        </Suspense>
    );
}
