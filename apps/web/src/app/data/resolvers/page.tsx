"use client";

import type React from "react";
import { useEffect, useState } from "react";
import BuilderShell from "../../../components/builder/BuilderShell";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Badge } from "../../../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../../../components/ui/dialog";
import { Label } from "../../../components/ui/label";
import { Textarea } from "../../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs";
import { formatError } from "../../../lib/utils";

type ResolverType = "alias_mapping" | "pattern_rule" | "transformation";

interface ResolverRule {
  rule_type: ResolverType;
  name: string;
  description?: string;
  is_active: boolean;
  priority: number;
  metadata?: Record<string, unknown>;
  rule_data: unknown;
}

interface ResolverConfig {
  name: string;
  description?: string;
  rules: ResolverRule[];
  default_namespace?: string;
  tags?: Record<string, unknown>;
  version: number;
}

interface ResolverAssetResponse {
  asset_id: string;
  asset_type: string;
  name: string;
  description?: string;
  version: number;
  status: string;
  config: ResolverConfig;
  scope?: string;
  tags?: Record<string, unknown>;
  created_by?: string;
  published_by?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
}

interface AliasMapping {
  source_entity: string;
  target_entity: string;
  namespace?: string;
  description?: string;
  is_active: boolean;
  priority: number;
  metadata?: Record<string, unknown>;
}

interface PatternRule {
  name: string;
  pattern: string;
  replacement: string;
  description?: string;
  is_active: boolean;
  priority: number;
  metadata?: Record<string, unknown>;
}

interface TransformationRule {
  name: string;
  transformation_type: string;
  field_name: string;
  description?: string;
  is_active: boolean;
  priority: number;
  parameters?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

interface ResolverSimulationRequest {
  config: ResolverConfig;
  test_entities: string[];
  simulation_options?: Record<string, unknown>;
}

interface ResolverSimulationResult {
  original_entity: string;
  resolved_entity: string;
  transformations_applied: string[];
  confidence_score: number;
  matched_rules: string[];
  metadata?: Record<string, unknown>;
}

const RULE_TYPE_LABELS: Record<ResolverType, string> = {
  alias_mapping: "Alias Mapping",
  pattern_rule: "Pattern Rule",
  transformation: "Transformation",
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

export default function ResolversPage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const enableAssetRegistry = process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY === "true";

  const [resolvers, setResolvers] = useState<ResolverAssetResponse[]>([]);
  const [selectedResolver, setSelectedResolver] = useState<ResolverAssetResponse | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isRuleDialogOpen, setIsRuleDialogOpen] = useState(false);
  const [isSimulateDialogOpen, setIsSimulateDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ResolverRule | null>(null);
  const [simulationInput, setSimulationInput] = useState("");
  const [simulationResults, setSimulationResults] = useState<ResolverSimulationResult[]>([]);

  const resolversQuery = useQuery({
    queryKey: ["asset-registry", "resolvers"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/asset_registry/resolvers`);
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Failed to load resolvers");
      }
      return body.data as ResolverAssetResponse[];
    },
    enabled: enableAssetRegistry,
  });

  const simulateMutation = useMutation({
    mutationFn: async (request: ResolverSimulationRequest) => {
      const response = await fetch(`${apiBaseUrl}/asset_registry/resolvers/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Simulation failed");
      }
      return body.data as ResolverSimulationResult[];
    },
    onSuccess: (data) => {
      setSimulationResults(data);
      setIsSimulateDialogOpen(true);
    },
  });

  useEffect(() => {
    if (resolversQuery.data) {
      setResolvers(resolversQuery.data);
    }
  }, [resolversQuery.data, setResolvers]);

  const handleCreateRule = (resolver: ResolverAssetResponse) => {
    setEditingRule({
      rule_type: "alias_mapping",
      name: "",
      is_active: true,
      priority: 0,
      rule_data: {
        source_entity: "",
        target_entity: "",
      },
    });
    setSelectedResolver(resolver);
    setIsRuleDialogOpen(true);
  };

