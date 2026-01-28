"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaViewerPanelProps {
  catalog: any;
  onRefresh: () => void;
}

export default function CatalogViewerPanel({ schema, onRefresh }: SchemaViewerPanelProps) {
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [togglingTable, setTogglingTable] = useState<string | null>(null);

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
    setTogglingTable(tableName);
    try {
      const response = await fetchApi(
        `/asset-registry/catalogs/${schema.asset_id}/tables/${tableName}/toggle`,
        {
          method: "POST",
          body: JSON.stringify({ enabled: !currentEnabled }),
        }
      );

      if (response.success) {
        onRefresh();
      } else {
        throw new Error(response.message || "Failed to toggle table");
      }
    } catch (error) {
      alert(`Failed to toggle table: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setTogglingTable(null);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold text-lg mb-4">Schema Structure</h3>

      {tables.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No tables found. Run schema scan first.
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {tables.map((table) => (
            <TableItem
              key={table.name}
              table={table}
              isExpanded={expandedTables.has(table.name)}
              onToggleExpanded={() => toggleTableExpanded(table.name)}
              onToggleEnabled={(enabled) => handleToggleTable(table.name, enabled)}
              isTogglingEnabled={togglingTable === table.name}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface TableItemProps {
  table: any;
  isExpanded: boolean;
  onToggleExpanded: () => void;
  onToggleEnabled: (enabled: boolean) => void;
  isTogglingEnabled: boolean;
}

function TableItem({
  table,
  isExpanded,
  onToggleExpanded,
  onToggleEnabled,
  isTogglingEnabled,
}: TableItemProps) {
  const enabled = table.enabled ?? true;
  const columns = table.columns || [];

  return (
    <div className="border border-gray-200 rounded">
      {/* Table Header */}
      <div className="flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <button
            onClick={onToggleExpanded}
            className="text-sm text-gray-600 hover:text-gray-900 flex-shrink-0"
          >
            {isExpanded ? "▼" : "▶"}
          </button>

          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggleEnabled(e.target.checked)}
            disabled={isTogglingEnabled}
            className="rounded border-gray-300 flex-shrink-0"
          />

          <span className="font-medium text-sm truncate">{table.name}</span>

          {table.row_count !== null && table.row_count !== undefined && (
            <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
              ({table.row_count.toLocaleString()} rows)
            </span>
          )}
        </div>

        {table.comment && (
          <span className="text-xs text-gray-600 ml-2 text-right flex-shrink-0 max-w-xs truncate">
            {table.comment}
          </span>
        )}
      </div>

      {/* Column List */}
      {isExpanded && (
        <div className="p-3 bg-white">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left p-1 font-semibold text-gray-700">Column</th>
                <th className="text-left p-1 font-semibold text-gray-700">Type</th>
                <th className="text-left p-1 font-semibold text-gray-700">Key</th>
                <th className="text-left p-1 font-semibold text-gray-700">Null</th>
                <th className="text-left p-1 font-semibold text-gray-700">Comment</th>
              </tr>
            </thead>
            <tbody>
              {columns.length > 0 ? (
                columns.map((col, idx) => (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="p-1 text-gray-900 font-mono">{col.column_name}</td>
                    <td className="p-1 text-gray-600">{col.data_type}</td>
                    <td className="p-1 text-center">
                      {col.is_primary_key && <span title="Primary Key">🔑</span>}
                      {col.is_foreign_key && <span title="Foreign Key">🔗</span>}
                    </td>
                    <td className="p-1 text-center">
                      {col.is_nullable ? (
                        <span className="text-green-600">Yes</span>
                      ) : (
                        <span className="text-red-600">No</span>
                      )}
                    </td>
                    <td className="p-1 text-gray-600 max-w-xs truncate">
                      {col.comment || col.default_value || "-"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="p-2 text-center text-gray-500">
                    No columns
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
