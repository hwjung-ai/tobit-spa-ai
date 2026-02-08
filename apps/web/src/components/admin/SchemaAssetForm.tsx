"use client";

import type React from "react";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { fetchApi } from "../../lib/adminUtils";
import type { SchemaAssetResponse, SourceAssetResponse } from "../../types/asset-registry";

interface ScanResult {
  success: boolean;
  message: string;
  tables?: Array<{
    table_name: string;
    row_count?: number;
    columns?: string[];
  }>;
}

interface SchemaTable {
  name: string;
  schema_name: string;
  description?: string;
  columns: Array<{
    name: string;
    data_type: string;
    is_nullable: boolean;
    is_primary_key: boolean;
    is_foreign_key: boolean;
    foreign_key_table?: string;
    foreign_key_column?: string;
    default_value?: string;
    description?: string;
  }>;
  indexes?: Record<string, unknown>;
  constraints?: Record<string, unknown>;
  tags?: Record<string, unknown>;
}

interface SchemaAssetFormProps {
  asset: SchemaAssetResponse;
  onSave: () => void;
}

export default function SchemaAssetForm({ asset, onSave }: SchemaAssetFormProps) {
  const [isScanDialogOpen, setIsScanDialogOpen] = useState(false);
  const [scanOptions, setScanOptions] = useState({
    include_tables: [] as string[],
    exclude_tables: [] as string[],
    scan_options: {} as Record<string, unknown>,
  });
  const [selectedTables, setSelectedTables] = useState<{
    include: string[];
    exclude: string[];
  }>({ include: [], exclude: [] });

  // Provide default catalog if not present
  const catalog = asset.catalog ?? {
    name: asset.name,
    source_ref: "",
    tables: [],
    scan_status: "pending" as const,
    table_count: 0,
    column_count: 0,
  };

  const sourcesQuery = useQuery({
    queryKey: ["asset-registry", "sources"],
    queryFn: async () => {
      const response = await fetchApi<{ assets: SourceAssetResponse[] }>(
        "/asset-registry/sources"
      );
      return response.data.assets ?? [];
    },
  });

  const scanMutation = useMutation({
    mutationFn: async ({ source_ref, options }: { source_ref: string; options: unknown }) => {
      const response = await fetchApi<ScanResult>(`/asset-registry/catalogs/${source_ref}/scan`, {
        method: "POST",
        body: JSON.stringify({ source_ref, ...(options as Record<string, unknown>) }),
      });
      return response.data;
    },
    onSuccess: () => {
      setIsScanDialogOpen(false);
      setScanOptions({
        include_tables: [],
        exclude_tables: [],
        scan_options: {},
      });
      setSelectedTables({ include: [], exclude: [] });
      onSave();
    },
  });

  const handleScan = (sourceRef: string) => {
    const options = {
      include_tables: selectedTables.include.length > 0 ? selectedTables.include : undefined,
      exclude_tables: selectedTables.exclude.length > 0 ? selectedTables.exclude : undefined,
      scan_options: scanOptions.scan_options,
    };
    scanMutation.mutate({ source_ref: sourceRef, options });
  };

  const catalogMap = useMemo(() => {
    return {
      name: asset.name,
      description: asset.description,
      source_ref: catalog.source_ref,
      tables: catalog.tables,
      last_scanned_at: catalog.last_scanned_at,
      scan_status: catalog.scan_status,
      scan_metadata: catalog.scan_metadata,
    };
  }, [asset, catalog]);

  const getSourceName = (sourceRef: string) => {
    return sourcesQuery.data?.find((s) => s.asset_id === sourceRef)?.name || sourceRef;
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs">Overview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>Status: {catalog.scan_status}</div>
          <div>Tables: {catalog.table_count ?? 0}</div>
          <div>Columns: {catalog.column_count ?? 0}</div>
          {catalog.last_scanned_at && (
            <div>
              Last scanned: {new Date(catalog.last_scanned_at).toLocaleString()}
            </div>
          )}
        </CardContent>
      </Card>

      {asset.description && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-300">
              {asset.description}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs">Source</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-300">
            {getSourceName(catalog.source_ref)}
          </p>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsScanDialogOpen(true)}
        >
          Rescan Schema
        </Button>
      </div>

      {catalogMap.tables && catalogMap.tables.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Tables ({catalogMap.tables.length})
          </div>
          <div className="custom-scrollbar max-h-[400px] space-y-2 overflow-auto pr-1">
            {catalogMap.tables.map((table) => (
              <Card key={table.name} className="border-slate-800">
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs">
                    {table.schema_name}.{table.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {table.description && (
                    <p className="text-xs text-slate-400">{table.description}</p>
                  )}
                  <div className="text-xs text-slate-300">
                    {table.columns.length} columns
                  </div>
                  {table.columns.slice(0, 3).map((col) => (
                    <div key={col.name} className="text-xs text-slate-400">
                      • {col.name}: {col.data_type}
                      {col.is_primary_key && " PK"}
                      {col.is_foreign_key && " FK"}
                    </div>
                  ))}
                  {table.columns.length > 3 && (
                    <div className="text-xs text-slate-400">
                      +{table.columns.length - 3} more columns
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <Dialog open={isScanDialogOpen} onOpenChange={setIsScanDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Scan Schema</DialogTitle>
            <DialogDescription>
              Scan {getSourceName(catalog.source_ref)} for database schema information
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Include Tables (optional)</Label>
              <Textarea
                placeholder="Enter table names, one per line"
                value={selectedTables.include.join("\n")}
                onChange={(e) => setSelectedTables({
                  ...selectedTables,
                  include: e.target.value.split("\n").filter(Boolean)
                })}
                rows={3}
              />
              <p className="text-xs text-slate-400">
                Specify tables to include in the scan. Leave empty to scan all tables.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Exclude Tables (optional)</Label>
              <Textarea
                placeholder="Enter table names, one per line"
                value={selectedTables.exclude.join("\n")}
                onChange={(e) => setSelectedTables({
                  ...selectedTables,
                  exclude: e.target.value.split("\n").filter(Boolean)
                })}
                rows={3}
              />
              <p className="text-xs text-slate-400">
                Specify tables to exclude from the scan.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Scan Options (JSON)</Label>
              <Textarea
                placeholder='{"max_tables": 100, "sample_data": true}'
                value={JSON.stringify(scanOptions.scan_options, null, 2)}
                onChange={(e) => {
                  try {
                    setScanOptions({
                      ...scanOptions,
                      scan_options: JSON.parse(e.target.value)
                    });
                  } catch {
                    // Invalid JSON, ignore
                  }
                }}
                rows={3}
              />
              <p className="text-xs text-slate-400">
                Additional scan options as JSON.
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsScanDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => handleScan(catalog.source_ref)}
                disabled={scanMutation.isPending}
              >
                {scanMutation.isPending ? "Scanning..." : "Start Scan"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
