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
    const buildDetailUrl = (assetId: string) => {
        const params = new URLSearchParams();
        const type = searchParams?.get("type");
        const status = searchParams?.get("status");
        
        if (type) params.append("type", type);
        if (status) params.append("status", status);
        
        const queryString = params.toString();
        return `/admin/assets/${assetId}${queryString ? `?${queryString}` : ""}`;
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
                        href={buildDetailUrl(params.data.asset_id)}
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
                const colors = type === "prompt" ? "bg-purple-950/50 text-purple-300 border-purple-800/50" :
                    type === "mapping" ? "bg-blue-950/50 text-blue-300 border-blue-800/50" :
                    type === "policy" ? "bg-green-950/50 text-green-300 border-green-800/50" :
                    type === "query" ? "bg-orange-950/50 text-orange-300 border-orange-800/50" :
                    type === "screen" ? "bg-cyan-950/50 text-cyan-300 border-cyan-800/50" :
                    type === "source" ? "bg-slate-900/60 text-slate-200 border-slate-700/60" :
                    type === "schema" ? "bg-fuchsia-950/40 text-fuchsia-300 border-fuchsia-800/40" :
                    type === "resolver" ? "bg-amber-950/40 text-amber-200 border-amber-800/40" :
                        "bg-slate-950/50 text-slate-300 border-slate-800/50";
                return (
                    <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${colors}`}>
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
                const colors = status === "published" ? "bg-emerald-950/50 text-emerald-300 border-emerald-800/50" :
                    "bg-slate-800/50 text-slate-400 border-slate-700/50";
                return (
                    <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${colors}`}>
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
                <span className="text-slate-400 font-mono text-xs">v{params.value}</span>
            )
        },
        {
            headerName: "Updated",
            field: "updated_at",
            flex: 1,
            minWidth: 150,
            cellRenderer: (params: ICellRendererParams<Asset>) => (
                <span className="text-slate-500 text-xs">
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
                        href={buildDetailUrl(params.value)}
                        className="text-slate-500 hover:text-sky-400 transition-colors"
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
            <div className="text-center py-20 bg-slate-900/40 rounded-2xl border border-slate-800">
                <div className="w-12 h-12 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-700/50">
                    <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                    </svg>
                </div>
                <p className="text-slate-500 text-sm font-medium italic">No assets found</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col w-full h-full overflow-hidden">
            {/* Grid Header with Count */}
            <div className="flex justify-between items-center px-4 py-2 border-b border-slate-800 bg-slate-900/60 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">
                        Assets Registry
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 text-sky-400 text-[10px] font-mono font-bold border border-slate-700">
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
                                        : "bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-slate-300"
                                }`}
                            >
                                All
                            </button>
                            <button
                                onClick={() => onStatusFilterChange("draft")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "draft"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : "bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-slate-300"
                                }`}
                            >
                                Draft
                            </button>
                            <button
                                onClick={() => onStatusFilterChange("published")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "published"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : "bg-slate-800 text-slate-500 hover:bg-slate-700 hover:text-slate-300"
                                }`}
                            >
                                Published
                            </button>
                        </div>
                    )}
                </div>
                <div className="text-[10px] text-slate-500 font-medium italic">
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
