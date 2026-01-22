"use client";

import type React from "react";
import { useState } from "react";
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
// Note: These types will need to be imported from the API after generating TypeScript types
// For now, we'll define them inline
interface SourceAssetResponse {
  asset_id: string;
  asset_type: string;
  name: string;
  description?: string;
  version: number;
  status: string;
  source_type: string;
  connection: {
    host: string;
    port: number;
    username: string;
    database?: string;
    timeout: number;
    ssl_mode?: string;
    connection_params?: Record<string, unknown>;
  };
  scope?: string;
  tags?: Record<string, unknown>;
  created_by?: string;
  published_by?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
}

interface ConnectionTestResult {
  success: boolean;
  message: string;
  error_details?: string;
  execution_time_ms?: number;
  test_result?: Record<string, unknown>;
}

type SourceType = "postgresql" | "mysql" | "redis" | "mongodb" | "kafka" | "s3" | "bigquery" | "snowflake";

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

export default function SourcesPage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const enableAssetRegistry = process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY === "true";

  const [selectedSource, setSelectedSource] = useState<SourceAssetResponse | null>(null);
  const [editingSource, setEditingSource] = useState<Partial<SourceAsset> | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const sourcesQuery = useQuery({
    queryKey: ["asset-registry", "sources"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/asset_registry/sources`);
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to load sources");
      }
      return body.data as SourceAssetResponse[];
    },
    enabled: enableAssetRegistry,
  });

  const createMutation = useMutation({
    mutationFn: async (source: Partial<SourceAsset>) => {
      const response = await fetch(`${apiBaseUrl}/asset_registry/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(source),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to create source");
      }
      return body.data as SourceAssetResponse;
    },
    onSuccess: () => {
      sourcesQuery.refetch();
      setIsCreateDialogOpen(false);
      setEditingSource(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, source }: { id: string; source: Partial<SourceAsset> }) => {
      const response = await fetch(`${apiBaseUrl}/asset_registry/sources/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(source),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to update source");
      }
      return body.data as SourceAssetResponse;
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
      const response = await fetch(`${apiBaseUrl}/asset_registry/sources/${id}`, {
        method: "DELETE",
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to delete source");
      }
    },
    onSuccess: () => {
      sourcesQuery.refetch();
      setSelectedSource(null);
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`${apiBaseUrl}/asset_registry/sources/${id}/test`, {
        method: "POST",
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to test connection");
      }
      return body.data as ConnectionTestResult;
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
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input
            id="name"
            value={editingSource.name || ""}
            onChange={(e) => setEditingSource({ ...editingSource, name: e.target.value })}
            placeholder="Enter source name"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={editingSource.description || ""}
            onChange={(e) => setEditingSource({ ...editingSource, description: e.target.value })}
            placeholder="Enter source description"
            rows={2}
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
            <SelectTrigger>
              <SelectValue placeholder="Select source type" />
            </SelectTrigger>
            <SelectContent>
              {sourceTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {SOURCE_TYPE_LABELS[type]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
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
              placeholder="localhost"
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
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
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
              placeholder="username"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="database">Database</Label>
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
              placeholder="database"
            />
          </div>
        </div>

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
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="scope">Scope</Label>
          <Input
            id="scope"
            value={editingSource.scope || ""}
            onChange={(e) => setEditingSource({ ...editingSource, scope: e.target.value })}
            placeholder="e.g., production, staging"
          />
        </div>

        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
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
            disabled={
              !editingSource.name ||
              !editingSource.source_type ||
              !editingSource.connection?.host ||
              !editingSource.connection?.username ||
              createMutation.isPending ||
              updateMutation.isPending
            }
          >
            {isCreateDialogOpen ? "Create" : "Save"}
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
                  className={`rounded-xl border px-3 py-2 cursor-pointer ${
                    selectedSource?.asset_id === source.asset_id
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
          selectedSource ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{selectedSource.name}</h2>
                <Badge variant={selectedSource.status === "active" ? "default" : "secondary"}>
                  {formatStatus(selectedSource.status)}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Connection Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <div>Type: {SOURCE_TYPE_LABELS[selectedSource.source_type as SourceType]}</div>
                    <div>Host: {selectedSource.connection?.host}</div>
                    <div>Port: {selectedSource.connection?.port}</div>
                    <div>Database: {selectedSource.connection?.database}</div>
                    <div>Username: {selectedSource.connection?.username}</div>
                    <div>Timeout: {selectedSource.connection?.timeout}s</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Metadata</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <div>ID: {selectedSource.asset_id}</div>
                    <div>Version: {selectedSource.version}</div>
                    <div>Scope: {selectedSource.scope || "None"}</div>
                    <div>Created: {new Date(selectedSource.created_at).toLocaleDateString()}</div>
                    {selectedSource.published_at && (
                      <div>Published: {new Date(selectedSource.published_at).toLocaleDateString()}</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {selectedSource.description && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Description</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-300">
                      {selectedSource.description}
                    </p>
                  </CardContent>
                </Card>
              )}

              {selectedSource.tags && Object.keys(selectedSource.tags).length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Tags</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(selectedSource.tags).map(([key, value]) => (
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
              {selectedSource && (
                <>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => handleEditSource(selectedSource)}
                  >
                    Edit Source
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => handleTestConnection(selectedSource)}
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {isCreateDialogOpen ? "Create New Source" : "Edit Source"}
            </DialogTitle>
            <DialogDescription>
              Configure a new data source connection
            </DialogDescription>
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
              Testing connection to {selectedSource?.name}
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
