"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaScanPanelProps {
  schema: any;
  onScanComplete: () => void;
}

export default function CatalogScanPanel({ schema, onScanComplete }: SchemaScanPanelProps) {
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
        `/asset-registry/catalogs/${schema.asset_id}/scan`,
        {
          method: "POST",
          body: JSON.stringify({
            schema_names: schemas.length > 0 ? schemas : null,
            include_row_counts: includeRowCounts,
          }),
        }
      );

      if (response.code === 0) {
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
    completed: "bg-green-900/30 text-green-400",
    scanning: "bg-yellow-900/30 text-yellow-400",
    failed: "bg-red-900/30 text-red-400",
    pending: "bg-slate-800/50 text-slate-400",
  };

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4">
      <h3 className="font-semibold text-lg mb-4 text-slate-100">Schema Discovery</h3>

      {/* Status */}
      <div className="mb-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-semibold text-sm text-slate-300">Status:</span>
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
          <div className="text-sm text-slate-400 mt-2">
            Last scanned: {new Date(lastScanned).toLocaleString()}
          </div>
        )}
        {scanError && (
          <div className="text-sm text-red-400 mt-2">
            Error: {scanError}
          </div>
        )}
      </div>

      {/* Configuration */}
      <div className="space-y-3 mb-4">
        <div>
          <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
            Schema Names (comma-separated)
          </label>
          <input
            type="text"
            value={schemaNames}
            onChange={(e) => setSchemaNames(e.target.value)}
            className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500/50 transition-all disabled:opacity-50"
            placeholder="public, schema2, schema3"
            disabled={scanning}
          />
          <p className="mt-2 text-xs text-slate-500">
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
            className="rounded border-slate-600"
          />
          <label htmlFor="rowCounts" className="ml-2 text-sm text-slate-300">
            Include row counts (slower for large tables)
          </label>
        </div>
      </div>

      {/* Scan Button */}
      <button
        onClick={handleScan}
        disabled={scanning || !schema.content?.source_ref}
        className={`w-full px-4 py-3 rounded-lg font-medium text-white transition-all ${
          scanning || !schema.content?.source_ref
            ? "bg-slate-800 text-slate-600 cursor-not-allowed"
            : "bg-sky-600 hover:bg-sky-500"
        }`}
      >
        {scanning ? "Scanning..." : "Scan Database Schema"}
      </button>

      {!schema.content?.source_ref && (
        <p className="mt-2 text-sm text-red-400">
          ⚠️ Schema asset must have a source_ref configured before scanning
        </p>
      )}
    </div>
  );
}
