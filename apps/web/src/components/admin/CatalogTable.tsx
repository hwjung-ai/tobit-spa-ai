"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { fetchApi } from "@/lib/adminUtils";
import Toast from "./Toast";
import StatusBadge from "./StatusBadge";
import { useConfirm } from "@/hooks/use-confirm";

interface CatalogAsset {
  asset_id: string;
  name: string;
  description?: string;
  status: string;
  version: number;
  content?: {
    catalog?: {
      scan_status?: string;
      tables?: Array<Record<string, unknown>>;
    };
  };
  created_at?: string;
  updated_at?: string;
}

interface CatalogTableProps {
  catalogs: CatalogAsset[];
  selectedCatalog?: CatalogAsset | null;
  onSelect: (catalog: CatalogAsset) => void;
  onRefresh: () => void;
}

export default function CatalogTable({
  catalogs,
  selectedCatalog,
  onSelect,
  onRefresh,
}: CatalogTableProps) {
  const [deleting, setDeleting] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [confirmDialog, ConfirmDialogComponent] = useConfirm();

  const handleDelete = async (catalogId: string) => {
    const ok = await confirmDialog({
      title: "Delete Catalog",
      description: "Are you sure you want to delete this catalog?",
      confirmLabel: "Delete",
    });
    if (!ok) {
      return;
    }

    setDeleting(catalogId);
    try {
      await fetchApi(`/asset-registry/catalogs/${catalogId}`, {
        method: "DELETE",
      });
      onRefresh();
    } catch (error) {
      setToast({ message: `Failed to delete catalog: ${error}`, type: "error" });
    } finally {
      setDeleting(null);
    }
  };

  const getScanStatus = (catalog: CatalogAsset) => {
    return catalog.content?.catalog?.scan_status || "pending";
  };

  const getTableCount = (catalog: CatalogAsset) => {
    return catalog.content?.catalog?.tables?.length || 0;
  };

  return (
    <>
    <div className="space-y-2">
      {catalogs.length === 0 ? (
        <div className="text-center py-8 border border-variant rounded-lg text-muted-foreground bg-surface-overlay">
          No catalogs created yet
        </div>
      ) : (
        catalogs.map((catalog) => (
          <div
            key={catalog.asset_id}
            onClick={() => onSelect(catalog)}
            className={cn(
              "p-3 rounded-lg cursor-pointer transition-colors border border-variant bg-surface-overlay hover:bg-surface-elevated",
              selectedCatalog?.asset_id === catalog.asset_id &&
                "bg-sky-900/40 border-sky-500/50"
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm truncate text-foreground">{catalog.name}</h4>
                {catalog.description && (
                  <p className="text-xs truncate mt-1 text-muted-foreground">{catalog.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <span>Tables: {getTableCount(catalog)}</span>
                  <span>•</span>
                  <StatusBadge status={catalog.status} />
                  <span>•</span>
                  <span className={cn(
                    "px-2 py-0.5 rounded bg-surface-overlay text-muted-foreground",
                    getScanStatus(catalog) === "completed" && "bg-green-900/50 text-green-400",
                    getScanStatus(catalog) === "scanning" && "bg-yellow-900/50 text-yellow-400"
                  )}>
                    scan:{getScanStatus(catalog)}
                  </span>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(catalog.asset_id);
                }}
                disabled={deleting === catalog.asset_id}
                className="ml-2 text-xs px-2 py-1 text-red-400 hover:bg-red-900/30 rounded transition-colors disabled:opacity-50"
              >
                {deleting === catalog.asset_id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        ))
      )}
    </div>

    {/* Toast */}
    {toast && (
      <Toast
        message={toast.message}
        type={toast.type}
        onDismiss={() => setToast(null)}
      />
    )}

    {/* Confirm Dialog */}
    <ConfirmDialogComponent />
    </>
  );
}
