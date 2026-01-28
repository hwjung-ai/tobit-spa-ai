"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaAsset {
    asset_id: string;
    name: string;
    content?: {
        catalog?: {
            tables?: Array<{
                name: string;
                schema_name?: string;
                description?: string;
                comment?: string;
                columns?: Array<{
                    column_name: string;
                    data_type: string;
                    is_nullable: boolean;
                    is_primary_key?: boolean;
                    is_foreign_key?: boolean;
                    foreign_key_table?: string;
                    foreign_key_column?: string;
                    comment?: string;
                    default_value?: string;
                }>;
                row_count?: number;
                enabled?: boolean;
            }>;
            scan_status?: string;
        };
    };
}

interface SchemaViewerPanelProps {
    schema: SchemaAsset;
    onRefresh?: () => void;
}

export default function SchemaViewerPanel({ schema, onRefresh }: SchemaViewerPanelProps) {
    const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

    const catalog = schema.content?.catalog || {};
    const tables = catalog.tables || [];

    const toggleTableExpanded = (tableName: string) => {
        const newExpanded = new Set(expandedTables);
        if (newExpanded.has(tableName)) {
            newExpanded.delete(tableName);
        } else {
            newExpanded.add(tableName);
        }
        setExpandedTables(newExpanded);
    };

    const handleToggleTable = async (tableName: string, currentEnabled: boolean) => {
        try {
            const response = await fetchApi(
                `/asset-registry/catalogs/${schema.asset_id}/tables/${tableName}/toggle`,
                {
                    method: "POST",
                    body: JSON.stringify({ enabled: !currentEnabled }),
                }
            );

            if (response.success) {
                onRefresh?.();
            } else {
                alert(`Failed to toggle table: ${response.message}`);
            }
        } catch (error) {
            alert(`Failed to toggle table: ${error instanceof Error ? error.message : String(error)}`);
        }
    };

    if (tables.length === 0) {
        return (
            <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4">
                <h3 className="font-semibold text-slate-200 mb-2">📋 Schema Structure</h3>
                <p className="text-sm text-slate-400">
                    {catalog.scan_status === "scanning"
                        ? "Scanning database schema..."
                        : "No tables found. Run schema scan first."}
                </p>
            </div>
        );
    }

    return (
        <div className="bg-slate-900/40 border border-slate-800 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-800">
                <h3 className="font-semibold text-slate-200">
                    📋 Schema Structure ({tables.length} tables)
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                    Click table names to view columns. Check boxes to enable/disable for Tool usage.
                </p>
            </div>

            {/* Tables List */}
            <div className="divide-y divide-slate-800 max-h-96 overflow-y-auto">
                {tables.map((table) => {
                    const isExpanded = expandedTables.has(table.name);
                    const enabled = table.enabled ?? true;
                    const columns = table.columns || [];

                    return (
                        <div key={table.name} className="p-4">
                            {/* Table Header */}
                            <div className="flex items-start gap-3">
                                {/* Checkbox */}
                                <input
                                    type="checkbox"
                                    checked={enabled}
                                    onChange={() => handleToggleTable(table.name, enabled)}
                                    className="mt-1 w-4 h-4 rounded border-slate-600 cursor-pointer"
                                />

                                {/* Expand Button & Table Name */}
                                <div className="flex-1 min-w-0">
                                    <button
                                        onClick={() => toggleTableExpanded(table.name)}
                                        className={`flex items-center gap-2 text-left w-full hover:text-slate-100 transition-colors ${
                                            enabled ? "text-slate-200" : "text-slate-500 opacity-50"
                                        }`}
                                    >
                                        <span className="text-sm font-mono">
                                            {isExpanded ? "▼" : "▶"}
                                        </span>
                                        <span className="font-medium truncate">{table.name}</span>
                                        {table.schema_name && table.schema_name !== "public" && (
                                            <span className="text-xs text-slate-500">
                                                ({table.schema_name})
                                            </span>
                                        )}
                                        {table.row_count !== null && table.row_count !== undefined && (
                                            <span className="text-xs text-slate-500 ml-auto flex-shrink-0">
                                                {table.row_count.toLocaleString()} rows
                                            </span>
                                        )}
                                    </button>

                                    {/* Table Comment */}
                                    {(table.comment || table.description) && (
                                        <p className="text-xs text-slate-500 mt-1">
                                            {table.comment || table.description}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Columns List (Expanded) */}
                            {isExpanded && columns.length > 0 && (
                                <div className="mt-3 ml-7 space-y-2">
                                    <div className="bg-slate-800/30 rounded border border-slate-800/50 overflow-hidden">
                                        <table className="w-full text-xs">
                                            <thead>
                                                <tr className="border-b border-slate-800/50 bg-slate-800/20">
                                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">
                                                        Column
                                                    </th>
                                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">
                                                        Type
                                                    </th>
                                                    <th className="px-3 py-2 text-center font-semibold text-slate-400">
                                                        Key
                                                    </th>
                                                    <th className="px-3 py-2 text-center font-semibold text-slate-400">
                                                        Null
                                                    </th>
                                                    <th className="px-3 py-2 text-left font-semibold text-slate-400">
                                                        Comment
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {columns.map((col, idx) => (
                                                    <tr
                                                        key={col.column_name}
                                                        className={`border-b border-slate-800/30 ${
                                                            idx % 2 === 0
                                                                ? "bg-transparent"
                                                                : "bg-slate-800/10"
                                                        }`}
                                                    >
                                                        <td className="px-3 py-2 font-mono text-slate-300">
                                                            {col.column_name}
                                                        </td>
                                                        <td className="px-3 py-2 text-slate-400">
                                                            {col.data_type}
                                                        </td>
                                                        <td className="px-3 py-2 text-center">
                                                            {col.is_primary_key ? (
                                                                <span
                                                                    title="Primary Key"
                                                                    className="text-yellow-400"
                                                                >
                                                                    🔑
                                                                </span>
                                                            ) : col.is_foreign_key ? (
                                                                <span
                                                                    title={`Foreign Key → ${col.foreign_key_table}.${col.foreign_key_column}`}
                                                                    className="text-blue-400"
                                                                >
                                                                    🔗
                                                                </span>
                                                            ) : (
                                                                <span className="text-slate-600">-</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2 text-center text-slate-400">
                                                            {col.is_nullable ? "✓" : "-"}
                                                        </td>
                                                        <td className="px-3 py-2 text-slate-500 max-w-xs truncate">
                                                            {col.comment || col.default_value ? (
                                                                <span title={col.comment || col.default_value}>
                                                                    {col.comment || `default: ${col.default_value}`}
                                                                </span>
                                                            ) : (
                                                                <span className="text-slate-600">-</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {isExpanded && columns.length === 0 && (
                                <div className="mt-2 ml-7 text-xs text-slate-500 italic">
                                    No columns found
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