  const handleSimulate = (resolver: ResolverAssetResponse) => {
    setSelectedResolver(resolver);
    setSimulationResults([]);
    setIsSimulateDialogOpen(true);
  };

  const runSimulation = () => {
    if (!selectedResolver || !simulationInput) return;

    const request: ResolverSimulationRequest = {
      config: selectedResolver.config,
      test_entities: simulationInput.split("\n").filter(Boolean),
    };

    simulateMutation.mutate(request);
  };

  const renderRuleForm = () => {
    if (!editingRule) return null;

    return (
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>Rule Type</Label>
          <Select
            value={editingRule.rule_type}
            onValueChange={(value) => setEditingRule({
              ...editingRule,
              rule_type: value as ResolverType,
              rule_data: getDefaultRuleData(value as ResolverType)
            })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(RULE_TYPE_LABELS).map(([type, label]) => (
                <SelectItem key={type} value={type}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="rule-name">Rule Name</Label>
          <Input
            id="rule-name"
            value={editingRule.name}
            onChange={(e) => setEditingRule({
              ...editingRule,
              name: e.target.value
            })}
            placeholder="Enter rule name"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="rule-description">Description</Label>
          <Textarea
            id="rule-description"
            value={editingRule.description || ""}
            onChange={(e) => setEditingRule({
              ...editingRule,
              description: e.target.value
            })}
            placeholder="Enter rule description"
            rows={2}
          />
        </div>

        {editingRule.rule_type === "alias_mapping" && (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Source Entity</Label>
              <Input
                value={editingRule.rule_data.source_entity}
                onChange={(e) => setEditingRule({
                  ...editingRule,
                  rule_data: {
                    ...editingRule.rule_data,
                    source_entity: e.target.value
                  }
                })}
                placeholder="source.entity"
              />
            </div>
            <div className="space-y-2">
              <Label>Target Entity</Label>
              <Input
                value={editingRule.rule_data.target_entity}
                onChange={(e) => setEditingRule({
                  ...editingRule,
                  rule_data: {
                    ...editingRule.rule_data,
                    target_entity: e.target.value
                  }
                })}
                placeholder="target.entity"
              />
            </div>
          </div>
        )}

        {editingRule.rule_type === "pattern_rule" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Pattern (Regex)</Label>
              <Input
                value={editingRule.rule_data.pattern}
                onChange={(e) => setEditingRule({
                  ...editingRule,
                  rule_data: {
                    ...editingRule.rule_data,
                    pattern: e.target.value
                  }
                })}
                placeholder="^old_.*"
              />
            </div>
            <div className="space-y-2">
              <Label>Replacement</Label>
              <Input
                value={editingRule.rule_data.replacement}
                onChange={(e) => setEditingRule({
                  ...editingRule,
                  rule_data: {
                    ...editingRule.rule_data,
                    replacement: e.target.value
                  }
                })}
                placeholder="new_$1"
              />
            </div>
          </div>
        )}

        {editingRule.rule_type === "transformation" && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Transformation Type</Label>
                <Select
                  value={editingRule.rule_data.transformation_type}
                  onValueChange={(value) => setEditingRule({
                    ...editingRule,
                    rule_data: {
                      ...editingRule.rule_data,
                      transformation_type: value
                    }
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="uppercase">Uppercase</SelectItem>
                    <SelectItem value="lowercase">Lowercase</SelectItem>
                    <SelectItem value="capitalize">Capitalize</SelectItem>
                    <SelectItem value="trim">Trim</SelectItem>
                    <SelectItem value="format">Custom Format</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Field Name</Label>
                <Input
                  value={editingRule.rule_data.field_name}
                  onChange={(e) => setEditingRule({
                    ...editingRule,
                    rule_data: {
                      ...editingRule.rule_data,
                      field_name: e.target.value
                    }
                  })}
                  placeholder="field_name"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Parameters (JSON)</Label>
              <Textarea
                placeholder='{"format": "%Y-%m-%d"}'
                value={JSON.stringify(editingRule.rule_data.parameters || {}, null, 2)}
                onChange={(e) => {
                  try {
                    setEditingRule({
                      ...editingRule,
                      rule_data: {
                        ...editingRule.rule_data,
                        parameters: JSON.parse(e.target.value)
                      }
                    });
                  } catch {
                    // Invalid JSON
                  }
                }}
                rows={3}
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Priority</Label>
            <Input
              type="number"
              value={editingRule.priority}
              onChange={(e) => setEditingRule({
                ...editingRule,
                priority: parseInt(e.target.value) || 0
              })}
            />
          </div>
          <div className="space-y-2">
            <Label>Active</Label>
            <Select
              value={editingRule.is_active ? "true" : "false"}
              onValueChange={(value) => setEditingRule({
                ...editingRule,
                is_active: value === "true"
              })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">Active</SelectItem>
                <SelectItem value="false">Inactive</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setIsRuleDialogOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => {
            // TODO: Implement rule creation/update
            console.log("Save rule:", editingRule);
            setIsRuleDialogOpen(false);
          }}>
            Save Rule
          </Button>
        </div>
      </div>
    );
  };

  const getDefaultRuleData = (type: ResolverType): unknown => {
    switch (type) {
      case "alias_mapping":
        return {
          source_entity: "",
          target_entity: "",
        };
      case "pattern_rule":
        return {
          pattern: "",
          replacement: "",
        };
      case "transformation":
        return {
          transformation_type: "uppercase",
          field_name: "",
          parameters: {},
        };
    }
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
        <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Admin only
        </div>
      </div>
      <p className="mb-6 text-sm text-slate-400">
        Manage entity resolution rules and mappings.
      </p>

      <BuilderShell
        leftPane={
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
              Resolvers ({resolvers.length})
            </div>
            <div className="custom-scrollbar max-h-[calc(100vh-300px)] space-y-2 overflow-auto pr-1">
              {resolversQuery.isError && (
                <div className="text-xs text-rose-300">
                  {formatError(resolversQuery.error)}
                </div>
              )}
              {resolvers.map((resolver) => (
                <div
                  key={resolver.asset_id}
                  className={`rounded-xl border px-3 py-2 cursor-pointer ${
                    selectedResolver?.asset_id === resolver.asset_id
                      ? "border-sky-500 bg-sky-500/10"
                      : "border-slate-800 hover:border-slate-600"
                  }`}
                  onClick={() => setSelectedResolver(resolver)}
                >
                  <div className="font-medium text-sm mb-1">{resolver.name}</div>
                  <div className="text-xs text-slate-400 mb-2">
                    {resolver.config.rules.length} rules, v{resolver.version}
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge variant={resolver.status === "active" ? "default" : "secondary"}>
                      {formatStatus(resolver.status)}
                    </Badge>
                    <div className="text-xs text-slate-400">
                      {resolver.config.rules.filter(r => r.is_active).length} active
                    </div>
                  </div>
                </div>
              ))}
              {resolvers.length === 0 && (
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

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs">Overview</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div>Rules: {selectedResolver.config.rules.length}</div>
                  <div>Active rules: {selectedResolver.config.rules.filter(r => r.is_active).length}</div>
                  <div>Version: {selectedResolver.version}</div>
                  {selectedResolver.config.default_namespace && (
                    <div>Default namespace: {selectedResolver.config.default_namespace}</div>
                  )}
                </CardContent>
              </Card>

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

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleCreateRule(selectedResolver)}
                >
                  Add Rule
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleSimulate(selectedResolver)}
                >
                  Test Resolver
                </Button>
              </div>

              <div className="space-y-3">
                <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                  Rules ({selectedResolver.config.rules.length})
                </div>
                <div className="custom-scrollbar max-h-[400px] space-y-2 overflow-auto pr-1">
                  {selectedResolver.config.rules.map((rule) => (
                    <Card key={rule.name} className="border-slate-800">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-xs">
                            {rule.name}
                          </CardTitle>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={rule.is_active ? "default" : "secondary"}
                              className="text-xs"
                            >
                              {rule.is_active ? "Active" : "Inactive"}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {RULE_TYPE_LABELS[rule.rule_type]}
                            </Badge>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-1">
                        {rule.description && (
                          <p className="text-xs text-slate-400">{rule.description}</p>
                        )}
                        <div className="text-xs text-slate-300">
                          Priority: {rule.priority}
                        </div>
                        {rule.rule_type === "alias_mapping" && (
                          <div className="text-xs text-slate-400">
                            {rule.rule_data.source_entity} → {rule.rule_data.target_entity}
                          </div>
                        )}
                        {rule.rule_type === "pattern_rule" && (
                          <div className="text-xs text-slate-400">
                            {rule.rule_data.pattern} → {rule.rule_data.replacement}
                          </div>
                        )}
                        {rule.rule_type === "transformation" && (
                          <div className="text-xs text-slate-400">
                            Transform {rule.rule_data.field_name} ({rule.rule_data.transformation_type})
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
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
              Rule Types
            </div>
            <div className="space-y-1 text-xs text-slate-300">
              {Object.entries(RULE_TYPE_LABELS).map(([type, label]) => (
                <div key={type}>
                  • {label}
                </div>
              ))}
            </div>

            <div className="text-xs uppercase tracking-[0.25em] text-slate-400 mt-6">
              Quick Actions
            </div>
            <div className="space-y-2">
              {selectedResolver && (
                <>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => handleCreateRule(selectedResolver)}
                  >
                    Add New Rule
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start"
                    onClick={() => handleSimulate(selectedResolver)}
                  >
                    Test Resolver
                  </Button>
                </>
              )}
            </div>

            <div className="text-xs uppercase tracking-[0.25em] text-slate-400 mt-6">
              Tips
            </div>
            <div className="space-y-2 text-xs text-slate-300">
              <p>• Rules are applied in priority order (highest first)</p>
              <p>• Alias mappings provide direct entity replacements</p>
              <p>• Pattern rules use regex for flexible matching</p>
              <p>• Transformations modify field values</p>
            </div>
          </div>
        }
      />

      {/* Rule Dialog */}
      <Dialog open={isRuleDialogOpen} onOpenChange={setIsRuleDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create/Edit Rule</DialogTitle>
            <DialogDescription>
              Configure a new resolution rule
            </DialogDescription>
          </DialogHeader>
          {renderRuleForm()}
        </DialogContent>
      </Dialog>

      {/* Simulation Dialog */}
      <Dialog open={isSimulateDialogOpen} onOpenChange={setIsSimulateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Test Resolver</DialogTitle>
            <DialogDescription>
              Test the resolver with sample entity names
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Test Entities (one per line)</Label>
              <Textarea
                placeholder="user&#10;customer&#10;account"
                value={simulationInput}
                onChange={(e) => setSimulationInput(e.target.value)}
                rows={4}
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsSimulateDialogOpen(false)}>
                Close
              </Button>
              <Button onClick={runSimulation} disabled={!simulationInput || simulateMutation.isPending}>
                {simulateMutation.isPending ? "Simulating..." : "Simulate"}
              </Button>
            </div>
          </div>

          {simulationResults.length > 0 && (
            <div className="space-y-3">
              <div className="text-xs uppercase tracking-[0.25em] text-slate-400">
                Simulation Results
              </div>
              <div className="space-y-2">
                {simulationResults.map((result, index) => (
                  <Card key={index} className="border-slate-800">
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">{result.original_entity}</span>
                        <span className="text-xs text-slate-400">
                          Score: {result.confidence_score.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-xs text-sky-400">
                        → {result.resolved_entity}
                      </div>
                      {result.transformations_applied.length > 0 && (
                        <div className="text-xs text-slate-400 mt-1">
                          Applied: {result.transformations_applied.join(", ")}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}