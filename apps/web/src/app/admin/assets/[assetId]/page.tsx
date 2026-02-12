"use client";

import { Suspense, useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";
import { Asset, fetchApi } from "../../../../lib/adminUtils";
import AssetForm from "../../../../components/admin/AssetForm";
import Link from "next/link";
import { useConfirm } from "@/hooks/use-confirm";
import { type TraceSummaryRow } from "@/lib/apiClientTypes";

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
            <div className="min-h-screen px-6 py-10">
                <div className="flex h-full flex-col items-center justify-center gap-4 rounded-3xl border p-12" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)" }}>
                    <div className="w-12 h-12 border-2 rounded-full animate-spin" style={{ borderColor: "var(--border)", borderTopColor: "var(--primary)" }}></div>
                    <p className="text-[var(--muted-foreground)] font-medium" style={{ color: "var(--foreground)" }}>Loading asset details...</p>
                    <Link
                        href={backUrl}
                        className="mt-6 px-6 py-2 text-white rounded-lg transition-all font-medium inline-block"
                        style={{ backgroundColor: "var(--surface-elevated)" }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "var(--primary)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "var(--surface-elevated)"; }}
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
                <div className="flex h-full flex-col items-center justify-center rounded-3xl border p-12" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)" }}>
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4" style={{ backgroundColor: "rgba(var(--error-rgb), 0.15)", color: "var(--error)" }}>
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold mb-2" style={{ color: "var(--foreground)" }}>Error Loading Asset</h2>
                    <p className="mb-8 max-w-xl text-center text-[var(--muted-foreground)]" style={{ color: "var(--muted-foreground)" }}>{(error as Error)?.message || "The requested asset could not be found or retrieved from the server."}</p>
                    <Link
                        href={backUrl}
                        className="px-6 py-2 text-white rounded-lg transition-all font-medium inline-block"
                        style={{ backgroundColor: "var(--surface-elevated)" }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "var(--primary)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "var(--surface-elevated)"; }}
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
                        href={backUrl}
                        className="font-medium text-sm flex items-center gap-1 transition-colors"
                        style={{ color: "var(--primary)" }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = "var(--primary-foreground)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = "var(--primary)"; }}
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Assets List
                    </Link>
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-6">
                        <h1 className="text-3xl font-bold tracking-tight leading-none" style={{ color: "var(--foreground)" }}>
                            {asset.name}
                        </h1>
                        <span className="inline-flex px-3 py-1 rounded-full text-[10px] uppercase font-bold tracking-widest border" style={{
                            backgroundColor: asset.status === "published" ? "rgba(var(--success-rgb), 0.15)" : "var(--surface-elevated)",
                            color: asset.status === "published" ? "var(--success)" : "var(--muted-foreground)",
                            borderColor: asset.status === "published" ? "rgba(var(--success-rgb), 0.3)" : "var(--border)"
                        }}>
                            {asset.status}
                        </span>
                    </div>
                    <p className="text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                        Asset ID: <span className="font-mono" style={{ color: "var(--foreground)" }}>{asset.asset_id}</span>
                        <span className="mx-2" style={{ color: "var(--foreground)" }}>|</span>
                        Type: <span className="capitalize" style={{ color: "var(--foreground)" }}>{asset.asset_type}</span>
                        <span className="mx-2" style={{ color: "var(--foreground)" }}>|</span>
                        Version: <span className="font-mono" style={{ color: "var(--foreground)" }}>v{asset.version}</span>
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
                            className="px-5 py-2.5 border rounded-xl transition-all font-bold text-[10px] uppercase tracking-widest"
                            style={{ backgroundColor: "var(--surface-overlay)", color: "var(--foreground-secondary)", borderColor: "var(--border)" }}
                            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                        >
                            Open in Data
                        </Link>
                    )}
                    {asset.status === "draft" && (
                        <button
                            onClick={handleDelete}
                            className="px-5 py-2.5 border rounded-xl transition-all font-bold text-[10px] uppercase tracking-widest"
                            style={{ backgroundColor: "rgba(var(--error-rgb), 0.15)", color: "var(--error)", borderColor: "rgba(var(--error-rgb), 0.4)" }}
                            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "rgba(var(--error-rgb), 0.25)"; e.currentTarget.style.borderColor = "var(--error)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "rgba(var(--error-rgb), 0.15)"; e.currentTarget.style.borderColor = "rgba(var(--error-rgb), 0.4)"; }}
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
                            className="px-5 py-2.5 border rounded-xl transition-all font-bold text-[10px] uppercase tracking-widest"
                            style={{ backgroundColor: "rgba(var(--warning-rgb), 0.15)", color: "var(--warning)", borderColor: "rgba(var(--warning-rgb), 0.4)" }}
                            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "rgba(var(--warning-rgb), 0.25)"; e.currentTarget.style.borderColor = "var(--warning)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "rgba(var(--warning-rgb), 0.15)"; e.currentTarget.style.borderColor = "rgba(var(--warning-rgb), 0.4)"; }}
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
                <div className="rounded-3xl border p-6 space-y-4" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)" }}>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h2 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>Applied Traces</h2>
                            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>이 asset이 사용된 trace 목록</p>
                        </div>
                        <Link
                            href={`/admin/inspector?asset_id=${asset.asset_id}`}
                            className="text-[10px] uppercase tracking-[0.2em] border rounded-full px-3 py-1 transition"
                            style={{ color: "var(--foreground-secondary)", borderColor: "var(--border)" }}
                            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                        >
                            Open in Inspector
                        </Link>
                    </div>
                    {tracesLoading ? (
                        <p className="text-sm" style={{ color: "var(--foreground)" }}>Loading traces...</p>
                    ) : tracesError ? (
                        <p className="text-sm" style={{ color: "var(--error)" }}>
                            {(tracesError as Error)?.message || "Failed to load traces"}
                        </p>
                    ) : traceData?.traces?.length ? (
                        <div className="divide-y" style={{ borderColor: "var(--border-muted)" }}>
                            {traceData.traces.map((trace) => (
                                <Link
                                    key={trace.trace_id}
                                    href={`/admin/inspector?trace_id=${trace.trace_id}`}
                                    className="block py-3 rounded-xl transition"
                                    style={{ backgroundColor: "var(--surface-base)" }}
                                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "var(--surface-elevated)"; }}
                                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "var(--surface-base)"; }}
                                >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="text-sm font-medium" style={{ color: "var(--foreground-secondary)" }}>{trace.question_snippet}</div>
                                        <div className="text-[11px] font-mono" style={{ color: "var(--foreground)" }}>
                                            {new Date(trace.created_at).toLocaleString("ko-KR")}
                                        </div>
                                    </div>
                                    <div className="mt-1 flex items-center gap-3 text-[11px]" style={{ color: "var(--foreground)" }}>
                                        <span className="uppercase tracking-[0.2em]">{trace.feature}</span>
                                        <span style={{ color: trace.status === "error" ? "var(--error)" : "var(--success)" }}>
                                            {trace.status}
                                        </span>
                                        <span>{trace.duration_ms} ms</span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm" style={{ color: "var(--foreground)" }}>No traces found for this asset yet.</p>
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
        <Suspense fallback={<div className="min-h-screen px-6 py-10 flex items-center justify-center" style={{ color: "var(--muted-foreground)" }}>Loading asset details...</div>}>
            <AssetDetailPageContent />
        </Suspense>
    );
}
