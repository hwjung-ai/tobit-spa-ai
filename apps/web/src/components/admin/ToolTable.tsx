"use client";

import { formatRelativeTime, fetchApi } from "../../lib/adminUtils";
import { useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

ModuleRegistry.registerModules([AllCommunityModule]);

// Tool Asset interface (duplicated here for component isolation)
interface ToolAsset {
    asset_id: string;
    asset_type: string;
    name: string;
    description: string | null;
    version: number;
    status: string;
    tool_type: string;
    tool_config: Record<string, unknown>;
    tool_input_schema: Record<string, unknown>;
    tool_output_schema: Record<string, unknown> | null;
    tags: Record<string, unknown> | null;
    created_by: string | null;
    published_by: string | null;
    published_at: string | null;
    created_at: string;
    updated_at: string;
}

interface ToolTableProps {
    tools: ToolAsset[];
    statusFilter?: "all" | "draft" | "published";
    onStatusFilterChange?: (status: "all" | "draft" | "published") => void;
    onToolSelect?: (tool: ToolAsset) => void;
    selectedToolId?: string;
    onRefresh?: () => void;
}

export default function ToolTable({
    tools,
    statusFilter = "all",
    onStatusFilterChange,
    onToolSelect,
    selectedToolId,
    onRefresh
}: ToolTableProps) {
    const [publishingId, setPublishingId] = useState<string | null>(null);

    const handlePublish = async (tool: ToolAsset, e: React.MouseEvent) => {
        e.stopPropagation();
        if (tool.status === "published") return;

        setPublishingId(tool.asset_id);
        try {
            await fetchApi(`/asset-registry/tools/${tool.asset_id}/publish`, {
                method: "POST",
            });
            onRefresh?.();
        } catch (error) {
            console.error("Publish failed:", error);
        } finally {
            setPublishingId(null);
        }
    };

    const colDefs = useMemo<ColDef<ToolAsset>[]>(() => [
        {
            headerName: "Name",
            field: "name",
            flex: 2,
            minWidth: 180,
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => {
                if (!params.data) return null;
                const isSelected = params.data.asset_id === selectedToolId;
                return (
                    <button
                        onClick={() => onToolSelect?.(params.data!)}
                        className={`text-left font-medium transition-colors ${
                            isSelected
                                ? "text-sky-300"
                                : "text-sky-400 hover:text-sky-300"
                        }`}
                    >
                        {params.value}
                    </button>
                );
            }
        },
        {
            headerName: "Type",
            field: "tool_type",
            flex: 1,
            minWidth: 130,
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => {
                const type = params.value as string;
                const colors =
                    type === "database_query" ? "bg-blue-950/50 text-blue-300 border-blue-800/50" :
                    type === "http_api" ? "bg-green-950/50 text-green-300 border-green-800/50" :
                    type === "graph_query" ? "bg-purple-950/50 text-purple-300 border-purple-800/50" :
                    type === "python_script" ? "bg-amber-950/50 text-amber-300 border-amber-800/50" :
                    "bg-[var(--surface-overlay)] text-[var(--foreground-secondary)] border-[var(--border)]";
                const label = type?.replace(/_/g, " ") || "unknown";
                return (
                    <span className={`inline-flex px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${colors}`}>
                        {label}
                    </span>
                );
            }
        },
        {
            headerName: "Description",
            field: "description",
            flex: 2,
            minWidth: 200,
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
                <span className=" text-xs truncate block max-w-full" style={{color: "var(--muted-foreground)"}} title={params.value || ""}>
                    {params.value || "-"}
                </span>
            )
        },
        {
            headerName: "Status",
            field: "status",
            width: 120,
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => {
                const status = params.value as string;
                const colors = status === "published"
                    ? "bg-emerald-950/50 text-emerald-300 border-emerald-800/50"
                    : "bg-[var(--surface-overlay)] text-[var(--muted-foreground)] border-[var(--border)]";
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
            width: 90,
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
                <span className=" font-mono text-xs" style={{color: "var(--muted-foreground)"}}>v{params.value}</span>
            )
        },
        {
            headerName: "Updated",
            field: "updated_at",
            flex: 1,
            minWidth: 120,
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
                <span className=" text-xs" style={{color: "var(--muted-foreground)"}}>
                    {formatRelativeTime(params.value)}
                </span>
            )
        },
        {
            headerName: "Actions",
            field: "asset_id",
            width: 140,
            sortable: false,
            filter: false,
            pinned: "right",
            cellRenderer: (params: ICellRendererParams<ToolAsset>) => {
                if (!params.data) return null;
                const tool = params.data;
                const isPublishing = publishingId === tool.asset_id;

                return (
                    <div className="flex items-center gap-2 pr-2">
                        <button
                            onClick={() => onToolSelect?.(tool)}
                            className=" hover:text-sky-400 transition-colors text-[10px] font-bold uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}
                            title="Test this tool"
                        >
                            Test
                        </button>
                        {tool.status === "draft" && (
                            <button
                                onClick={(e) => handlePublish(tool, e)}
                                disabled={isPublishing}
                                className="text-emerald-500 hover:text-emerald-400 transition-colors text-[10px] font-bold uppercase tracking-wider disabled:opacity-50"
                                title="Publish this tool"
                            >
                                {isPublishing ? "..." : "Publish"}
                            </button>
                        )}
                    </div>
                );
            }
        }
    ], [selectedToolId, publishingId, onToolSelect, onRefresh]);

    if (tools.length === 0) {
        return (
            <div className="text-center py-20  rounded-2xl border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                <div className="w-12 h-12 /50 rounded-full flex items-center justify-center mx-auto mb-4 border /50" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-elevated)"}}>
                    <svg className="w-6 h-6 " style={{color: "var(--muted-foreground)"}} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
                    </svg>
                </div>
                <p className=" text-sm font-medium italic" style={{color: "var(--muted-foreground)"}}>No tools found</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col w-full h-full overflow-hidden">
            {/* Grid Header with Count */}
            <div className="flex justify-between items-center px-4 py-2 border-b   backdrop-blur-sm" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                <div className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-bold  uppercase tracking-[0.2em]" style={{color: "var(--muted-foreground)"}}>
                        Tool Registry
                    </span>
                    <span className="px-2 py-0.5 rounded-full  text-emerald-400 text-[10px] font-mono font-bold border " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-elevated)"}}>
                        count: {tools.length}
                    </span>
                    {/* Status Filter Buttons */}
                    {onStatusFilterChange && (
                        <div className="flex gap-1.5 ml-4">
                            <button
                                onClick={() => onStatusFilterChange("all")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "all"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : " 0 hover: hover:"
                                }`} style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)"}}
                            >
                                All
                            </button>
                            <button
                                onClick={() => onStatusFilterChange("draft")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "draft"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : " 0 hover: hover:"
                                }`} style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)"}}
                            >
                                Draft
                            </button>
                            <button
                                onClick={() => onStatusFilterChange("published")}
                                className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all ${
                                    statusFilter === "published"
                                        ? "bg-sky-600 text-white shadow-lg shadow-sky-900/20"
                                        : " 0 hover: hover:"
                                }`} style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)"}}
                            >
                                Published
                            </button>
                        </div>
                    )}
                </div>
                <div className="text-[10px]  font-medium italic" style={{color: "var(--muted-foreground)"}}>
                    Click row to test • Click headers to sort
                </div>
            </div>

            <div className="ag-theme-cep w-full overflow-hidden" style={{height: '600px'}}>
                <AgGridReact
                    theme="legacy"
                    rowData={tools}
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
                    onRowClicked={(event) => {
                        if (event.data) {
                            onToolSelect?.(event.data);
                        }
                    }}
                    rowClassRules={{
                        'bg-sky-900/20': (params) => params.data?.asset_id === selectedToolId,
                    }}
                />
            </div>
        </div>
    );
}
