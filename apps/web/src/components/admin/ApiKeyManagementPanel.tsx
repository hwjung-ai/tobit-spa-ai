"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Copy, Eye, EyeOff, Trash2, Plus, AlertTriangle, Check } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scope: string[];
  is_active: boolean;
  last_used_at?: string;
  expires_at?: string;
  created_at: string;
}

interface CreateApiKeyPayload {
  name: string;
  scope: string[];
  expires_at?: string;
}

const AVAILABLE_SCOPES = [
  { category: "API Management", scopes: ["api:read", "api:write", "api:delete", "api:execute"] },
  { category: "CI/CD", scopes: ["ci:read", "ci:write", "ci:delete"] },
  { category: "Monitoring", scopes: ["metric:read", "graph:read", "history:read"] },
  { category: "CEP Rules", scopes: ["cep:read", "cep:write"] },
];

export function ApiKeyManagementPanel() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isRevokeDialogOpen, setIsRevokeDialogOpen] = useState(false);
  const [selectedKeyForRevoke, setSelectedKeyForRevoke] = useState<ApiKey | null>(null);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  // Form states
  const [createForm, setCreateForm] = useState<CreateApiKeyPayload>({
    name: "",
    scope: ["api:read"],
  });

  // Fetch API keys
  useEffect(() => {
    fetchApiKeys();
  }, []);

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      // Mock API call - replace with actual API
      const mockKeys: ApiKey[] = [
        {
          id: "key1",
          name: "CI Integration",
          key_prefix: "sk_a1b2",
          scope: ["api:read", "ci:read"],
          is_active: true,
          last_used_at: "2026-01-18T10:30:00Z",
          created_at: "2026-01-10T00:00:00Z",
        },
        {
          id: "key2",
          name: "Monitoring Service",
          key_prefix: "sk_c3d4",
          scope: ["metric:read", "graph:read"],
          is_active: true,
          created_at: "2026-01-12T00:00:00Z",
        },
        {
          id: "key3",
          name: "Old Key",
          key_prefix: "sk_e5f6",
          scope: ["api:read"],
          is_active: false,
          created_at: "2025-12-01T00:00:00Z",
        },
      ];
      setApiKeys(mockKeys);
      setError(null);
    } catch {
      setError("Failed to fetch API keys");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async () => {
    if (!createForm.name.trim()) {
      setError("Please enter a key name");
      return;
    }

    if (createForm.scope.length === 0) {
      setError("Please select at least one scope");
      return;
    }

    try {
      setLoading(true);
      // Mock API call
      const newKey = `sk_${Math.random().toString(36).substr(2, 32)}`;
      setCreatedKey(newKey);

      // Add to list (in real app, this would come from server)
      const apiKey: ApiKey = {
        id: `key${Date.now()}`,
        ...createForm,
        key_prefix: newKey.slice(0, 8),
        is_active: true,
        created_at: new Date().toISOString(),
      };
      setApiKeys([apiKey, ...apiKeys]);

      setSuccess("API key created successfully!");
      setCreateForm({ name: "", scope: ["api:read"] });
      setIsCreateDialogOpen(false);
      setTimeout(() => {
        setSuccess(null);
        setCreatedKey(null);
        setShowKeySecret(false);
      }, 10000);
    } catch {
      setError("Failed to create API key");
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeApiKey = async () => {
    if (!selectedKeyForRevoke) return;

    try {
      setLoading(true);
      // Mock API call
      setApiKeys(apiKeys.map(k =>
        k.id === selectedKeyForRevoke.id ? { ...k, is_active: false } : k
      ));
      setSuccess("API key revoked successfully!");
      setIsRevokeDialogOpen(false);
      setSelectedKeyForRevoke(null);
      setTimeout(() => setSuccess(null), 3000);
    } catch {
      setError("Failed to revoke API key");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(key);
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  const toggleScopeSelection = (scope: string) => {
    setCreateForm({
      ...createForm,
      scope: createForm.scope.includes(scope)
        ? createForm.scope.filter(s => s !== scope)
        : [...createForm.scope, scope],
    });
  };

  const getScopeColor = (scope: string) => {
    if (scope.includes("api")) return "bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300";
    if (scope.includes("ci")) return "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300";
    if (scope.includes("metric") || scope.includes("graph")) return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300";
    if (scope.includes("cep")) return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300";
    return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300";
  };

  const activeKeysCount = apiKeys.filter(k => k.is_active).length;
  const inactiveKeysCount = apiKeys.filter(k => !k.is_active).length;

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <p className="text-sm font-medium">Total Keys</p>
              <p className="text-3xl font-bold">{apiKeys.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <p className="text-sm font-medium">Active Keys</p>
              <p className="text-3xl font-bold text-green-600">{activeKeysCount}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <p className="text-sm font-medium">Revoked Keys</p>
              <p className="text-3xl font-bold text-red-600">{inactiveKeysCount}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>API Key Management</CardTitle>
            <CardDescription>Create and manage API keys for programmatic access</CardDescription>
          </div>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger onClick={() => setIsCreateDialogOpen(true)}>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Create API Key
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create New API Key</DialogTitle>
                <DialogDescription>
                  Create a new API key for programmatic access
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                {/* Key Name */}
                <div>
                  <label className="block text-sm font-medium mb-2">Key Name</label>
                  <Input
                    placeholder="e.g., CI Integration, Monitoring Service"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  />
                </div>

                {/* Scopes Selection */}
                <div>
                  <label className="block text-sm font-medium mb-4">Select Scopes</label>
                  <div className="space-y-4">
                    {AVAILABLE_SCOPES.map((group) => (
                      <div key={group.category}>
                        <h4 className="text-sm font-semibold mb-2">{group.category}</h4>
                        <div className="space-y-2">
                          {group.scopes.map((scope) => (
                            <div key={scope} className="flex items-center space-x-2">
                              <Checkbox
                                id={scope}
                                checked={createForm.scope.includes(scope)}
                                onCheckedChange={() => toggleScopeSelection(scope)}
                              />
                              <label
                                htmlFor={scope}
                                className="text-sm font-medium cursor-pointer"
                              >
                                {scope}
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Expiration */}
                <div>
                  <label className="block text-sm font-medium mb-2">Expires (Optional)</label>
                  <Input
                    type="datetime-local"
                    value={createForm.expires_at || ""}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, expires_at: e.target.value || undefined })
                    }
                  />
                  <p className="text-xs mt-1">
                    Leave empty for key that never expires
                  </p>
                </div>

                {/* Create Button */}
                <Button onClick={handleCreateApiKey} disabled={loading} className="w-full">
                  {loading ? "Creating..." : "Create API Key"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardHeader>

        <CardContent>
          {error && (
            <Alert className="mb-4 bg-rose-50 border-rose-200 text-rose-800">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="mb-4 bg-green-50 border-green-200">
              <AlertDescription className="text-green-800">{success}</AlertDescription>
            </Alert>
          )}

          {/* Created Key Display */}
          {createdKey && (
            <Alert className="mb-4 bg-amber-50 border-amber-200">
              <AlertTriangle className="w-4 h-4" />
              <AlertDescription className="text-amber-800 mt-2">
                <p className="font-semibold mb-2">⚠️ Save Your API Key</p>
                <p className="mb-3">
                  This is the only time you will see this key. Please save it in a secure location.
                </p>
                <div className="bg-white dark:bg-slate-950 p-3 rounded border border-amber-300 dark:border-amber-700 mb-3 flex items-center justify-between">
                  <code className="text-sm font-mono break-all flex-1 text-slate-900 dark:text-slate-100">
                    {showKeySecret ? createdKey : "•".repeat(32)}
                  </code>
                  <div className="flex gap-2 ml-2 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowKeySecret(!showKeySecret)}
                    >
                      {showKeySecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopyKey(createdKey)}
                    >
                      {copiedKeyId === createdKey ? (
                        <Check className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* API Keys List */}
          <div className="space-y-2">
            {apiKeys.length > 0 ? (
              apiKeys.map((key) => (
                <Card key={key.id} className={key.is_active ? "" : "opacity-50"}>
                  <CardContent className="pt-6">
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold">{key.name}</h3>
                            {key.is_active ? (
                              <Badge variant="outline" className="bg-green-50 text-green-800">
                                Active
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-red-50 text-red-800">
                                Revoked
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm mt-1">
                            Key: <code className="px-2 py-1 rounded text-xs">{key.key_prefix}...</code>
                          </p>
                        </div>
                        {key.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedKeyForRevoke(key);
                              setIsRevokeDialogOpen(true);
                            }}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>

                      {/* Scopes */}
                      <div className="flex flex-wrap gap-1">
                        {key.scope.map((scope) => (
                          <Badge key={scope} className={getScopeColor(scope)} variant="secondary">
                            {scope}
                          </Badge>
                        ))}
                      </div>

                      {/* Metadata */}
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          Created: {new Date(key.created_at).toLocaleDateString()}
                        </div>
                        {key.last_used_at && (
                          <div>
                            Last used: {new Date(key.last_used_at).toLocaleDateString()}
                          </div>
                        )}
                        {key.expires_at && (
                          <div className="col-span-2 text-amber-600">
                            Expires: {new Date(key.expires_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <div className="text-center py-8">
                No API keys yet. Create one to get started.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Revoke Confirmation Dialog */}
      <Dialog open={isRevokeDialogOpen} onOpenChange={setIsRevokeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API Key</DialogTitle>
            <DialogDescription>
              Are you sure you want to revoke this API key?
            </DialogDescription>
          </DialogHeader>

          {selectedKeyForRevoke && (
            <div className="bg-red-50 p-4 rounded-lg border border-red-200 mb-4">
              <p className="text-sm text-red-800">
                <strong>Key Name:</strong> {selectedKeyForRevoke.name}
              </p>
              <p className="text-sm text-red-800 mt-2">
                This action cannot be undone. Any services using this key will lose access.
              </p>
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <Button
              variant="outline"
              onClick={() => setIsRevokeDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRevokeApiKey}
              disabled={loading}
            >
              {loading ? "Revoking..." : "Revoke Key"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
