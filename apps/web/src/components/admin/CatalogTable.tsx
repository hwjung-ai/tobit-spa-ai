"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface CatalogAsset {
  asset_id: string;
  name: string;
  description?: string;
  status: string;
  version: number;
  content?: any;
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

  const handleDelete = async (catalogId: string) => {
    if (!confirm("Are you sure you want to delete this catalog?")) {
      return;
    }

    setDeleting(catalogId);
    try {
      await fetchApi(`/asset-registry/catalogs/${catalogId}`, {
        method: "DELETE",
      });
      onRefresh();
    } catch (error) {
      alert(`Failed to delete catalog: ${error}`);
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
    <div className="space-y-2">
      {catalogs.length === 0 ? (
        <div className="text-center py-8 text-gray-500 bg-white rounded-lg">
          No catalogs created yet
        </div>
      ) : (
        catalogs.map((catalog) => (
          <div
            key={catalog.asset_id}
            onClick={() => onSelect(catalog)}
            className={`p-3 rounded-lg cursor-pointer transition-colors border ${
              selectedCatalog?.asset_id === catalog.asset_id
                ? "bg-blue-50 border-blue-300"
                : "bg-white border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm truncate">{catalog.name}</h4>
                {catalog.description && (
                  <p className="text-xs text-gray-600 truncate mt-1">{catalog.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <span>Tables: {getTableCount(catalog)}</span>
                  <span>•</span>
                  <span className={`px-2 py-0.5 rounded ${
                    getScanStatus(catalog) === "completed"
                      ? "bg-green-100 text-green-700"
                      : getScanStatus(catalog) === "scanning"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-gray-100 text-gray-700"
                  }`}>
                    {getScanStatus(catalog)}
                  </span>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(catalog.asset_id);
                }}
                disabled={deleting === catalog.asset_id}
                className="ml-2 text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
              >
                {deleting === catalog.asset_id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
