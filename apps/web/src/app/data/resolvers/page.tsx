"use client";

import type React from "react";
import { useEffect, useState } from "react";
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
import { useSearchParams } from "next/navigation";

// Resolver types based on backend API
interface ResolverAssetResponse {
  asset_id: string;
  asset_type: string;
  name: string;
  description?: string;
  version: number;
  status: string;
  config: {
    name: string;
    description?: string;
    rules: ResolverRule[];
    default_namespace?: string;
    tags?: Record<string, unknown>;
    version: number;
  };
  scope?: string;
  tags?: Record<string, unknown>;
  created_by?: string;
  published_by?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
}

interface ResolverRule {
  rule_type: "alias_mapping" | "pattern_rule" | "transformation";
  name: string;
  description?: string;
  is_active: boolean;
  priority: number;
  extra_metadata?: Record<string, unknown>;
  rule_data: AliasMapping | PatternRule | TransformationRule;
}

interface AliasMapping {
  source_entity: string;
  target_entity: string;
  namespace?: string;
  description?: string;
  is_active: boolean;
  priority: number;
}

interface PatternRule {
  pattern: string;
  replacement: string;
  description?: string;
  is_active: boolean;
  priority: number;
}

interface TransformationRule {
  transformation_type: string;
  field_name: string;
  description?: string;
  is_active: boolean;
  priority: number;
  parameters?: Record<string, unknown>;
}

interface ResolverSimulationRequest {
  config: {
    name: string;
    description?: string;
    rules: ResolverRule[];
    default_namespace?: string;
    tags?: Record<string, unknown>;
    version: number;
  };
  test_entities: string[];
  simulation_options?: Record<string, unknown>;
}

interface ResolverSimulationResult {
  original_entity: string;
  resolved_entity: string;
  transformations_applied: string[];
  confidence_score: number;
  matched_rules: string[];
  extra_metadata?: Record<string, unknown>;
}

interface ResolverAsset {
  asset_id?: string;
  asset_type: string;
  name: string;
  description?: string;
  version?: number;
  status?: string;
  config?: {
    name: string;
    description?: string;
    rules: ResolverRule[];
    default_namespace?: string;
    tags?: Record<string, unknown>;
    version: number;
  };
  scope?: string;
  tags?: Record<string, unknown>;
  created_by?: string;
  published_by?: string;
  published_at?: string;
  created_at?: string;
  updated_at?: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  active: "Active",
  inactive: "Inactive",
  deprecated: "Deprecated",
};

const RULE_TYPE_LABELS: Record<string, string> = {
  alias_mapping: "Alias Mapping",
  pattern_rule: "Pattern Rule",
  transformation: "Transformation",
};

const AMBIGUITY_POLICY_LABELS: Record<string, string> = {
  ask_user: "Ask User",
  use_first: "Use First",
  use_most_recent: "Use Most Recent",
  fail: "Fail",
};

const formatStatus = (status: string) => {
  return STATUS_LABELS[status] || status;
};

