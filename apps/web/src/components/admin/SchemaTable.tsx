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
            await fetchApi(`/asset-registry/catalogs/${schemaId}`, {
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
                <div className="text-center py-8 text-slate-500 bg-slate-900/40 border border-slate-800 rounded-lg">
                    No schemas created yet
                </div>
            ) : (
                schemas.map((schema) => (
                    <div
                        key={schema.asset_id}
                        onClick={() => onSelect(schema)}
                        className={`p-3 rounded-lg cursor-pointer transition-colors border ${
                            selectedSchema?.asset_id === schema.asset_id
                                ? "bg-sky-900/40 border-sky-500/50"
                                : "bg-slate-900/40 border-slate-800 hover:bg-slate-900/60"
                        }`}
                    >
                        <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                                <h4 className="font-medium text-sm truncate text-slate-100">{schema.name}</h4>
                                {schema.description && (
                                    <p className="text-xs text-slate-400 truncate mt-1">{schema.description}</p>
                                )}
                                <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                                    <span>Tables: {getTableCount(schema)}</span>
                                    <span>•</span>
                                    <span
                                        className={`px-2 py-0.5 rounded ${
                                            getScanStatus(schema) === "completed"
                                                ? "bg-green-900/50 text-green-400"
                                                : getScanStatus(schema) === "scanning"
                                                ? "bg-yellow-900/50 text-yellow-400"
                                                : "bg-slate-800/50 text-slate-400"
                                        }`}
                                    >
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
                                className="ml-2 text-xs px-2 py-1 text-red-400 hover:bg-red-900/30 rounded transition-colors disabled:opacity-50"
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
