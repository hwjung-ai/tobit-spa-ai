"use client";

import type React from "react";
import { Suspense, useMemo, useState, useEffect } from "react";
import BuilderShell from "../../../components/builder/BuilderShell";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Badge } from "../../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { Label } from "../../../components/ui/label";
import { Textarea } from "../../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { formatError } from "../../../lib/utils";
import { fetchApi } from "../../../lib/adminUtils";
import { useSearchParams } from "next/navigation";
import type { ConnectionTestResult, SourceAssetResponse, SourceType } from "../../../types/asset-registry";

const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  postgresql: "PostgreSQL",
  mysql: "MySQL",
  redis: "Redis",
  mongodb: "MongoDB",
  kafka: "Kafka",
  s3: "Amazon S3",
  bigquery: "Google BigQuery",
  snowflake: "Snowflake",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  active: "Active",
  inactive: "Inactive",
  deprecated: "Deprecated",
};

const formatStatus = (status: string) => {
  return STATUS_LABELS[status] || status;
};

function SourcesContent() {
  const enableAssetRegistry = process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY !== "false";
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    setSelectedAssetId(searchParams.get("asset_id"));
  }, [searchParams]);

  const [selectedSource, setSelectedSource] = useState<SourceAssetResponse | null>(null);
  const [editingSource, setEditingSource] = useState<Partial<SourceAssetResponse> | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const sourcesQuery = useQuery({
    queryKey: ["asset-registry", "sources"],
    queryFn: async () => {
      const response = await fetchApi<{ assets: SourceAssetResponse[] }>(
        "/asset-registry/sources"
      );
      return response.data.assets ?? [];
    },
    enabled: enableAssetRegistry,
  });

  const createMutation = useMutation({
    mutationFn: async (source: Partial<SourceAssetResponse>) => {
      const response = await fetchApi<SourceAssetResponse>("/asset-registry/sources", {
        method: "POST",
        body: JSON.stringify(source),
      });
      return response.data;
    },
    onSuccess: () => {
      sourcesQuery.refetch();
      setIsCreateDialogOpen(false);
      setEditingSource(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, source }: { id: string; source: Partial<SourceAssetResponse> }) => {
      const response = await fetchApi<SourceAssetResponse>(`/asset-registry/sources/${id}`, {
        method: "PUT",
        body: JSON.stringify(source),
      });
      return response.data;
    },
    onSuccess: () => {
      sourcesQuery.refetch();
      setIsEditDialogOpen(false);
      setEditingSource(null);
      setSelectedSource(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await fetchApi(`/asset-registry/sources/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      sourcesQuery.refetch();
      setSelectedSource(null);
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetchApi<ConnectionTestResult>(`/asset-registry/sources/${id}/test`, {
        method: "POST",
      });
      return response.data;
    },
    onSuccess: (data) => {
      setTestResults(data);
      setIsTestDialogOpen(true);
    },
  });


  const filteredSources = (sourcesQuery.data ?? []).filter(source =>
    source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    source.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedSourceFromParam = useMemo(() => {
    if (!selectedAssetId || !sourcesQuery.data?.length) {
      return null;
    }
    return sourcesQuery.data.find((source) => source.asset_id === selectedAssetId) ?? null;
  }, [selectedAssetId, sourcesQuery.data]);

  const activeSource = useMemo(() => {
    if (!selectedSource) {
      return selectedSourceFromParam;
    }
    const stillExists = sourcesQuery.data?.some((source) => source.asset_id === selectedSource.asset_id);
    return stillExists ? selectedSource : selectedSourceFromParam;
  }, [selectedSource, selectedSourceFromParam, sourcesQuery.data]);

  const handleCreateSource = () => {
    setEditingSource({
      asset_type: "source",
      name: "",
      description: "",
      source_type: "postgresql",
      connection: {
        host: "",
        port: 5432,
        username: "",
        database: "",
        timeout: 30,
        ssl_mode: "verify-full",
        connection_params: {},
      },
      scope: "",
      tags: {},
    });
    setIsCreateDialogOpen(true);
  };

  const handleEditSource = (source: SourceAssetResponse) => {
    setEditingSource(source);
    setIsEditDialogOpen(true);
  };

  const handleSaveSource = () => {
    if (editingSource) {
      if (isCreateDialogOpen) {
        createMutation.mutate(editingSource);
      } else if (editingSource.asset_id) {
        updateMutation.mutate({
          id: editingSource.asset_id,
          source: editingSource,
        });
      }
    }
  };

  const handleDeleteSource = (source: SourceAssetResponse) => {
    if (confirm(`Are you sure you want to delete "${source.name}"?`)) {
      deleteMutation.mutate(source.asset_id);
    }
  };

  const handleTestConnection = (source: SourceAssetResponse) => {
    setSelectedSource(source);
    testMutation.mutate(source.asset_id);
  };

  const renderConnectionForm = () => {
    if (!editingSource) return null;

    const sourceTypes = Object.keys(SOURCE_TYPE_LABELS) as SourceType[];

    return (
      <div className="space-y-6 max-h-[70vh] overflow-y-auto px-1 py-1 custom-scrollbar">
        {/* Basic Information Section */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-1 bg-sky-500 rounded-full" />
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Basic Information</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={editingSource.name || ""}
                onChange={(e) => setEditingSource({ ...editingSource, name: e.target.value })}
                placeholder="Database Production"
                className="bg-slate-900/50 border-slate-800 focus:border-sky-500/50 transition-colors"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="source_type">Source Type</Label>
              <Select
                value={editingSource.source_type}
                onValueChange={(value) => setEditingSource({
                  ...editingSource,
                  source_type: value as SourceType
                })}
              >
                <SelectTrigger className="bg-slate-900/50 border-slate-800">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800">
                  {sourceTypes.map((type) => (
                    <SelectItem key={type} value={type}>
                      {SOURCE_TYPE_LABELS[type]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={editingSource.description || ""}
              onChange={(e) => setEditingSource({ ...editingSource, description: e.target.value })}
              placeholder="Primary analytical database for production metrics"
              rows={2}
              className="bg-slate-900/50 border-slate-800 focus:border-sky-500/50 transition-colors resize-none"
            />
          </div>
        </section>

        {/* Connection Configuration Section */}
        <section className="space-y-4 p-4 rounded-xl border border-slate-800 bg-slate-900/40 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-500"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
          </div>

          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-1 bg-sky-500 rounded-full" />
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Connection Settings</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="host">Host</Label>
              <Input
                id="host"
                value={editingSource.connection?.host || ""}
                onChange={(e) => setEditingSource({
                  ...editingSource,
                  connection: {
                    ...editingSource.connection,
                    host: e.target.value
                  }
                })}
                placeholder="db.example.com"
                className="bg-slate-950/50 border-slate-800/80 focus:border-sky-500/50 transition-colors"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                type="number"
                value={editingSource.connection?.port || ""}
                onChange={(e) => setEditingSource({
                  ...editingSource,
                  connection: {
                    ...editingSource.connection,
                    port: parseInt(e.target.value) || 5432
                  }
                })}
                className="bg-slate-950/50 border-slate-800/80 focus:border-sky-500/50 transition-colors"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={editingSource.connection?.username || ""}
                onChange={(e) => setEditingSource({
                  ...editingSource,
                  connection: {
                    ...editingSource.connection,
                    username: e.target.value
                  }
                })}
                placeholder="admin"
                className="bg-slate-950/50 border-slate-800/80 focus:border-sky-500/50 transition-colors"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="database">Database Name</Label>
              <Input
                id="database"
                value={editingSource.connection?.database || ""}
                onChange={(e) => setEditingSource({
                  ...editingSource,
                  connection: {
                    ...editingSource.connection,
                    database: e.target.value
                  }
                })}
                placeholder="production_db"
                className="bg-slate-950/50 border-slate-800/80 focus:border-sky-500/50 transition-colors"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="timeout">Timeout (seconds)</Label>
              <Input
                id="timeout"
                type="number"
                value={editingSource.connection?.timeout || 30}
                onChange={(e) => setEditingSource({
                  ...editingSource,
                  connection: {
                    ...editingSource.connection,
                    timeout: parseInt(e.target.value) || 30
                  }
                })}
                className="bg-slate-950/50 border-slate-800/80 focus:border-sky-500/50 transition-colors"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="scope">Environment / Scope</Label>
              <Input
                id="scope"
                value={editingSource.scope || ""}
                onChange={(e) => setEditingSource({ ...editingSource, scope: e.target.value })}
                placeholder="e.g., production, staging"
                className="bg-slate-950/50 border-slate-800/80 focus:border-sky-500/50 transition-colors"
              />
            </div>
          </div>
        </section>

        {/* Footer Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800/50">
          <Button
            variant="ghost"
            className="hover:bg-slate-800"
            onClick={() => {
              setIsCreateDialogOpen(false);
              setIsEditDialogOpen(false);
              setEditingSource(null);
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSaveSource}
            className="bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-all shadow-lg shadow-sky-900/20"
            disabled={
              !editingSource.name ||
              !editingSource.source_type ||
              !editingSource.connection?.host ||
              !editingSource.connection?.username ||
              createMutation.isPending ||
              updateMutation.isPending
            }
          >
            {createMutation.isPending || updateMutation.isPending ? "Saving..." : isCreateDialogOpen ? "Create Source" : "Update Source"}
          </Button>
        </div>
      </div>
    );
  };

  if (!enableAssetRegistry) {
    return (
      <div className="min-h-screen bg-[#05070f] px-10 py-10 text-slate-200">
        <h1 className="text-2xl font-semibold">Sources</h1>
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
        <h1 className="text-2xl font-semibold text-white">Sources</h1>
        <div className="flex items-center gap-4">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
            Admin only
          </div>
          <Button onClick={handleCreateSource}>
            Create Source
          </Button>
        </div>
      </div>
      <p className="mb-6 text-sm text-slate-400">
        Manage database and data source connections.
      </p>

      <div className="mb-4">
        <Input
          placeholder="Search sources..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-sm"
        />
      </div>

      <BuilderShell
        leftPane={
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
              Sources ({filteredSources.length})
            </div>
            <div className="custom-scrollbar max-h-[calc(100vh-300px)] space-y-2 overflow-auto pr-1">
              {sourcesQuery.isError && (
                <div className="text-xs text-rose-300">
                  {formatError(sourcesQuery.error)}
                </div>
              )}
              {filteredSources.map((source) => (
                <div
                  key={source.asset_id}
                  className={`rounded-xl border px-3 py-2 cursor-pointer ${activeSource?.asset_id === source.asset_id
                    ? "border-sky-500 bg-sky-500/10"
                    : "border-slate-800 hover:border-slate-600"
                    }`}
                  onClick={() => setSelectedSource(source)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium text-sm">{source.name}</div>
                    <Badge variant="secondary" className="text-xs">
                      {SOURCE_TYPE_LABELS[source.source_type as SourceType]}
                    </Badge>
                  </div>
                  <div className="text-xs text-slate-400 mb-1">
                    {source.connection?.host}:{source.connection?.port}
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={source.status === "active" ? "default" : "secondary"}
                      className="text-xs"
                    >
                      {formatStatus(source.status)}
                    </Badge>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditSource(source);
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTestConnection(source);
                        }}
                      >
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-xs text-rose-400 hover:text-rose-300"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSource(source);
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              {filteredSources.length === 0 && (
                <div className="text-center py-8 text-sm text-slate-400">
                  No sources found
                </div>
              )}
            </div>
          </div>
        }
        centerTop={
          activeSource ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{activeSource.name}</h2>
                <Badge variant={activeSource.status === "active" ? "default" : "secondary"}>
                  {formatStatus(activeSource.status)}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Connection Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <div>Type: {SOURCE_TYPE_LABELS[activeSource.source_type as SourceType]}</div>
                    <div>Host: {activeSource.connection?.host}</div>
                    <div>Port: {activeSource.connection?.port}</div>
                    <div>Database: {activeSource.connection?.database}</div>
                    <div>Username: {activeSource.connection?.username}</div>
                    <div>Timeout: {activeSource.connection?.timeout}s</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Metadata</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <div>ID: {activeSource.asset_id}</div>
                    <div>Version: {activeSource.version}</div>
                    <div>Scope: {activeSource.scope || "None"}</div>
                    <div>Created: {new Date(activeSource.created_at).toLocaleDateString()}</div>
                    {activeSource.published_at && (
                      <div>Published: {new Date(activeSource.published_at).toLocaleDateString()}</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {activeSource.description && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Description</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-300">
                      {activeSource.description}
                    </p>
                  </CardContent>
                </Card>
              )}

              {activeSource.tags && Object.keys(activeSource.tags).length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Tags</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(activeSource.tags).map(([key, value]) => (
                        <Badge key={key} variant="outline" className="text-xs">
                          {key}: {String(value)}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-slate-400">
              Select a source to view details
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
                onClick={handleCreateSource}
              >
                Create New Source
              </Button>
              {activeSource && (
                <>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => handleEditSource(activeSource)}
                  >
                    Edit Source
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => handleTestConnection(activeSource)}
                  >
                    Test Connection
                  </Button>
                </>
              )}
            </div>

            <div className="text-xs uppercase tracking-[0.25em] text-slate-400 mt-6">
              Supported Types
            </div>
            <div className="space-y-1">
              {Object.entries(SOURCE_TYPE_LABELS).map(([type, label]) => (
                <div key={type} className="text-xs text-slate-300">
                  • {label}
                </div>
              ))}
            </div>
          </div>
        }
      />

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateDialogOpen || isEditDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setIsCreateDialogOpen(false);
          setIsEditDialogOpen(false);
          setEditingSource(null);
        }
      }}>
        <DialogContent className="max-w-3xl bg-slate-950 border-slate-800 text-slate-100 shadow-2xl">
          <DialogHeader className="mb-4">
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2 bg-sky-500/10 rounded-lg">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-400"><path d="M21 15V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8"></path><line x1="16" y1="5" x2="16" y2="19"></line><path d="M2 10h18"></path><circle cx="18.5" cy="19.5" r="2.5"></circle></svg>
              </div>
              <div>
                <DialogTitle className="text-xl font-bold tracking-tight">
                  {isCreateDialogOpen ? "Create New Source" : "Edit Source"}
                </DialogTitle>
                <DialogDescription className="text-slate-400">
                  {isCreateDialogOpen ? "Configure a new data source connection for your workspace" : "Update existing connection settings and metadata"}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          {renderConnectionForm()}
        </DialogContent>
      </Dialog>

      {/* Test Connection Dialog */}
      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Test Connection</DialogTitle>
            <DialogDescription>
              Testing connection to {activeSource?.name}
            </DialogDescription>
          </DialogHeader>
          {testResults && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {testResults.success ? (
                  <>
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-sm text-green-400">Connection successful</span>
                  </>
                ) : (
                  <>
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span className="text-sm text-red-400">Connection failed</span>
                  </>
                )}
              </div>

              {testResults.success && (
                <div className="space-y-2">
                  {testResults.execution_time_ms && (
                    <div className="text-sm text-slate-300">
                      Execution time: {testResults.execution_time_ms}ms
                    </div>
                  )}
                  {testResults.test_result && (
                    <div className="text-sm text-slate-300">
                      Result: {JSON.stringify(testResults.test_result, null, 2)}
                    </div>
                  )}
                </div>
              )}

              {testResults.error_details && (
                <div className="text-sm text-red-300">
                  Error: {testResults.error_details}
                </div>
              )}

              <div className="text-xs text-slate-400">
                {testResults.message}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function SourcesPage() {
  return (
    <Suspense fallback={<div className="p-4 text-slate-400">Loading...</div>}>
      <SourcesContent />
    </Suspense>
  );
}