export default function ResolversPage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const enableAssetRegistry = process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY === "true";
  const searchParams = useSearchParams();
  const selectedAssetId = searchParams.get("asset_id");

  const [selectedResolver, setSelectedResolver] = useState<ResolverAssetResponse | null>(null);
  const [editingResolver, setEditingResolver] = useState<Partial<ResolverAsset> | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isSimulateDialogOpen, setIsSimulateDialogOpen] = useState(false);
  const [simulationResults, setSimulationResults] = useState<ResolverSimulationResult[]>([]);
  const [testEntityInput, setTestEntityInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const resolversQuery = useQuery({
    queryKey: ["asset-registry", "resolvers"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/asset-registry/resolvers`);
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to load resolvers");
      }
      return (body.data?.assets ?? []) as ResolverAssetResponse[];
    },
    enabled: enableAssetRegistry,
  });

  const createMutation = useMutation({
    mutationFn: async (resolver: Partial<ResolverAsset>) => {
      const response = await fetch(`${apiBaseUrl}/asset-registry/resolvers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resolver),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to create resolver");
      }
      return body.data as ResolverAssetResponse;
    },
    onSuccess: () => {
      resolversQuery.refetch();
      setIsCreateDialogOpen(false);
      setEditingResolver(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, resolver }: { id: string; resolver: Partial<ResolverAsset> }) => {
      const response = await fetch(`${apiBaseUrl}/asset-registry/resolvers/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(resolver),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to update resolver");
      }
      return body.data as ResolverAssetResponse;
    },
    onSuccess: () => {
      resolversQuery.refetch();
      setIsEditDialogOpen(false);
      setEditingResolver(null);
      setSelectedResolver(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`${apiBaseUrl}/asset-registry/resolvers/${id}`, {
        method: "DELETE",
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to delete resolver");
      }
    },
    onSuccess: () => {
      resolversQuery.refetch();
      setSelectedResolver(null);
    },
  });

  const simulateMutation = useMutation({
    mutationFn: async (request: ResolverSimulationRequest) => {
      const response = await fetch(`${apiBaseUrl}/asset-registry/resolvers/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to simulate resolver");
      }
      return body.data as ResolverSimulationResult[];
    },
    onSuccess: (data) => {
      setSimulationResults(data);
      setIsSimulateDialogOpen(true);
    },
  });

  const filteredResolvers = (resolversQuery.data ?? []).filter(resolver =>
    resolver.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    resolver.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useEffect(() => {
    if (!selectedAssetId || !resolversQuery.data?.length) {
      return;
    }
    const match = resolversQuery.data.find((resolver) => resolver.asset_id === selectedAssetId);
    if (match) {
      setSelectedResolver(match);
    }
  }, [selectedAssetId, resolversQuery.data]);

  const handleCreateResolver = () => {
    setEditingResolver({
      asset_type: "resolver",
      name: "",
      description: "",
      config: {
        name: "",
        description: "",
        rules: [],
        default_namespace: "",
        tags: {},
        version: 1,
      },
      scope: "",
      tags: {},
    });
    setIsCreateDialogOpen(true);
  };

  const handleEditResolver = (resolver: ResolverAssetResponse) => {
    setEditingResolver(resolver);
    setIsEditDialogOpen(true);
  };

  const handleSaveResolver = () => {
    if (editingResolver) {
      if (isCreateDialogOpen) {
        createMutation.mutate(editingResolver);
      } else if (editingResolver.asset_id) {
        updateMutation.mutate({
          id: editingResolver.asset_id,
          resolver: editingResolver,
        });
      }
    }
  };

  const handleDeleteResolver = (resolver: ResolverAssetResponse) => {
    if (confirm(`Are you sure you want to delete "${resolver.name}"?`)) {
      deleteMutation.mutate(resolver.asset_id);
    }
  };

  const handleSimulateResolver = (resolver: ResolverAssetResponse) => {
    setSelectedResolver(resolver);
    const entities = testEntityInput.split('\n').filter(e => e.trim());
    const request: ResolverSimulationRequest = {
      config: resolver.config,
      test_entities: entities,
      simulation_options: {},
    };
    simulateMutation.mutate(request);
  };

  const addRule = (ruleType: "alias_mapping" | "pattern_rule" | "transformation") => {
    if (!editingResolver?.config) return;

    const newRule: ResolverRule = {
      rule_type: ruleType,
      name: `New ${ruleType}`,
      description: "",
      is_active: true,
      priority: 0,
      extra_metadata: {},
      rule_data: ruleType === "alias_mapping" ? {
        source_entity: "",
        target_entity: "",
        namespace: "",
        description: "",
        is_active: true,
        priority: 0,
      } : ruleType === "pattern_rule" ? {
        pattern: "",
        replacement: "",
        description: "",
        is_active: true,
        priority: 0,
      } : {
        transformation_type: "",
        field_name: "",
        description: "",
        is_active: true,
        priority: 0,
        parameters: {},
      },
    };

    setEditingResolver({
      ...editingResolver,
      config: {
        ...editingResolver.config,
        rules: [...editingResolver.config.rules, newRule],
      },
    });
  };

  const updateRule = (index: number, updatedRule: ResolverRule) => {
    if (!editingResolver?.config) return;

    const newRules = [...editingResolver.config.rules];
    newRules[index] = updatedRule;

    setEditingResolver({
      ...editingResolver,
      config: {
        ...editingResolver.config,
        rules: newRules,
      },
    });
  };

  const removeRule = (index: number) => {
    if (!editingResolver?.config) return;

    const newRules = editingResolver.config.rules.filter((_, i) => i !== index);
    setEditingResolver({
      ...editingResolver,
      config: {
        ...editingResolver.config,
        rules: newRules,
      },
    });
  };

  const renderRuleForm = (rule: ResolverRule, index: number) => {
    return (
      <Card key={index} className="p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium">Rule #{index + 1}</h4>
            <Badge className="text-xs">
              {RULE_TYPE_LABELS[rule.rule_type]}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input
                value={rule.name}
                onChange={(e) => updateRule(index, { ...rule, name: e.target.value })}
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label>Priority</Label>
              <Input
                type="number"
                value={rule.priority}
                onChange={(e) => updateRule(index, { ...rule, priority: parseInt(e.target.value) || 0 })}
                className="h-8 text-sm"
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label>Description</Label>
            <Textarea
              value={rule.description || ""}
              onChange={(e) => updateRule(index, { ...rule, description: e.target.value })}
              rows={2}
              className="text-sm"
            />
          </div>

          {rule.rule_type === "alias_mapping" && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Source Entity</Label>
                <Input
                  value={(rule.rule_data as AliasMapping).source_entity}
                  onChange={(e) => updateRule(index, {
                    ...rule,
                    rule_data: { ...(rule.rule_data as AliasMapping), source_entity: e.target.value }
                  })}
                  placeholder="e.g., GT-01"
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label>Target Entity</Label>
                <Input
                  value={(rule.rule_data as AliasMapping).target_entity}
                  onChange={(e) => updateRule(index, {
                    ...rule,
                    rule_data: { ...(rule.rule_data as AliasMapping), target_entity: e.target.value }
                  })}
                  placeholder="e.g., Gas Turbine 01"
                  className="h-8 text-sm"
                />
              </div>
            </div>
          )}

          {rule.rule_type === "pattern_rule" && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Pattern (Regex)</Label>
                <Input
                  value={(rule.rule_data as PatternRule).pattern}
                  onChange={(e) => updateRule(index, {
                    ...rule,
                    rule_data: { ...(rule.rule_data as PatternRule), pattern: e.target.value }
                  })}
                  placeholder="e.g., GT-(\\d+)"
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label>Replacement</Label>
                <Input
                  value={(rule.rule_data as PatternRule).replacement}
                  onChange={(e) => updateRule(index, {
                    ...rule,
                    rule_data: { ...(rule.rule_data as PatternRule), replacement: e.target.value }
                  })}
                  placeholder="e.g., Gas Turbine $1"
                  className="h-8 text-sm"
                />
              </div>
            </div>
          )}

          {rule.rule_type === "transformation" && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Transformation Type</Label>
                <Select
                  value={(rule.rule_data as TransformationRule).transformation_type}
                  onValueChange={(value) => updateRule(index, {
                    ...rule,
                    rule_data: { ...(rule.rule_data as TransformationRule), transformation_type: value }
                  })}
                >
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="uppercase">Uppercase</SelectItem>
                    <SelectItem value="lowercase">Lowercase</SelectItem>
                    <SelectItem value="trim">Trim</SelectItem>
                    <SelectItem value="normalize">Normalize</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Field Name</Label>
                <Input
                  value={(rule.rule_data as TransformationRule).field_name}
                  onChange={(e) => updateRule(index, {
                    ...rule,
                    rule_data: { ...(rule.rule_data as TransformationRule), field_name: e.target.value }
                  })}
                  placeholder="field_name"
                  className="h-8 text-sm"
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`active-${index}`}
                checked={rule.is_active}
                onChange={(e) => updateRule(index, { ...rule, is_active: e.target.checked })}
                className="h-4 w-4"
              />
              <Label htmlFor={`active-${index}`} className="text-sm">Active</Label>
            </div>
            <button
              className="ml-auto h-7 rounded text-xs text-rose-400 hover:text-rose-300"
              onClick={() => removeRule(index)}
            >
              Remove Rule
            </button>
          </div>
        </div>
      </Card>
    );
  };

  if (!enableAssetRegistry) {
    return (
      <div className="min-h-screen bg-[#05070f] px-10 py-10 text-slate-200">
        <h1 className="text-2xl font-semibold">Resolvers</h1>
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
        <h1 className="text-2xl font-semibold text-white">Resolvers</h1>
        <div className="flex items-center gap-4">
          <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
            Admin only
          </div>
          <Button onClick={handleCreateResolver}>
            Create Resolver
          </Button>
        </div>
      </div>
      <p className="mb-6 text-sm text-slate-400">
        Configure entity resolution with alias mappings, pattern rules, and transformations.
      </p>

      <div className="mb-4">
        <Input
          placeholder="Search resolvers..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-sm"
        />
      </div>

      <BuilderShell
        leftPane={
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
              Resolvers ({filteredResolvers.length})
            </div>
            <div className="custom-scrollbar max-h-[calc(100vh-300px)] space-y-2 overflow-auto pr-1">
              {resolversQuery.isError && (
                <div className="text-xs text-rose-300">
                  {formatError(resolversQuery.error)}
                </div>
              )}
              {filteredResolvers.map((resolver) => (
                <div
                  key={resolver.asset_id}
                  className={`rounded-xl border px-3 py-2 cursor-pointer ${selectedResolver?.asset_id === resolver.asset_id
                    ? "border-sky-500 bg-sky-500/10"
                    : "border-slate-800 hover:border-slate-600"
                    }`}
                  onClick={() => setSelectedResolver(resolver)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium text-sm">{resolver.name}</div>
                    <Badge variant="secondary" className="text-xs">
                      v{resolver.version}
                    </Badge>
                  </div>
                  <div className="text-xs text-slate-400 mb-1">
                    {resolver.config.rules.length} rules
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={resolver.status === "active" ? "default" : "secondary"}
                      className="text-xs"
                    >
                      {formatStatus(resolver.status)}
                    </Badge>
                    <div className="flex gap-1">
                      <button
                        className="h-6 w-6 rounded p-0 text-xs hover:bg-slate-800"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditResolver(resolver);
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="h-6 w-6 rounded p-0 text-xs hover:bg-slate-800"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedResolver(resolver);
                          setTestEntityInput("");
                        }}
                      >
                        Test
                      </button>
                      <button
                        className="h-6 w-6 rounded p-0 text-xs text-rose-400 hover:text-rose-300"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteResolver(resolver);
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {filteredResolvers.length === 0 && (
                <div className="text-center py-8 text-sm text-slate-400">
                  No resolvers found
                </div>
              )}
            </div>
          </div>
        }
        centerTop={
          selectedResolver ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{selectedResolver.name}</h2>
                <Badge variant={selectedResolver.status === "active" ? "default" : "secondary"}>
                  {formatStatus(selectedResolver.status)}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Configuration</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <div>Rules: {selectedResolver.config.rules.length}</div>
                    <div>Default Namespace: {selectedResolver.config.default_namespace || "None"}</div>
                    <div>Version: {selectedResolver.config.version}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Metadata</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-sm">
                    <div>ID: {selectedResolver.asset_id}</div>
                    <div>Status: {selectedResolver.status}</div>
                    <div>Created: {new Date(selectedResolver.created_at).toLocaleDateString()}</div>
                    {selectedResolver.published_at && (
                      <div>Published: {new Date(selectedResolver.published_at).toLocaleDateString()}</div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {selectedResolver.description && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Description</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-slate-300">
                      {selectedResolver.description}
                    </p>
                  </CardContent>
                </Card>
              )}

              {selectedResolver.config.rules.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs">Rules</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {selectedResolver.config.rules.map((rule, index) => (
                      <div key={index} className="flex items-center justify-between rounded border border-slate-700 p-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{rule.name}</span>
                          <Badge variant="outline" className="text-xs">
                            {RULE_TYPE_LABELS[rule.rule_type]}
                          </Badge>
                          {!rule.is_active && (
                            <Badge variant="secondary" className="text-xs">
                              Inactive
                            </Badge>
                          )}
                        </div>
                        <div className="text-slate-400">
                          Priority: {rule.priority}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs">Test Resolver</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1">
                    <Label>Test Entities (one per line)</Label>
                    <Textarea
                      value={testEntityInput}
                      onChange={(e) => setTestEntityInput(e.target.value)}
                      placeholder="GT-01&#10;가스터빈1호기&#10;equipment-123"
                      rows={4}
                      className="text-sm"
                    />
                  </div>
                  <Button
                    onClick={() => handleSimulateResolver(selectedResolver)}
                    disabled={!testEntityInput.trim()}
                  >
                    Simulate Resolution
                  </Button>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-slate-400">
              Select a resolver to view details
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
                className="w-full justify-start"
                onClick={handleCreateResolver}
              >
                Create New Resolver
              </Button>
              {selectedResolver && (
                <>
                  <Button
                    className="w-full justify-start"
                    onClick={() => handleEditResolver(selectedResolver)}
                  >
                    Edit Resolver
                  </Button>
                  <Button
                    className="w-full justify-start"
                    onClick={() => setSelectedResolver(selectedResolver)}
                  >
                    Test Resolver
                  </Button>
                </>
              )}
            </div>

            <div className="text-xs uppercase tracking-[0.25em] text-slate-400 mt-6">
              Rule Types
            </div>
            <div className="space-y-1">
              {Object.entries(RULE_TYPE_LABELS).map(([type, label]) => (
                <div key={type} className="text-xs text-slate-300">
                  • {label}
                </div>
              ))}
            </div>

            <div className="text-xs uppercase tracking-[0.25em] text-slate-400 mt-6">
              Supported Transformations
            </div>
            <div className="space-y-1">
              <div className="text-xs text-slate-300">• Uppercase</div>
              <div className="text-xs text-slate-300">• Lowercase</div>
              <div className="text-xs text-slate-300">• Trim</div>
              <div className="text-xs text-slate-300">• Normalize</div>
            </div>
          </div>
        }
      />

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateDialogOpen || isEditDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setIsCreateDialogOpen(false);
          setIsEditDialogOpen(false);
          setEditingResolver(null);
        }
      }}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {isCreateDialogOpen ? "Create New Resolver" : "Edit Resolver"}
            </DialogTitle>
            <DialogDescription>
              Configure entity resolution rules
            </DialogDescription>
          </DialogHeader>

          {editingResolver && (
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={editingResolver.name || ""}
                      onChange={(e) => setEditingResolver({ ...editingResolver, name: e.target.value })}
                      placeholder="Enter resolver name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="default_namespace">Default Namespace</Label>
                    <Input
                      id="default_namespace"
                      value={editingResolver.config?.default_namespace || ""}
                      onChange={(e) => setEditingResolver({
                        ...editingResolver,
                        config: { ...editingResolver.config!, default_namespace: e.target.value }
                      })}
                      placeholder="e.g., production"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={editingResolver.description || ""}
                    onChange={(e) => setEditingResolver({ ...editingResolver, description: e.target.value })}
                    placeholder="Enter resolver description"
                    rows={2}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="scope">Scope</Label>
                  <Input
                    id="scope"
                    value={editingResolver.scope || ""}
                    onChange={(e) => setEditingResolver({ ...editingResolver, scope: e.target.value })}
                    placeholder="e.g., production, staging"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium">Rules</h3>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => addRule("alias_mapping")}
                    >
                      + Alias Mapping
                    </Button>
                    <Button
                      onClick={() => addRule("pattern_rule")}
                    >
                      + Pattern Rule
                    </Button>
                    <Button
                      onClick={() => addRule("transformation")}
                    >
                      + Transformation
                    </Button>
                  </div>
                </div>

                {editingResolver.config?.rules && editingResolver.config.rules.length > 0 ? (
                  <div className="space-y-3">
                    {editingResolver.config.rules.map((rule, index) => renderRuleForm(rule, index))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-sm text-slate-400 border border-dashed border-slate-700 rounded-xl">
                    No rules configured. Click one of the buttons above to add a rule.
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
                <Button
                  onClick={() => {
                    setIsCreateDialogOpen(false);
                    setIsEditDialogOpen(false);
                    setEditingResolver(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveResolver}
                  disabled={
                    !editingResolver.name ||
                    createMutation.isPending ||
                    updateMutation.isPending
                  }
                >
                  {isCreateDialogOpen ? "Create" : "Save"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Simulation Results Dialog */}
      <Dialog open={isSimulateDialogOpen} onOpenChange={setIsSimulateDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Resolver Simulation Results</DialogTitle>
            <DialogDescription>
              Testing {selectedResolver?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {simulationResults.map((result, index) => (
              <Card key={index}>
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-sm">{result.original_entity}</div>
                      <div className="text-xs text-slate-400">
                        Confidence: {(result.confidence_score * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">→</span>
                      <span className="text-sm font-medium text-sky-400">{result.resolved_entity}</span>
                    </div>
                    {result.transformations_applied.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs text-slate-400">Transformations:</div>
                        {result.transformations_applied.map((transform, i) => (
                          <div key={i} className="text-xs text-slate-300">• {transform}</div>
                        ))}
                      </div>
                    )}
                    {result.matched_rules.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs text-slate-400">Matched Rules:</div>
                        {result.matched_rules.map((rule, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {rule}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
