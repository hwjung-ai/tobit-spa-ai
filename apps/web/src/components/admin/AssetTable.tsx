"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import type { ColDef, ICellRendererParams } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

import { Asset, formatRelativeTime } from "../../lib/adminUtils";
import { cn } from "@/lib/utils";

ModuleRegistry.registerModules([AllCommunityModule]);

interface AssetTableProps {
  assets: Asset[];
  loading?: boolean;
  statusFilter?: "all" | "draft" | "published";
  onStatusFilterChange?: (status: "all" | "draft" | "published") => void;
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

export default function AssetTable({
  assets,
  loading = false,
  statusFilter = "all",
  onStatusFilterChange,
}: AssetTableProps) {
  const searchParams = useSearchParams();

  const buildDetailUrl = useCallback(
    (assetId: string, assetType?: string) => {
      const params = new URLSearchParams();
      const type = searchParams?.get("type");
      const status = searchParams?.get("status");

      if (type) params.append("type", type);
      if (status) params.append("status", status);

      const queryString = params.toString();
      const basePath = assetType === "screen" ? "/admin/screens" : "/admin/assets";
      return `${basePath}/${assetId}${queryString ? `?${queryString}` : ""}`;
    },
    [searchParams],
  );

  const colDefs = useMemo<ColDef<Asset>[]>(
    () => [
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
              className="font-medium text-sky-600 transition-colors hover:text-sky-500 dark:text-sky-400 dark:hover:text-sky-300"
            >
              {params.value}
            </Link>
          );
        },
      },
      {
        headerName: "Type",
        field: "asset_type",
        flex: 1,
        minWidth: 120,
        cellRenderer: (params: ICellRendererParams<Asset>) => {
          const type = String(params.value || "unknown");
          return (
            <span className="inline-flex rounded-md border border-slate-300 bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {type}
            </span>
          );
        },
      },
      {
        headerName: "Status",
        field: "status",
        flex: 1,
        minWidth: 120,
        cellRenderer: (params: ICellRendererParams<Asset>) => {
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
        width: 100,
        cellRenderer: (params: ICellRendererParams<Asset>) => (
          <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
            v{params.value}
          </span>
        ),
      },
      {
        headerName: "Updated",
        field: "updated_at",
        flex: 1,
        minWidth: 150,
        cellRenderer: (params: ICellRendererParams<Asset>) => (
          <span className="text-xs text-slate-600 dark:text-slate-400">
            {formatRelativeTime(params.value)}
          </span>
        ),
      },
      {
        headerName: "Actions",
        field: "asset_id",
        width: 100,
        sortable: false,
        filter: false,
        pinned: "right",
        cellRenderer: (params: ICellRendererParams<Asset>) => (
          <div className="flex w-full justify-end pr-2">
            <Link
              href={buildDetailUrl(
                params.data?.asset_id ?? String(params.value),
                params.data?.asset_type,
              )}
              className="text-slate-500 transition-colors hover:text-sky-500 dark:text-slate-400 dark:hover:text-sky-300"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </Link>
          </div>
        ),
      },
    ],
    [buildDetailUrl],
  );

  if (loading) {
    return (
      <div className="insp-section overflow-hidden flex h-full w-full flex-col shadow-sm">
        <div className="flex items-center justify-between border-b border-border px-4 py-2">
          <div className="flex items-center gap-3">
            <div className="h-1.5 w-1.5 rounded-full bg-sky-500" />
            <span className="text-label-sm">
              Assets Registry
            </span>
          </div>
        </div>

        <div className="relative h-[600px] w-full overflow-hidden bg-surface-base">
          <div className="absolute inset-0 flex items-center justify-center gap-3">
            <div className="h-8 w-8 rounded-full border-2 border-sky-500/20 border-t-sky-500 animate-spin" />
            <span className="text-label-sm text-muted-standard">
              Loading Registry...
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div className="insp-section py-20 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border bg-surface-elevated">
          <svg
            className="h-6 w-6 text-muted-standard"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
        </div>
        <p className="text-sm font-medium italic text-muted-standard">
          No assets found
        </p>
      </div>
    );
  }

  return (
    <div className="insp-section overflow-hidden flex h-full w-full flex-col shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="h-1.5 w-1.5 rounded-full bg-sky-500" />
          <span className="text-label-sm">
            Assets Registry
          </span>
          <span className="badge-primary font-mono text-primary">
            count: {assets.length}
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
        <div className="text-label-sm font-medium italic text-muted-standard">
          Drag columns to reorder • Click headers to sort
        </div>
      </div>

      <div className="ag-theme-cep ag-theme-cep-static w-full overflow-hidden" style={{ height: "600px" }}>
        <AgGridReact
          theme="legacy"
          rowData={assets}
          columnDefs={colDefs}
          defaultColDef={{
            sortable: true,
            filter: true,
            resizable: true,
            suppressMovable: true,
            unSortIcon: true,
          }}
          rowSelection="single"
          headerHeight={44}
          rowHeight={48}
        />
      </div>
    </div>
  );
}
