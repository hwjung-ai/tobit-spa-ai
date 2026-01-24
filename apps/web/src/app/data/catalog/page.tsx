"use client";

import type React from "react";
import { Suspense, useMemo, useState } from "react";
import BuilderShell from "../../../components/builder/BuilderShell";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "../../../components/ui/button";
import { Badge } from "../../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Label } from "../../../components/ui/label";
import { Textarea } from "../../../components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs";
import { formatError } from "../../../lib/utils";
import { fetchApi } from "../../../lib/adminUtils";
import type { SchemaAssetResponse } from "../../../types/asset-registry";
import { useSearchParams } from "next/navigation";

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

interface SchemaCatalog {
  name: string;
  description?: string;
  source_ref: string;
  tables: SchemaTable[];
  last_scanned_at?: string;
  scan_status: "pending" | "scanning" | "completed" | "failed";
  scan_metadata?: Record<string, unknown>;
}

function CatalogContent() {
  const enableAssetRegistry = process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY !== "false";
  const searchParams = useSearchParams();
  const selectedAssetId = searchParams.get("asset_id");

  const [selectedSchema, setSelectedSchema] = useState<SchemaAssetResponse | null>(null);
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

  const schemasQuery = useQuery({
    queryKey: ["asset-registry", "schemas"],
    queryFn: async () => {
      const response = await fetchApi<{ assets: SchemaAssetResponse[] }>(
        "/asset-registry/schemas"
      );
      return response.data.assets ?? [];
    },
    enabled: enableAssetRegistry,
  });

  const catalogsQuery = useQuery({
    queryKey: ["asset-registry", "catalogs"],
    queryFn: async () => {
      const response = await fetchApi<{ assets: SchemaAssetResponse[] }>(
        "/asset-registry/schemas"
      );
      return response.data.assets ?? [];
    },
    enabled: enableAssetRegistry,
  });

  const scanMutation = useMutation({
    mutationFn: async ({ source_ref, options }: { source_ref: string; options: unknown }) => {
      const response = await fetchApi<ScanResult>(`/asset-registry/schemas/${source_ref}/scan`, {
        method: "POST",
        body: JSON.stringify({ source_ref, ...(options as Record<string, unknown>) }),
      });
      return response.data;
    },
    onSuccess: () => {
      catalogsQuery.refetch();
      setIsScanDialogOpen(false);
      setScanOptions({
        include_tables: [],
        exclude_tables: [],
        scan_options: {},
      });
      setSelectedTables({ include: [], exclude: [] });
    },
  });

  // Compute catalog map from query data directly
  const catalogMap = useMemo(() => {
    if (!catalogsQuery.data) return {};
    const map: Record<string, SchemaCatalog> = {};
    catalogsQuery.data.forEach((catalog) => {
      map[catalog.asset_id] = {
        name: catalog.name,
        description: catalog.description,
        source_ref: catalog.catalog.source_ref,
        tables: catalog.catalog.tables,
        last_scanned_at: catalog.catalog.last_scanned_at,
        scan_status: catalog.catalog.scan_status,
        scan_metadata: catalog.catalog.scan_metadata,
      };
    });
    return map;
  }, [catalogsQuery.data]);

  const handleScan = (sourceRef: string) => {
    const options = {
      include_tables: selectedTables.include.length > 0 ? selectedTables.include : undefined,
      exclude_tables: selectedTables.exclude.length > 0 ? selectedTables.exclude : undefined,
      scan_options: scanOptions.scan_options,
    };
    scanMutation.mutate({ source_ref: sourceRef, options });
  };

  const selectedSchemaFromParam = useMemo(() => {
    if (!selectedAssetId || !schemasQuery.data?.length) {
      return null;
    }
    return schemasQuery.data.find((schema) => schema.asset_id === selectedAssetId) ?? null;
  }, [selectedAssetId, schemasQuery.data]);

  const activeSchema = useMemo(() => {
    if (!selectedSchema) {
      return selectedSchemaFromParam;
    }
    const stillExists = schemasQuery.data?.some((schema) => schema.asset_id === selectedSchema.asset_id);
    return stillExists ? selectedSchema : selectedSchemaFromParam;
  }, [selectedSchema, selectedSchemaFromParam, schemasQuery.data]);

  const renderScanDialog = (sourceRef: string) => {
    const sourceName = schemasQuery.data?.find(s => s.asset_id === sourceRef)?.name || sourceRef;

    return (
      <Dialog open={isScanDialogOpen} onOpenChange={setIsScanDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Scan Schema</DialogTitle>
            <DialogDescription>
              Scan {sourceName} for database schema information
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
                onClick={() => handleScan(sourceRef)}
                disabled={scanMutation.isPending}
              >
                {scanMutation.isPending ? "Scanning..." : "Start Scan"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    );
  };

  if (!enableAssetRegistry) {
    return (
      <div className="min-h-screen bg-[#05070f] px-10 py-10 text-slate-200">
        <h1 className="text-2xl font-semibold">Catalog</h1>
        <p className="mt-4 text-sm text-slate-400">
          Asset Registry is disabled. Enable{" "}
          <code className="rounded bg-slate-800 px-2 py-1 text-xs">
            NEXT_PUBLIC_ENABLE_ASSET_REGISTRY
          </code>{" "}
          to continue.
        </p>
      </div>
    );
  }

  return (
    <div className="py-6 tracking-tight builder-shell builder-text">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Catalog</h1>
        <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Admin only
        </div>
      </div>
      <p className="mb-6 text-sm text-slate-400">
        Explore database schemas and table structures.
      </p>

      <Tabs defaultValue="schemas" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="schemas">Schemas</TabsTrigger>
          <TabsTrigger value="tables">Tables</TabsTrigger>
        </TabsList>

        <TabsContent value="schemas" className="space-y-4">
          <BuilderShell
            leftPane={
              <div className="space-y-3">
                <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                  Schemas ({schemasQuery.data?.length ?? 0})
                </div>
                <div className="custom-scrollbar max-h-[calc(100vh-300px)] space-y-2 overflow-auto pr-1">
                  {schemasQuery.isError && (
                    <div className="text-xs text-rose-300">
                      {formatError(schemasQuery.error)}
                    </div>
                  )}
                  {schemasQuery.data?.map((schema) => (
                    <div
                      key={schema.asset_id}
                      className={`rounded-xl border px-3 py-2 cursor-pointer ${activeSchema?.asset_id === schema.asset_id
                        ? "border-sky-500 bg-sky-500/10"
                        : "border-slate-800 hover:border-slate-600"
                        }`}
                      onClick={() => setSelectedSchema(schema)}
                    >
                      <div className="font-medium text-sm mb-1">{schema.name}</div>
                      <div className="text-xs text-slate-400 mb-2">
                        {schema.catalog.table_count} tables, {schema.catalog.column_count} columns
                      </div>
                      <div className="flex items-center justify-between">
                        <Badge
                          variant={
                            schema.catalog.scan_status === "completed" ? "default" :
                              schema.catalog.scan_status === "scanning" ? "secondary" :
                                schema.catalog.scan_status === "failed" ? "destructive" : "outline"
                          }
                          className="text-xs"
                        >
                          {schema.catalog.scan_status}
                        </Badge>
                        {schema.catalog.last_scanned_at && (
                          <div className="text-xs text-slate-400">
                            {new Date(schema.catalog.last_scanned_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  )) ?? []}
                  {!schemasQuery.data || schemasQuery.data.length === 0 && (
                    <div className="text-center py-8 text-sm text-slate-400">
                      No schemas found
                    </div>
                  )}
                </div>
              </div>
            }
            centerTop={
              activeSchema ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">{activeSchema.name}</h2>
                    <Badge variant="outline">
                      {activeSchema.catalog.table_count} tables
                    </Badge>
                  </div>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-xs">Overview</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div>Status: {activeSchema.catalog.scan_status}</div>
                      <div>Tables: {activeSchema.catalog.table_count}</div>
                      <div>Columns: {activeSchema.catalog.column_count}</div>
                      {activeSchema.catalog.last_scanned_at && (
                        <div>
                          Last scanned: {new Date(activeSchema.catalog.last_scanned_at).toLocaleString()}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {activeSchema.description && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-xs">Description</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-slate-300">
                          {activeSchema.description}
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
                        {activeSchema.catalog.source_ref}
                      </p>
                    </CardContent>
                  </Card>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsScanDialogOpen(true)}
                    >
                      Rescan
                    </Button>
                  </div>

                  {catalogMap[activeSchema.asset_id] && (
                    <div className="space-y-3">
                      <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                        Tables
                      </div>
                      <div className="custom-scrollbar max-h-[400px] space-y-2 overflow-auto pr-1">
                        {catalogMap[activeSchema.asset_id]?.tables.map((table) => (
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
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-slate-400">
                  Select a schema to explore
                </div>
              )
            }
            rightPane={
              <div className="space-y-3">
                <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                  Quick Actions
                </div>
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => {
                      if ((schemasQuery.data?.length ?? 0) > 0) {
                        setIsScanDialogOpen(true);
                      }
                    }}
                  >
                    Create New Scan
                  </Button>
                </div>

                <div className="text-xs uppercase tracking-[0.25em] text-slate-400 mt-6">
                  Scan Status
                </div>
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span>Completed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-yellow-500" />
                    <span>Scanning</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span>Failed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-slate-500" />
                    <span>Pending</span>
                  </div>
                </div>
              </div>
            }
          />
        </TabsContent>

        <TabsContent value="tables" className="space-y-4">
          <BuilderShell
            leftPane={
              <div className="space-y-3">
                <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                  All Tables
                </div>
                <div className="custom-scrollbar max-h-[calc(100vh-300px)] space-y-2 overflow-auto pr-1">
                  {Object.entries(catalogMap).flatMap(([schemaId, catalog]) =>
                    catalog.tables.map((table) => ({
                      schemaId,
                      tableName: table.name,
                      schemaName: table.schema_name,
                      table
                    }))
                  ).map(({ schemaId, tableName, schemaName, table }) => (
                    <div
                      key={`${schemaId}.${tableName}`}
                      className="rounded-xl border border-slate-800 px-3 py-2 text-sm hover:border-slate-600 cursor-pointer"
                    >
                      <div className="font-medium">{schemaName}.{tableName}</div>
                      <div className="text-xs text-slate-400">
                        {table.columns.length} columns
                      </div>
                    </div>
                  )) ?? []}
                  {Object.keys(catalogMap).length === 0 && (
                    <div className="text-center py-8 text-sm text-slate-400">
                      No tables found. Run a scan first.
                    </div>
                  )}
                </div>
              </div>
            }
            centerTop={
              <div className="flex items-center justify-center h-full text-sm text-slate-400">
                Select a table to view details
              </div>
            }
            rightPane={
              <div className="space-y-3">
                <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                  Tips
                </div>
                <div className="space-y-2 text-xs text-slate-300">
                  <p>• Click on a schema to see all its tables</p>
                  <p>• Use the scan dialog to update schema information</p>
                  <p>• Table columns include data types and constraints</p>
                </div>
              </div>
            }
          />
        </TabsContent>
      </Tabs>

      {renderScanDialog(activeSchema?.catalog.source_ref || "")}
    </div>
  );
}

export default function CatalogPage() {
  return (
    <Suspense fallback={<div className="p-4 text-slate-400">Loading...</div>}>
      <CatalogContent />
    </Suspense>
  );
}
