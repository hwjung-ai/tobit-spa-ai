"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/adminUtils";
import Toast from "./Toast";
import ValidationAlert from "./ValidationAlert";

interface CatalogAssetForScan {
  asset_id: string;
  content?: {
    source_ref?: string;
    catalog?: {
      scan_status?: string;
      last_scanned_at?: string;
      scan_error?: string;
    };
  };
}

interface SchemaScanPanelProps {
  schema: CatalogAssetForScan;
  onScanComplete: () => void;
}

function normalizeScanErrorMessage(rawMessage: string): string {
  const normalized = rawMessage.trim();
  if (!normalized || normalized === "INTERNAL_SERVER_ERROR") {
    return "Schema scan failed due to a server error. Please verify this is a real catalog asset and try again.";
  }
  if (normalized === "Invalid catalog asset_id format") {
    return "This catalog is not a persisted asset. Demo catalogs cannot be scanned.";
  }
  return normalized;
}

export default function CatalogScanPanel({ schema, onScanComplete }: SchemaScanPanelProps) {
  const [scanning, setScanning] = useState(false);
  const [schemaNames, setSchemaNames] = useState("public");
  const [includeRowCounts, setIncludeRowCounts] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);
  const canScan = !scanning && Boolean(schema.content?.source_ref);

  const handleScan = async () => {
    setScanning(true);
    setErrors([]);
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
        setToast({ message: "Schema scan completed successfully.", type: "success" });
        onScanComplete();
      } else {
        throw new Error(response.message || "Scan failed");
      }
    } catch (error) {
      const rawMessage = error instanceof Error ? error.message : String(error);
      const message = normalizeScanErrorMessage(rawMessage);
      setErrors([message]);
      setToast({ message: "Schema scan failed.", type: "error" });
    } finally {
      setScanning(false);
    }
  };

  const catalog = schema.content?.catalog ?? {};
  const scanStatus = catalog.scan_status || "pending";
  const lastScanned = catalog.last_scanned_at;
  const scanError = catalog.scan_error;

  const statusColor = {
    completed: "bg-green-900/30 text-green-400",
    scanning: "bg-yellow-900/30 text-yellow-400",
    failed: "bg-red-900/30 text-red-400",
    pending: "bg-surface-overlay text-muted-foreground",
  };

  return (
    <div className="rounded-lg border border-variant bg-surface-base p-4">
      {errors.length > 0 && (
        <div className="mb-4">
          <ValidationAlert errors={errors} onClose={() => setErrors([])} />
        </div>
      )}

      <h3 className="font-semibold text-lg mb-4 ">Schema Discovery</h3>

      {/* Status */}
      <div className="mb-4 rounded-lg border border-variant bg-surface-elevated p-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-semibold text-sm ">Status:</span>
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
          <div className="text-sm  mt-2">
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
          <label className="block text-xs font-bold  uppercase tracking-wider mb-2">
            Schema Names (comma-separated)
          </label>
          <input
            type="text"
            value={schemaNames}
            onChange={(e) => setSchemaNames(e.target.value)}
            className="w-full rounded-lg border border-variant bg-surface-base px-4 py-3 text-foreground placeholder:text-muted-foreground focus:border-sky-500/50 focus:outline-none transition-all disabled:opacity-50"
            placeholder="public, schema2, schema3"
            disabled={scanning}
          />
          { }
          <p className="mt-2 text-xs">
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
            className="rounded "
          />
          <label htmlFor="rowCounts" className="ml-2 text-sm ">
            Include row counts (slower for large tables)
          </label>
        </div>
      </div>

      {/* Scan Button */}
      <button
        onClick={handleScan}
        disabled={!canScan}
        className={`w-full px-4 py-3 rounded-lg font-medium text-foreground transition-all ${
          !canScan
            ? "  cursor-not-allowed"
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

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  );
}
