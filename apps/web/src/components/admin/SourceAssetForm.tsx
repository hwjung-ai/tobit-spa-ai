"use client";

import type React from "react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import Toast from "./Toast";
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

interface SourceAssetFormProps {
  asset: SourceAssetResponse;
  onSave: () => void;
}

const normalizeSourceType = (value: unknown): SourceType => {
  const raw = String(value || "").trim().toLowerCase();
  if (raw === "postgres") return "postgresql";
  if (raw in SOURCE_TYPE_LABELS) return raw as SourceType;
  return "postgresql";
};

const normalizeEditingSource = (source: Partial<SourceAssetResponse>): Partial<SourceAssetResponse> => ({
  ...source,
  source_type: normalizeSourceType(source.source_type),
});

const fieldClassName =
  "border-variant bg-surface-base text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/40 focus-visible:border-sky-500/50 transition-colors";

export default function SourceAssetForm({ asset, onSave }: SourceAssetFormProps) {
  const [editingSource, setEditingSource] = useState<Partial<SourceAssetResponse> | null>(
    normalizeEditingSource(asset),
  );
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" | "info" } | null>(
    null,
  );

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
      setToast({ message: "Source updated successfully.", type: "success" });
      onSave();
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : "Failed to update source.";
      setToast({ message, type: "error" });
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
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : "Connection test failed.";
      setToast({ message, type: "error" });
    },
  });

  const handleEditSource = () => {
    setEditingSource(normalizeEditingSource(asset));
    setIsEditDialogOpen(true);
  };

  const handleSaveSource = () => {
    if (editingSource && asset.asset_id) {
      const normalizedSource = normalizeEditingSource(editingSource);
      updateMutation.mutate({
        id: asset.asset_id,
        source: normalizedSource,
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
    const isSqlLikeSource =
      currentSourceType === "postgresql" ||
      currentSourceType === "mysql" ||
      currentSourceType === "bigquery" ||
      currentSourceType === "snowflake";
    const isCredentialSource = isSqlLikeSource || currentSourceType === "neo4j";

    return (
      <div className="space-y-6 max-h-[70vh] overflow-y-auto px-1 py-1 custom-scrollbar">
        <section className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-1 bg-sky-500 rounded-full" />
            <h3 className="text-sm font-semibold  uppercase tracking-wider">Basic Information</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={editingSource.name || ""}
                onChange={(e) => setEditingSource({ ...editingSource, name: e.target.value })}
                placeholder="Database Production"
                className={fieldClassName}
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
                <SelectTrigger className={fieldClassName}>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent className="border-variant bg-surface-base text-foreground">
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
              className={`${fieldClassName} resize-none`}
            />
          </div>
        </section>

        <section className="space-y-4 p-4 rounded-xl border border-variant bg-surface-elevated/40 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-500"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
          </div>

          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 w-1 bg-sky-500 rounded-full" />
            <h3 className="text-sm font-semibold  uppercase tracking-wider">Connection Settings</h3>
          </div>

          {/* Database Connection Fields (PostgreSQL, MySQL, BigQuery, Snowflake) */}
          {isSqlLikeSource && (
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
                    className={fieldClassName}
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
                    className={fieldClassName}
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
                    className={fieldClassName}
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
                    className={fieldClassName}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={editingSource.connection?.password || ""}
                    onChange={(e) => setEditingSource({
                      ...editingSource,
                      connection: {
                        ...editingSource.connection,
                        password: e.target.value
                      }
                    })}
                    placeholder="DB password (dev) or leave empty"
                    className={fieldClassName}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="secret_key_ref">Secret Key Ref</Label>
                  <Input
                    id="secret_key_ref"
                    value={editingSource.connection?.secret_key_ref || ""}
                    onChange={(e) => setEditingSource({
                      ...editingSource,
                      connection: {
                        ...editingSource.connection,
                        secret_key_ref: e.target.value
                      }
                    })}
                    placeholder="env:PG_PASSWORD"
                    className={fieldClassName}
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
                    className={fieldClassName}
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
                    className={fieldClassName}
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
                  className={fieldClassName}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={editingSource.connection?.password || ""}
                    onChange={(e) => setEditingSource({
                      ...editingSource,
                      connection: {
                        ...editingSource.connection,
                        password: e.target.value
                      }
                    })}
                    placeholder="Neo4j password (dev) or leave empty"
                    className={fieldClassName}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="secret_key_ref">Secret Key Ref</Label>
                  <Input
                    id="secret_key_ref"
                    value={editingSource.connection?.secret_key_ref || ""}
                    onChange={(e) => setEditingSource({
                      ...editingSource,
                      connection: {
                        ...editingSource.connection,
                        secret_key_ref: e.target.value
                      }
                    })}
                    placeholder="env:NEO4J_PASSWORD"
                    className={fieldClassName}
                  />
                </div>
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
                  className={fieldClassName}
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
                    className={fieldClassName}
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
                    className={fieldClassName}
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
                className={fieldClassName}
              />
            </div>
          </div>

          {isCredentialSource && (
            <p className="text-xs text-muted-foreground">
              Prefer <code>secret_key_ref</code> (for example <code>env:PG_PASSWORD</code>) in real mode.
            </p>
          )}
        </section>

        <div className="flex justify-end gap-3 pt-4 border-t border-variant">
          <Button
            variant="ghost"
            className="text-muted-foreground hover:text-foreground hover:bg-surface-elevated"
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
        <Card className="border-variant bg-surface-base">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground uppercase tracking-wider">Connection Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-foreground">
            <div>Type: {SOURCE_TYPE_LABELS[normalizeSourceType(asset.source_type)]}</div>
            <div>Host: {asset.connection?.host}</div>
            <div>Port: {asset.connection?.port}</div>
            <div>Database: {asset.connection?.database}</div>
            <div>Username: {asset.connection?.username}</div>
            <div>Secret Ref: {asset.connection?.secret_key_ref || "Not set"}</div>
            <div>Timeout: {asset.connection?.timeout}s</div>
          </CardContent>
        </Card>

        <Card className="border-variant bg-surface-base">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground uppercase tracking-wider">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-foreground">
            <div>ID: {asset.asset_id}</div>
            <div>Version: {asset.version}</div>
            <div>Created: {new Date(asset.created_at || "").toLocaleDateString()}</div>
            {asset.published_at && (
              <div>Published: {new Date(asset.published_at).toLocaleDateString()}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {asset.description && (
        <Card className="border-variant bg-surface-base">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground uppercase tracking-wider">Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground">
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
          className="border border-variant bg-surface-base text-foreground hover:bg-surface-elevated"
        >
          Edit Connection
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleTestConnection}
          disabled={testMutation.isPending}
          className="border border-variant bg-surface-base text-foreground hover:bg-surface-elevated"
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
        <DialogContent className="max-w-3xl border border-variant bg-surface-base text-foreground shadow-2xl">
          <DialogHeader className="mb-4">
            <div className="flex items-center gap-3 mb-1">
              <div className="p-2 bg-sky-500/10 rounded-lg">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sky-400"><path d="M21 15V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8"></path><line x1="16" y1="5" x2="16" y2="19"></line><path d="M2 10h18"></path><circle cx="18.5" cy="19.5" r="2.5"></circle></svg>
              </div>
              <div>
                <DialogTitle className="text-xl font-bold tracking-tight">
                  Edit Source
                </DialogTitle>
                <DialogDescription className="text-muted-foreground">
                  Update connection settings and metadata
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          {renderConnectionForm()}
        </DialogContent>
      </Dialog>

      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent className="max-w-lg border border-variant bg-surface-base text-foreground shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold">Test Connection</DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Testing connection to {asset.name}
            </DialogDescription>
          </DialogHeader>
          {testResults && (
            <div className="space-y-4 rounded-xl border border-variant bg-surface-elevated/40 p-4">
              <div className="flex items-center gap-2 text-sm font-medium">
                {testResults.success ? (
                  <>
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span className="text-emerald-500">Connection successful</span>
                  </>
                ) : (
                  <>
                    <div className="w-2 h-2 rounded-full bg-rose-500" />
                    <span className="text-rose-500">Connection failed</span>
                  </>
                )}
              </div>

              {testResults.success && (
                <div className="space-y-2">
                  {testResults.execution_time_ms && (
                    <div className="text-sm text-foreground">
                      Execution time: {testResults.execution_time_ms}ms
                    </div>
                  )}
                  {testResults.test_result && (
                    <pre className="max-h-56 overflow-auto rounded-lg border border-variant bg-surface-base p-3 text-xs text-foreground custom-scrollbar">
                      {JSON.stringify(testResults.test_result, null, 2)}
                    </pre>
                  )}
                </div>
              )}

              {testResults.error_details && (
                <div className="text-sm text-rose-500">
                  Error: {testResults.error_details}
                </div>
              )}

              <div className="text-xs text-muted-foreground">
                {testResults.message}
              </div>
            </div>
          )}
          <div className="flex justify-end pt-2">
            <Button
              type="button"
              variant="outline"
              className="border border-variant bg-surface-base text-foreground hover:bg-surface-elevated"
              onClick={() => setIsTestDialogOpen(false)}
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

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
