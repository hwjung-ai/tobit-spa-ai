"use client";

import { Asset, formatRelativeTime } from "../../lib/adminUtils";
import Link from "next/link";
import { useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

ModuleRegistry.registerModules([AllCommunityModule]);

interface AssetTableProps {
    assets: Asset[];
    statusFilter?: "all" | "draft" | "published";
    onStatusFilterChange?: (status: "all" | "draft" | "published") => void;
}

export default function AssetTable({ assets, statusFilter = "all", onStatusFilterChange }: AssetTableProps) {
    const searchParams = useSearchParams();
    
    // Build detail URL with preserved filter parameters
    const buildDetailUrl = (assetId: string, assetType?: string) => {
        const params = new URLSearchParams();
        const type = searchParams?.get("type");
        const status = searchParams?.get("status");

        if (type) params.append("type", type);
        if (status) params.append("status", status);

        const queryString = params.toString();
        // Screen assets have their own dedicated editor page
        const basePath = assetType === "screen" ? "/admin/screens" : "/admin/assets";
        return `${basePath}/${assetId}${queryString ? `?${queryString}` : ""}`;
    };
    const colDefs = useMemo<ColDef<Asset>[]>(() => [
        {
            headerName: "Name",
            field: "name",
            flex: 2,
            minWidth: 200,
            cellRenderer: (params: ICellRendererParams<Asset>) => {
                if (!params.data) return null;
                return (
                    <Link
                        href={buildDetailUrl(params.data.asset_id, params.data.asset_type)}
                        className="text-sky-400 hover:text-sky-300 font-medium transition-colors"
                    >
                        {params.value}
                    </Link>
                );
            }
        },
        {
            headerName: "Type",
            field: "asset_type",
            flex: 1,
            minWidth: 120,
            cellRenderer: (params: ICellRendererParams<Asset>) => {
                const type = params.value as string;
                const colors = type === "prompt" ? "bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-900/40 dark:text-purple-300 dark:border-purple-700/40" :
                    type === "mapping" ? "bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-700/40" :
                    type === "policy" ? "bg-green-100 text-green-700 border-green-300 dark:bg-green-900/40 dark:text-green-300 dark:border-green-700/40" :
                    type === "query" ? "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-700/40" :
                    type === "resolver" ? "bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-700/40" :
                        "";
                const style = type === "source"
                    ? { backgroundColor: "var(--surface-elevated)", color: "var(--foreground)", borderColor: "var(--border)" }
                    : !colors
                        ? { backgroundColor: "var(--surface-base)", color: "var(--foreground)", borderColor: "var(--border)" }
                        : undefined;
                return (
                    <span
                        className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${colors}`}
                        style={style}
                    >
                        {type}
                    </span>
                );
            }
        },
        {
            headerName: "Status",
            field: "status",
            flex: 1,
            minWidth: 120,
            cellRenderer: (params: ICellRendererParams<Asset>) => {
                const status = params.value as string;
                const colors = status === "published"
                    ? "bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700/40"
                    : "";
                const style = status === "published" ? undefined :
                    { backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)", borderColor: "var(--border)" };
                return (
                    <span
                        className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${colors}`}
                        style={style}
                    >
                        {status}
                    </span>
                );
            }
        },
        {
            headerName: "Version",
            field: "version",
            width: 100,
            cellRenderer: (params: ICellRendererParams<Asset>) => (
                <span className="font-mono text-xs" style={{ color: "var(--muted-foreground)" }}>v{params.value}</span>
            )
        },
        {
            headerName: "Updated",
            field: "updated_at",
            flex: 1,
            minWidth: 150,
            cellRenderer: (params: ICellRendererParams<Asset>) => (
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    {formatRelativeTime(params.value)}
                </span>
            )
        },
        {
            headerName: "Actions",
            field: "asset_id",
            width: 100,
            sortable: false,
            filter: false,
            pinned: "right",
            cellRenderer: (params: ICellRendererParams<Asset>) => (
                <div className="flex justify-end w-full pr-2">
                    <Link
                        href={buildDetailUrl(params.data?.asset_id ?? params.value, params.data?.asset_type)}
                        className="hover:text-sky-400 transition-colors"
                        style={{ color: "var(--muted-foreground)" }}
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </Link>
                </div>
            )
        }
    ], []);

    if (assets.length === 0) {
        return (
            <div className="text-center py-20 rounded-2xl border" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)" }}>
                <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 border" style={{ backgroundColor: "var(--surface-elevated)", borderColor: "var(--border)" }}>
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: "var(--muted-foreground)" }}>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                    </svg>
                </div>
                <p className="text-sm font-medium italic" style={{ color: "var(--muted-foreground)" }}>No assets found</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col w-full h-full overflow-hidden">
            {/* Grid Header with Count */}
            <div className="flex justify-between items-center px-4 py-2 border-b backdrop-blur-sm" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)" }}>
                <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" />
                    <span className="text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--muted-foreground)" }}>
                        Assets Registry
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border" style={{ backgroundColor: "var(--surface-elevated)", color: "#38bdf8", borderColor: "var(--border-muted)" }}>
                        count: {assets.length}
                    </span>
                    {/* Status Filter Buttons */}
                    {onStatusFilterChange && (
                        <div className="flex gap-1.5 ml-4">
                            <button
                                onClick={() => onStatusFilterChange("all")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "all"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : ""
                                }`}
                                style={statusFilter !== "all" ? { backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)" } : undefined}
                            >
                                All
                            </button>
                            <button
                                onClick={() => onStatusFilterChange("draft")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "draft"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : ""
                                }`}
                                style={statusFilter !== "draft" ? { backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)" } : undefined}
                            >
                                Draft
                            </button>
                            <button
                                onClick={() => onStatusFilterChange("published")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "published"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : ""
                                }`}
                                style={statusFilter !== "published" ? { backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)" } : undefined}
                            >
                                Published
                            </button>
                        </div>
                    )}
                </div>
                <div className="text-[10px] font-medium italic" style={{ color: "var(--muted-foreground)" }}>
                    Drag columns to reorder • Click headers to sort
                </div>
            </div>

            <div className="ag-theme-cep w-full overflow-hidden" style={{ height: '600px' }}>
                <AgGridReact
                    theme="legacy"
                    rowData={assets}
                    columnDefs={colDefs}
                    defaultColDef={{
                        sortable: true,
                        filter: true,
                        resizable: true,
                        suppressMovable: false,
                        unSortIcon: true,
                    }}
                    rowSelection="single"
                    animateRows={true}
                    headerHeight={44}
                    rowHeight={48}
                />
            </div>
        </div>
    );
}
