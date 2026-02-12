"use client";

import type React from "react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { fetchApi } from "../../lib/adminUtils";
import type { ConnectionTestResult, SourceAssetResponse, SourceType } from "../../types/asset-registry";

const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  // SQL Databases
  postgresql: "PostgreSQL",
  mysql: "MySQL",
  bigquery: "Google BigQuery",
  snowflake: "Snowflake",
  // NoSQL / Graph
  mongodb: "MongoDB",
  neo4j: "Neo4j",
  redis: "Redis",
  // Message Queue
  kafka: "Kafka",
  // Storage
  s3: "Amazon S3",
  // API
  rest_api: "REST API",
  graphql_api: "GraphQL API",
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

interface SourceAssetFormProps {
  asset: SourceAssetResponse;
  onSave: () => void;
}

export default function SourceAssetForm({ asset, onSave }: SourceAssetFormProps) {
  const [editingSource, setEditingSource] = useState<Partial<SourceAssetResponse> | null>(asset);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult | null>(null);

  const updateMutation = useMutation({
    mutationFn: async ({ id, source }: { id: string; source: Partial<SourceAssetResponse> }) => {
      const response = await fetchApi<SourceAssetResponse>(`/asset-registry/sources/${id}`, {
        method: "PUT",
        body: JSON.stringify(source),
      });
      return response.data;
    },
    onSuccess: () => {
      setIsEditDialogOpen(false);
      setEditingSource(null);
      onSave();
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

  const handleEditSource = () => {
    setEditingSource(asset);
    setIsEditDialogOpen(true);
  };

  const handleSaveSource = () => {
    if (editingSource && asset.asset_id) {
      updateMutation.mutate({
        id: asset.asset_id,
        source: editingSource,
      });
    }
  };

  const handleTestConnection = () => {
    if (asset.asset_id) {
      testMutation.mutate(asset.asset_id);
    }
  };

  const renderConnectionForm = () => {
    if (!editingSource) return null;

    const sourceTypes = Object.keys(SOURCE_TYPE_LABELS) as SourceType[];
    const currentSourceType = editingSource.source_type || "postgresql";

    return (
      <div className="space-y-6 max-h-[70vh] overflow-y-auto px-1 py-1 custom-scrollbar">
        <section className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-1 bg-sky-500 rounded-full" />
            <h3 className="text-sm font-semibold  uppercase tracking-wider" style={{color: "var(--foreground-secondary)"}}>Basic Information</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={editingSource.name || ""}
                onChange={(e) => setEditingSource({ ...editingSource, name: e.target.value })}
                placeholder="Database Production"
                className="  focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
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
                <SelectTrigger className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent className=" " style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
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
              className="  focus:border-sky-500/50 transition-colors resize-none" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
            />
          </div>
        </section>

        <section className="space-y-4 p-4 rounded-xl border   relative overflow-hidden" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
          <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-500"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
          </div>

          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-1 bg-sky-500 rounded-full" />
            <h3 className="text-sm font-semibold  uppercase tracking-wider" style={{color: "var(--foreground-secondary)"}}>Connection Settings</h3>
          </div>

          {/* Database Connection Fields (PostgreSQL, MySQL, BigQuery, Snowflake) */}
          {(currentSourceType === "postgresql" || currentSourceType === "mysql" ||
            currentSourceType === "bigquery" || currentSourceType === "snowflake") && (
            <>
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
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
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
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
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
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
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
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                  />
                </div>
              </div>
            </>
          )}

          {/* Neo4j Connection Fields */}
          {currentSourceType === "neo4j" && (
            <>
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
                    placeholder="neo4j.example.com"
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
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
                        port: parseInt(e.target.value) || 7687
                      }
                    })}
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                  />
                </div>
              </div>

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
                  placeholder="neo4j"
                  className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                />
              </div>
            </>
          )}

          {/* REST API / GraphQL API Connection Fields */}
          {(currentSourceType === "rest_api" || currentSourceType === "graphql_api") && (
            <>
              <div className="space-y-2">
                <Label htmlFor="host">Base URL</Label>
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
                  placeholder="https://api.example.com"
                  className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">API Key / Username</Label>
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
                    placeholder="api_key_id"
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="database">Auth Token (optional)</Label>
                  <Input
                    id="database"
                    type="password"
                    value={editingSource.connection?.database || ""}
                    onChange={(e) => setEditingSource({
                      ...editingSource,
                      connection: {
                        ...editingSource.connection,
                        database: e.target.value
                      }
                    })}
                    placeholder="Bearer token or API secret"
                    className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
                  />
                </div>
              </div>
            </>
          )}

          {/* Common Fields for all source types */}
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
                className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="scope">Environment / Scope</Label>
              <Input
                id="scope"
                value={editingSource.scope || ""}
                onChange={(e) => setEditingSource({ ...editingSource, scope: e.target.value })}
                placeholder="e.g., production, staging"
                className="/50 /80 focus:border-sky-500/50 transition-colors" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end gap-3 pt-4 border-t /50" style={{borderColor: "var(--border)"}}>
          <Button
            variant="ghost"
            className="hover:" style={{backgroundColor: "var(--surface-elevated)"}}
            onClick={() => {
              setIsEditDialogOpen(false);
              setEditingSource(null);
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSaveSource}
            className="bg-sky-600 hover:bg-sky-500 text-white font-semibold transition-all shadow-lg shadow-sky-900/20 dark:bg-sky-700 dark:hover:bg-sky-600"
            disabled={
              !editingSource.name ||
              !editingSource.source_type ||
              !editingSource.connection?.host ||
              !editingSource.connection?.username ||
              updateMutation.isPending
            }
          >
            {updateMutation.isPending ? "Saving..." : "Update Source"}
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Card className="/50  " style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-base)"}}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs " style={{color: "var(--foreground-secondary)"}}>Connection Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm " style={{color: "var(--foreground-secondary)"}}>
            <div>Type: {SOURCE_TYPE_LABELS[asset.source_type as SourceType]}</div>
            <div>Host: {asset.connection?.host}</div>
            <div>Port: {asset.connection?.port}</div>
            <div>Database: {asset.connection?.database}</div>
            <div>Username: {asset.connection?.username}</div>
            <div>Timeout: {asset.connection?.timeout}s</div>
          </CardContent>
        </Card>

        <Card className="/50  " style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-base)"}}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs " style={{color: "var(--foreground-secondary)"}}>Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm " style={{color: "var(--foreground-secondary)"}}>
            <div>ID: {asset.asset_id}</div>
            <div>Version: {asset.version}</div>
            <div>Scope: {asset.scope || "None"}</div>
            <div>Created: {new Date(asset.created_at || "").toLocaleDateString()}</div>
            {asset.published_at && (
              <div>Published: {new Date(asset.published_at).toLocaleDateString()}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {asset.description && (
        <Card className="/50  " style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-base)"}}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs " style={{color: "var(--foreground-secondary)"}}>Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm " style={{color: "var(--foreground-secondary)"}}>
              {asset.description}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleEditSource}
          className=" /50  hover: hover:" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-elevated)"}}
        >
          Edit Connection
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleTestConnection}
          disabled={testMutation.isPending}
          className=" /50  hover: hover:" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)", backgroundColor: "var(--surface-elevated)"}}
        >
          {testMutation.isPending ? "Testing..." : "Test Connection"}
        </Button>
      </div>

      <Dialog open={isEditDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setIsEditDialogOpen(false);
          setEditingSource(null);
        }
      }}>
        <DialogContent className="max-w-3xl    shadow-2xl" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-base)"}}>
          <DialogHeader className="mb-4">
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2 bg-sky-500/10 rounded-lg">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-400"><path d="M21 15V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8"></path><line x1="16" y1="5" x2="16" y2="19"></line><path d="M2 10h18"></path><circle cx="18.5" cy="19.5" r="2.5"></circle></svg>
              </div>
              <div>
                <DialogTitle className="text-xl font-bold tracking-tight">
                  Edit Source
                </DialogTitle>
                <DialogDescription className="" style={{color: "var(--muted-foreground)"}}>
                  Update connection settings and metadata
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          {renderConnectionForm()}
        </DialogContent>
      </Dialog>

      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Test Connection</DialogTitle>
            <DialogDescription>
              Testing connection to {asset.name}
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
                    <div className="text-sm " style={{color: "var(--foreground-secondary)"}}>
                      Execution time: {testResults.execution_time_ms}ms
                    </div>
                  )}
                  {testResults.test_result && (
                    <div className="text-sm " style={{color: "var(--foreground-secondary)"}}>
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

              <div className="text-xs " style={{color: "var(--muted-foreground)"}}>
                {testResults.message}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
