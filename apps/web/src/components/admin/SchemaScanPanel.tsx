"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaScanPanelProps {
  schema: any;
  onScanComplete: () => void;
}

export default function SchemaScanPanel({ schema, onScanComplete }: SchemaScanPanelProps) {
  const [scanning, setScanning] = useState(false);
  const [schemaNames, setSchemaNames] = useState("public");
  const [includeRowCounts, setIncludeRowCounts] = useState(false);

  const handleScan = async () => {
    setScanning(true);
    try {
      const schemas = schemaNames
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s);

      const response = await fetchApi(
        `/asset-registry/schemas/${schema.asset_id}/scan`,
        {
          method: "POST",
          body: JSON.stringify({
            schema_names: schemas.length > 0 ? schemas : null,
            include_row_counts: includeRowCounts,
          }),
        }
      );

      if (response.success) {
        alert("Schema scan completed successfully!");
        onScanComplete();
      } else {
        throw new Error(response.message || "Scan failed");
      }
    } catch (error) {
      alert(`Scan failed: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setScanning(false);
    }
  };

  const catalog = schema.content?.catalog || {};
  const scanStatus = catalog.scan_status || "pending";
  const lastScanned = catalog.last_scanned_at;
  const scanError = catalog.scan_error;

  const statusColor = {
    completed: "bg-green-100 text-green-800",
    scanning: "bg-yellow-100 text-yellow-800",
    failed: "bg-red-100 text-red-800",
    pending: "bg-gray-100 text-gray-800",
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold text-lg mb-4">Schema Discovery</h3>

      {/* Status */}
      <div className="mb-4 p-3 bg-gray-50 rounded">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-semibold text-sm">Status:</span>
            <span
              className={`ml-2 inline-block px-3 py-1 rounded text-xs font-medium ${
                statusColor[scanStatus as keyof typeof statusColor] || statusColor.pending
              }`}
            >
              {scanStatus}
            </span>
          </div>
        </div>
        {lastScanned && (
          <div className="text-sm text-gray-600 mt-2">
            Last scanned: {new Date(lastScanned).toLocaleString()}
          </div>
        )}
        {scanError && (
          <div className="text-sm text-red-600 mt-2">
            Error: {scanError}
          </div>
        )}
      </div>

      {/* Configuration */}
      <div className="space-y-3 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Schema Names (comma-separated)
          </label>
          <input
            type="text"
            value={schemaNames}
            onChange={(e) => setSchemaNames(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            placeholder="public, schema2, schema3"
            disabled={scanning}
          />
          <p className="mt-1 text-xs text-gray-500">
            For PostgreSQL, typically "public". For MySQL, use database name. For Oracle, use owner name.
          </p>
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="rowCounts"
            checked={includeRowCounts}
            onChange={(e) => setIncludeRowCounts(e.target.checked)}
            disabled={scanning}
            className="rounded border-gray-300"
          />
          <label htmlFor="rowCounts" className="ml-2 text-sm text-gray-700">
            Include row counts (slower for large tables)
          </label>
        </div>
      </div>

      {/* Scan Button */}
      <button
        onClick={handleScan}
        disabled={scanning || !schema.content?.source_ref}
        className={`w-full px-4 py-2 rounded-md font-medium text-white transition-colors ${
          scanning || !schema.content?.source_ref
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700"
        }`}
      >
        {scanning ? "Scanning..." : "Scan Database Schema"}
      </button>

      {!schema.content?.source_ref && (
        <p className="mt-2 text-sm text-red-600">
          ⚠️ Schema asset must have a source_ref configured before scanning
        </p>
      )}
    </div>
  );
}
