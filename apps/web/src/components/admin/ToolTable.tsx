"use client";

import { useCallback, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import { formatRelativeTime, fetchApi } from "../../lib/adminUtils";
import { cn } from "@/lib/utils";

ModuleRegistry.registerModules([AllCommunityModule]);

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

const filterBtnClass = (active: boolean) =>
  cn(
    "rounded-md px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition hover:border-sky-500",
    active
      ? "bg-sky-600 text-white"
      : "border text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
    {
      "bg-slate-50": !active,
      "dark:bg-slate-900": !active,
      "border-slate-300": !active,
      "dark:border-slate-700": !active,
    },
  );

export default function ToolTable({
  tools,
  statusFilter = "all",
  onStatusFilterChange,
  onToolSelect,
  selectedToolId,
  onRefresh,
}: ToolTableProps) {
  const [publishingId, setPublishingId] = useState<string | null>(null);

  const handlePublish = useCallback(
    async (tool: ToolAsset, e: React.MouseEvent) => {
      e.stopPropagation();
      if (tool.status === "published") return;

      setPublishingId(tool.asset_id);
      try {
        await fetchApi(`/asset-registry/tools/${tool.asset_id}/publish`, { method: "POST" });
        onRefresh?.();
      } catch (error) {
        console.error("Publish failed:", error);
      } finally {
        setPublishingId(null);
      }
    },
    [onRefresh],
  );

  const colDefs = useMemo<ColDef<ToolAsset>[]>(
    () => [
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
              className={cn(
                "text-left font-medium transition-colors",
                isSelected
                  ? "text-sky-500 dark:text-sky-300"
                  : "text-sky-600 hover:text-sky-500 dark:text-sky-400 dark:hover:text-sky-300",
              )}
            >
              {params.value}
            </button>
          );
        },
      },
      {
        headerName: "Type",
        field: "tool_type",
        flex: 1,
        minWidth: 130,
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => {
          const label = String(params.value || "unknown").replace(/_/g, " ");
          return (
            <span className="inline-flex rounded-md border border-slate-300 bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {label}
            </span>
          );
        },
      },
      {
        headerName: "Description",
        field: "description",
        flex: 2,
        minWidth: 200,
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
          <span
            className="block max-w-full truncate text-xs text-slate-600 dark:text-slate-400"
            title={params.value || ""}
          >
            {params.value || "-"}
          </span>
        ),
      },
      {
        headerName: "Status",
        field: "status",
        width: 120,
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => {
          const status = String(params.value || "draft");
          return (
            <span
              className={cn(
                "inline-flex rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                status === "published"
                  ? "border-emerald-300 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                  : "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300",
              )}
            >
              {status}
            </span>
          );
        },
      },
      {
        headerName: "Version",
        field: "version",
        width: 90,
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
          <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
            v{params.value}
          </span>
        ),
      },
      {
        headerName: "Updated",
        field: "updated_at",
        flex: 1,
        minWidth: 120,
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
          <span className="text-xs text-slate-600 dark:text-slate-400">
            {formatRelativeTime(params.value)}
          </span>
        ),
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
                className="text-[10px] font-bold uppercase tracking-wider text-slate-600 transition-colors hover:text-sky-500 dark:text-slate-400 dark:hover:text-sky-300"
                title="Test this tool"
              >
                Test
              </button>
              {tool.status === "draft" && (
                <button
                  onClick={(e) => void handlePublish(tool, e)}
                  disabled={isPublishing}
                  className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 transition-colors hover:text-emerald-500 disabled:opacity-50 dark:text-emerald-400 dark:hover:text-emerald-300"
                  title="Publish this tool"
                >
                  {isPublishing ? "..." : "Publish"}
                </button>
              )}
            </div>
          );
        },
      },
    ],
    [handlePublish, onToolSelect, publishingId, selectedToolId],
  );

  if (tools.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white py-20 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
          <svg
            className="h-6 w-6 text-slate-500 dark:text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"
            />
          </svg>
        </div>
        <p className="text-sm font-medium italic text-slate-600 dark:text-slate-400">
          No tools found
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/90">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600 dark:text-slate-400">
            Tool Registry
          </span>
          <span className="rounded-full border border-slate-300 bg-slate-50 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-600 dark:border-slate-700 dark:bg-slate-800 dark:text-emerald-400">
            count: {tools.length}
          </span>
          {onStatusFilterChange && (
            <div className="ml-4 flex gap-1.5">
              <button
                onClick={() => onStatusFilterChange("all")}
                className={filterBtnClass(statusFilter === "all")}
              >
                All
              </button>
              <button
                onClick={() => onStatusFilterChange("draft")}
                className={filterBtnClass(statusFilter === "draft")}
              >
                Draft
              </button>
              <button
                onClick={() => onStatusFilterChange("published")}
                className={filterBtnClass(statusFilter === "published")}
              >
                Published
              </button>
            </div>
          )}
        </div>
        <div className="text-[10px] font-medium italic text-slate-500 dark:text-slate-400">
          Click row to test • Click headers to sort
        </div>
      </div>

      <div className="ag-theme-cep w-full overflow-hidden" style={{ height: "600px" }}>
        <AgGridReact
          theme="legacy"
          rowData={tools}
          columnDefs={colDefs}
          defaultColDef={{
            sortable: true,
            filter: true,
            resizable: true,
            suppressMovable: true,
            unSortIcon: true,
          }}
          rowSelection="single"
          animateRows
          headerHeight={44}
          rowHeight={48}
          onRowClicked={(event) => {
            if (event.data) {
              onToolSelect?.(event.data);
            }
          }}
        />
      </div>
    </div>
  );
}
