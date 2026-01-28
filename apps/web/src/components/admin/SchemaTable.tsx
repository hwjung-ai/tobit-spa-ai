"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaAsset {
  asset_id: string;
  name: string;
  description?: string;
  status: string;
  version: number;
  content?: any;
  created_at?: string;
  updated_at?: string;
}

interface SchemaTableProps {
  schemas: SchemaAsset[];
  selectedSchema?: SchemaAsset | null;
  onSelect: (schema: SchemaAsset) => void;
  onRefresh: () => void;
}

export default function SchemaTable({
  schemas,
  selectedSchema,
  onSelect,
  onRefresh,
}: SchemaTableProps) {
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleDelete = async (schemaId: string) => {
    if (!confirm("Are you sure you want to delete this schema?")) {
      return;
    }

    setDeleting(schemaId);
    try {
      await fetchApi(`/asset-registry/schemas/${schemaId}`, {
        method: "DELETE",
      });
      onRefresh();
    } catch (error) {
      alert(`Failed to delete schema: ${error}`);
    } finally {
      setDeleting(null);
    }
  };

  const getScanStatus = (schema: SchemaAsset) => {
    return schema.content?.catalog?.scan_status || "pending";
  };

  const getTableCount = (schema: SchemaAsset) => {
    return schema.content?.catalog?.tables?.length || 0;
  };

  return (
    <div className="space-y-2">
      {schemas.length === 0 ? (
        <div className="text-center py-8 text-gray-500 bg-white rounded-lg">
          No schemas created yet
        </div>
      ) : (
        schemas.map((schema) => (
          <div
            key={schema.asset_id}
            onClick={() => onSelect(schema)}
            className={`p-3 rounded-lg cursor-pointer transition-colors border ${
              selectedSchema?.asset_id === schema.asset_id
                ? "bg-blue-50 border-blue-300"
                : "bg-white border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-sm truncate">{schema.name}</h4>
                {schema.description && (
                  <p className="text-xs text-gray-600 truncate mt-1">{schema.description}</p>
                )}
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <span>Tables: {getTableCount(schema)}</span>
                  <span>•</span>
                  <span className={`px-2 py-0.5 rounded ${
                    getScanStatus(schema) === "completed"
                      ? "bg-green-100 text-green-700"
                      : getScanStatus(schema) === "scanning"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-gray-100 text-gray-700"
                  }`}>
                    {getScanStatus(schema)}
                  </span>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(schema.asset_id);
                }}
                disabled={deleting === schema.asset_id}
                className="ml-2 text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
              >
                {deleting === schema.asset_id ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
