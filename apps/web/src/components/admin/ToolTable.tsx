"use client";

import { useCallback, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import { formatRelativeTime, fetchApi } from "../../lib/adminUtils";
import { cn } from "@/lib/utils";
import StatusBadge from "./StatusBadge";

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
  loading?: boolean;
  statusFilter?: "all" | "draft" | "published";
  onStatusFilterChange?: (status: "all" | "draft" | "published") => void;
  onToolSelect?: (tool: ToolAsset) => void;
  selectedToolId?: string;
  onRefresh?: () => void;
}

const filterBtnClass = (active: boolean) =>
  cn(
    "rounded-md h-6 px-2 text-[9px] font-medium uppercase tracking-wider transition hover:border-sky-500",
    active
      ? "bg-sky-600 text-white"
      : "border text-foreground hover:bg-surface-elevated dark:text-muted-foreground dark:hover:bg-surface-elevated",
    {
      "bg-surface-elevated": !active,
      "dark:bg-surface-base": !active,
      "border-variant": !active,
      "dark:border-variant": !active,
    },
  );

export default function ToolTable({
  tools,
  loading = false,
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
            <span className="inline-flex rounded-md border border-variant bg-surface-elevated px-2 py-0.5 text-tiny font-bold uppercase tracking-wider text-muted-foreground">
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
            className="block max-w-full truncate text-xs text-muted-foreground"
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
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => <StatusBadge status={String(params.value || "draft")} />,
      },
      {
        headerName: "Version",
        field: "version",
        width: 90,
        cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
          <span className="font-mono text-xs text-muted-foreground">
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
          <span className="text-xs text-muted-foreground">
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
                className="text-tiny font-bold uppercase tracking-wider text-muted-foreground transition-colors hover:text-sky-500"
                title="Test this tool"
              >
                Test
              </button>
              {tool.status === "draft" && (
                <button
                  onClick={(e) => void handlePublish(tool, e)}
                  disabled={isPublishing}
                  className="text-tiny font-bold uppercase tracking-wider text-emerald-600 transition-colors hover:text-emerald-500 disabled:opacity-50 dark:text-emerald-400 dark:hover:text-emerald-300"
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

  if (loading) {
    return (
      <div className="insp-section overflow-hidden flex h-full w-full flex-col shadow-sm">
        <div className="flex items-center justify-between border-b border-variant px-4 py-2">
          <div className="flex items-center gap-3">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-label-sm">
              Tool Registry
            </span>
          </div>
        </div>

        <div className="relative h-[600px] w-full overflow-hidden bg-surface-base">
          <div className="absolute inset-0 flex items-center justify-center gap-3">
            <div className="h-8 w-8 rounded-full border-2 border-sky-500/20 border-t-sky-500 animate-spin" />
            <span className="text-label text-muted-foreground">
              Loading Tools...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (tools.length === 0) {
    return (
      <div className="insp-section py-20 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-variant bg-surface-elevated">
          <svg
            className="h-6 w-6 text-muted-foreground"
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
        <p className="text-sm font-medium italic text-muted-foreground">
          No tools found
        </p>
      </div>
    );
  }

  return (
    <div className="insp-section overflow-hidden flex h-full w-full flex-col shadow-sm">
      <div className="flex items-center justify-between border-b border-variant px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          <span className="text-label-sm">
            Tool Registry
          </span>
          <span className="badge-primary font-mono text-success">
            count: {tools.length}
          </span>
          {onStatusFilterChange && (
            <div className="ml-4 flex gap-2">
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
      </div>

      <div className="ag-theme-quartz ag-theme-cep ag-theme-cep-static h-[600px] w-full overflow-hidden">
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
