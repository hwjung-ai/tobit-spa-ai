"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaViewerPanelProps {
  schema: any;
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

      if (response.code === 0) {
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
    <div className=" border  rounded-lg p-4" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
      <h3 className="font-semibold text-lg mb-4 " style={{color: "var(--foreground)"}}>Schema Structure</h3>

      {tables.length === 0 ? (
        <div className="text-center py-8 " style={{color: "var(--muted-foreground)"}}>
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
    <div className="border  rounded-lg overflow-hidden" style={{borderColor: "var(--border)"}}>
      {/* Table Header */}
      <div className="flex items-center justify-between p-3  hover:/70 transition-colors" style={{backgroundColor: "var(--surface-overlay)"}}>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <button
            onClick={onToggleExpanded}
            className="text-sm  hover: flex-shrink-0" style={{color: "var(--foreground-secondary)"}}
          >
            {isExpanded ? "▼" : "▶"}
          </button>

          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggleEnabled(e.target.checked)}
            disabled={isTogglingEnabled}
            className="rounded  flex-shrink-0" style={{borderColor: "var(--border)"}}
          />

          <span className="font-medium text-sm truncate " style={{color: "var(--foreground-secondary)"}}>{table.name}</span>

          {table.row_count !== null && table.row_count !== undefined && (
            <span className="text-xs  flex-shrink-0 ml-2" style={{color: "var(--muted-foreground)"}}>
              ({table.row_count.toLocaleString()} rows)
            </span>
          )}
        </div>

        {table.comment && (
          <span className="text-xs  ml-2 text-right flex-shrink-0 max-w-xs truncate" style={{color: "var(--muted-foreground)"}}>
            {table.comment}
          </span>
        )}
      </div>

      {/* Column List */}
      {isExpanded && (
        <div className="p-3 /50" style={{backgroundColor: "var(--surface-base)"}}>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b " style={{borderColor: "var(--border)"}}>
                <th className="text-left p-1 font-semibold " style={{color: "var(--muted-foreground)"}}>Column</th>
                <th className="text-left p-1 font-semibold " style={{color: "var(--muted-foreground)"}}>Type</th>
                <th className="text-left p-1 font-semibold " style={{color: "var(--muted-foreground)"}}>Key</th>
                <th className="text-left p-1 font-semibold " style={{color: "var(--muted-foreground)"}}>Null</th>
                <th className="text-left p-1 font-semibold " style={{color: "var(--muted-foreground)"}}>Comment</th>
              </tr>
            </thead>
            <tbody>
              {columns.length > 0 ? (
                columns.map((col, idx) => (
                  <tr key={idx} className="border-b  hover:" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                    <td className="p-1  font-mono" style={{color: "var(--foreground-secondary)"}}>{col.column_name}</td>
                    <td className="p-1 " style={{color: "var(--muted-foreground)"}}>{col.data_type}</td>
                    <td className="p-1 text-center">
                      {col.is_primary_key && <span title="Primary Key">🔑</span>}
                      {col.is_foreign_key && <span title="Foreign Key">🔗</span>}
                    </td>
                    <td className="p-1 text-center">
                      {col.is_nullable ? (
                        <span className="text-green-400">Yes</span>
                      ) : (
                        <span className="text-red-400">No</span>
                      )}
                    </td>
                    <td className="p-1  max-w-xs truncate" style={{color: "var(--muted-foreground)"}}>
                      {col.comment || col.default_value || "-"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="p-2 text-center " style={{color: "var(--muted-foreground)"}}>
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
