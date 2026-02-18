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
import StatusBadge from "./StatusBadge";

ModuleRegistry.registerModules([AllCommunityModule]);

interface AssetTableProps {
  assets: Asset[];
  loading?: boolean;
  statusFilter?: "all" | "draft" | "published";
  onStatusFilterChange?: (status: "all" | "draft" | "published") => void;
}

const filterBtnClass = (active: boolean) =>
  cn(
    "rounded-md h-6 px-2 text-[9px] font-medium uppercase tracking-wider transition hover:border-sky-500",
    active
      ? "bg-sky-600 text-white"
      : "border text-foreground hover:bg-slate-100 dark:text-muted-foreground dark:hover:bg-surface-elevated",
    {
      "bg-surface-elevated": !active,
      "dark:bg-surface-base": !active,
      "border-variant": !active,
      "dark:border-variant": !active,
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
          const isSystem = params.data.is_system;
          return (
            <div className="flex items-center gap-2">
              <Link
                href={buildDetailUrl(params.data.asset_id, params.data.asset_type)}
                className="font-medium text-sky-600 transition-colors hover:text-sky-500 dark:text-sky-400 dark:hover:text-sky-300"
              >
                {params.value}
              </Link>
              {isSystem && (
                <span className="inline-flex h-5 items-center rounded-md border border-amber-500/50 bg-amber-500/10 px-2 text-tiny font-bold uppercase tracking-wider leading-none whitespace-nowrap text-amber-600 dark:text-amber-400">
                  System
                </span>
              )}
            </div>
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
            <span className="inline-flex rounded-md border border-variant bg-surface-elevated px-2 py-0.5 text-tiny font-bold uppercase tracking-wider text-muted-foreground">
              {type}
            </span>
          );
        },
      },
      {
        headerName: "System",
        field: "is_system",
        width: 110,
        valueGetter: (params) => Boolean(params.data?.is_system),
        cellRenderer: (params: ICellRendererParams<Asset>) => {
          const isSystem = Boolean(params.value);
          return (
            <span
              className={cn(
                "inline-flex h-5 items-center rounded-md px-2 text-tiny font-bold uppercase tracking-wider leading-none whitespace-nowrap",
                isSystem
                  ? "border border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-400"
                  : "border border-variant bg-surface-elevated text-muted-foreground",
              )}
            >
              {isSystem ? "Yes" : "No"}
            </span>
          );
        },
      },
      {
        headerName: "Status",
        field: "status",
        flex: 1,
        minWidth: 120,
        cellRenderer: (params: ICellRendererParams<Asset>) => <StatusBadge status={String(params.value || "draft")} />,
      },
      {
        headerName: "Version",
        field: "version",
        width: 100,
        cellRenderer: (params: ICellRendererParams<Asset>) => (
          <span className="font-mono text-xs text-muted-foreground">
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
          <span className="text-xs text-muted-foreground">
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
              className="text-muted-foreground transition-colors hover:text-sky-500 dark:text-muted-foreground dark:hover:text-sky-300"
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
          headerHeight={44}
          rowHeight={48}
        />
      </div>
    </div>
  );
}
